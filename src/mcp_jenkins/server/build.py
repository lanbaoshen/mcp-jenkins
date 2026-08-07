import base64
from typing import Literal

from fastmcp import Context

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.jenkins import Jenkins
from mcp_jenkins.server import mcp


def _last_build_number(client: Jenkins, fullname: str) -> int:
    """Resolve the last build number of a job, raising a clear error when it has none

    The number is fetched with a tree query rather than a depth=1 item fetch: the latter returns every
    build stub, action and parameter definition of the job to read a single integer.
    """
    number = client.get_last_build_number(fullname=fullname)
    if number is None:
        raise ValueError(f'No build found for job: {fullname}')

    return number


@mcp.tool(tags=['read'])
async def get_running_builds(ctx: Context) -> list[dict]:
    """Get all running builds from Jenkins

    Returns:
        A list of all running builds
    """
    return [
        item.model_dump(include={'number', 'url', 'building', 'timestamp'})
        for item in jenkins(ctx).get_running_builds()
    ]


@mcp.tool(tags=['read'])
async def get_build(ctx: Context, fullname: str, number: int | None = None) -> dict:
    """Get specific build info from Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build

    Returns:
        The build info
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return jenkins(ctx).get_build(fullname=fullname, number=number).model_dump(exclude_none=True)


@mcp.tool(tags=['read'])
async def get_build_scripts(ctx: Context, fullname: str, number: int | None = None) -> list[str]:
    """Get the scripts used in a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build

    Returns:
        A list of scripts used in the build
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return jenkins(ctx).get_build_replay(fullname=fullname, number=number).scripts


@mcp.tool(tags=['read'])
async def get_build_console_output(
    ctx: Context,
    fullname: str,
    number: int | None = None,
    pattern: str | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> str:
    """Get the console output of a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build
        pattern: Optional regex pattern to filter lines (only matching lines are returned)
        offset: Number of lines to skip from the beginning after filtering, default 0
        limit: Maximum number of lines to return after filtering and offset

    Returns:
        The console output of the build
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number
    if number is None:
        raise ValueError(f'No build found for job: {fullname}')

    return jenkins(ctx).get_build_console_output(
        fullname=fullname, number=number, pattern=pattern, offset=offset, limit=limit
    )


@mcp.tool(tags=['read'])
async def get_build_test_report(ctx: Context, fullname: str, number: int | None = None) -> dict:
    """Get the test report of a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build

    Returns:
        The test report of the build
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return jenkins(ctx).get_build_test_report(fullname=fullname, number=number)


@mcp.tool(tags=['read'])
async def get_build_parameters(ctx: Context, fullname: str, number: int | None = None) -> dict:
    """Get the parameters of a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build

    Returns:
        A dictionary of build parameter names and their values
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return jenkins(ctx).get_build_parameters(fullname=fullname, number=number)


@mcp.tool(tags=['write'])
async def stop_build(ctx: Context, fullname: str, number: int) -> None:
    """Stop a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build to stop
    """
    return jenkins(ctx).stop_build(fullname=fullname, number=number)


@mcp.tool(tags=['read'])
async def get_pending_inputs(ctx: Context, fullname: str, number: int | None = None) -> list[dict]:
    """Get the pending input steps of a specific build in Jenkins

    A pipeline showing "Paused for Input" is waiting on an input step. Call this before submit_input
    to discover the input id and the parameter definitions the pipeline is waiting for.

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build

    Returns:
        A list of pending inputs with id, message, proceedText and inputs (parameter definitions)
    """
    client = jenkins(ctx)

    if number is None:
        number = _last_build_number(client, fullname)

    return [
        pending_input.model_dump(exclude_none=True)
        for pending_input in client.get_build_pending_inputs(fullname=fullname, number=number)
    ]


@mcp.tool(tags=['write'])
async def submit_input(
    ctx: Context,
    fullname: str,
    number: int,
    input_id: str | None = None,
    parameters: dict | None = None,
    action: Literal['proceed', 'abort'] = 'proceed',
) -> dict:
    """Respond to a pipeline input step of a build that is paused for input in Jenkins

    Warnings:
        Omitting parameters proceeds without submitting any values — Jenkins does not fall back to the
        declared defaults. That is refused when the input is discovered here, but passing input_id skips
        discovery, so call get_pending_inputs first in that case.
        If this call times out the input may or may not have been settled: re-check with
        get_pending_inputs rather than retrying, because a settled input rejects a second submission.

    Args:
        fullname: The fullname of the job
        number: The number of the build to respond to, use get_pending_inputs to find the paused build
        input_id: The id of the pending input, if None, resolved automatically when exactly one is pending
        parameters: A mapping of parameter name to value, e.g. {'APPROVE': True, 'TARGET': 'prod'}
        action: 'proceed' to continue the pipeline, 'abort' to reject the input and abort the build

    Returns:
        A dict with the fullname, number, inputId and the Jenkins action that was submitted:
        'proceed' with values, 'proceedEmpty' with none, or 'abort'
    """
    if action == 'abort' and parameters:
        raise ValueError(f'parameters cannot be combined with action="abort" for {fullname} #{number}')

    client = jenkins(ctx)

    # Only known when the input is discovered here: an explicit input_id skips the wfapi lookup.
    declared = None

    if input_id is None:
        pending_inputs = client.get_build_pending_inputs(fullname=fullname, number=number)
        if not pending_inputs:
            raise ValueError(f'No pending input for {fullname} #{number}')
        if len(pending_inputs) > 1:
            ids = ', '.join(pending_input.id for pending_input in pending_inputs)
            raise ValueError(f'Multiple pending inputs for {fullname} #{number}, pass input_id: {ids}')
        input_id = pending_inputs[0].id
        declared = {parameter['name'] for parameter in pending_inputs[0].inputs if 'name' in parameter}

    # An input that reports no definitions is left to Jenkins: absent data is not proof of absent parameters.
    if declared and action == 'proceed':
        if not parameters:
            msg = (
                f'Input {input_id} of {fullname} #{number} declares {", ".join(sorted(declared))}. '
                f'Proceeding without values settles it with null rather than the declared defaults, '
                f'so pass parameters explicitly.'
            )
            raise ValueError(msg)

        unknown = sorted(set(parameters) - declared)
        if unknown:
            msg = (
                f'Input {input_id} of {fullname} #{number} does not declare {", ".join(unknown)}. '
                f'Declared parameters: {", ".join(sorted(declared))}'
            )
            raise ValueError(msg)

    if action == 'abort':
        jenkins_action = 'abort'
    else:
        jenkins_action = 'proceed' if parameters else 'proceedEmpty'

    client.submit_build_input(
        fullname=fullname, number=number, input_id=input_id, action=jenkins_action, parameters=parameters
    )

    return {'fullname': fullname, 'number': number, 'inputId': input_id, 'action': jenkins_action}


@mcp.tool(tags=['read'])
async def get_all_build_artifacts(ctx: Context, fullname: str, number: int | None = None) -> list[dict]:
    """List the artifacts of a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build

    Returns:
        A list of artifact metadata dicts with fileName, relativePath, and displayPath
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return [
        artifact.model_dump(exclude_none=True)
        for artifact in jenkins(ctx).get_build_artifacts(fullname=fullname, number=number)
    ]


@mcp.tool(tags=['read'])
async def get_build_artifact(ctx: Context, fullname: str, relative_path: str, number: int | None = None) -> dict:
    """Download an artifact from a specific build in Jenkins

    Binary files are returned as base64-encoded content; text files are returned as plain text.

    Args:
        fullname: The fullname of the job
        relative_path: The relative path of the artifact (e.g. playwright-report/index.html)
        number: The number of the build, if None, get the last build

    Returns:
        A dict with 'content' (str) and 'encoding' ('utf-8' or 'base64')
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    content = jenkins(ctx).get_build_artifact(fullname=fullname, number=number, relative_path=relative_path)

    try:
        return {'content': content.decode('utf-8'), 'encoding': 'utf-8'}
    except UnicodeDecodeError:
        return {'content': base64.b64encode(content).decode('ascii'), 'encoding': 'base64'}


@mcp.tool(tags=['read'])
async def get_build_artifact_url(ctx: Context, fullname: str, relative_path: str, number: int | None = None) -> str:
    """Get the direct URL of an artifact from a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        relative_path: The relative path of the artifact (e.g. playwright-report/index.html)
        number: The number of the build, if None, get the last build

    Returns:
        The direct Jenkins URL of the artifact
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return jenkins(ctx).get_build_artifact_url(fullname=fullname, number=number, relative_path=relative_path)
