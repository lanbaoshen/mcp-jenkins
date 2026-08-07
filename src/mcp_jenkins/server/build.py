import base64
from typing import Literal

from fastmcp import Context
from requests.exceptions import HTTPError

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.jenkins import Jenkins, PendingInputsUnavailableError
from mcp_jenkins.server import mcp


def _resolve_build_number(client: Jenkins, fullname: str, number: int | None) -> int:
    """Resolve an omitted build number to the job's last build, raising a clear error when it has none

    The number is fetched with a tree query rather than a depth=1 item fetch: the latter returns every
    build stub, action and parameter definition of the job to read a single integer.
    """
    if number is not None:
        return number

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

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

    Only the given build is inspected. With number=None that is the job's last build, so a paused build
    that is no longer the most recent one is not found that way — locate it with get_running_builds and
    pass its number explicitly.

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, check the last build

    Returns:
        A list of pending inputs with id, message, proceedText and inputs (parameter definitions)
    """
    client = jenkins(ctx)

    number = _resolve_build_number(client, fullname, number)

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
        Omitting a declared parameter settles it with null — Jenkins does not fall back to the declared
        defaults, so every declared parameter must be submitted. That is enforced whenever the pending
        input can be discovered; when the pending inputs cannot be fetched (wfapi endpoint missing or
        erroring) an explicit input_id is submitted as-is, so check the declared parameters yourself in
        that case.
        If this call times out the input may or may not have been settled: re-check with
        get_pending_inputs rather than retrying, because a settled input rejects a second submission.

    Args:
        fullname: The fullname of the job
        number: The number of the paused build, use get_pending_inputs to confirm its pending input
            (and get_running_builds to locate a paused build that is not the job's last one)
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

    # Validation needs the pending input's declared parameters. An explicit input_id must stay usable on
    # controllers where the wfapi endpoint is missing or unreadable, so there a failed discovery degrades
    # to no validation. Malformed wfapi responses are not a degrade signal — they raise, because silently
    # skipping validation lets a misspelled parameter settle the real one with null.
    pending_inputs = None
    discovery_error = None
    if input_id is None or action == 'proceed':
        try:
            pending_inputs = client.get_build_pending_inputs(fullname=fullname, number=number)
        except (PendingInputsUnavailableError, HTTPError) as e:
            if input_id is None:
                raise
            discovery_error = e

    pending = None
    if input_id is None:
        if not pending_inputs:
            raise ValueError(f'No pending input for {fullname} #{number}')
        if len(pending_inputs) > 1:
            ids = ', '.join(pending_input.id for pending_input in pending_inputs)
            raise ValueError(f'Multiple pending inputs for {fullname} #{number}, pass input_id: {ids}')
        pending = pending_inputs[0]
        input_id = pending.id
    elif pending_inputs is not None:
        pending = next((pending_input for pending_input in pending_inputs if pending_input.id == input_id), None)
        if pending is None:
            ids = ', '.join(pending_input.id for pending_input in pending_inputs) or 'none'
            raise ValueError(f'No pending input {input_id} for {fullname} #{number}. Pending inputs: {ids}')

    if pending is not None and action == 'proceed':
        declared = {parameter['name'] for parameter in pending.inputs if 'name' in parameter}
        submitted = set(parameters or {})

        unknown = sorted(submitted - declared)
        if unknown:
            msg = (
                f'Input {input_id} of {fullname} #{number} does not declare {", ".join(unknown)}. '
                f'Declared parameters: {", ".join(sorted(declared)) or "none"}'
            )
            raise ValueError(msg)

        missing = sorted(declared - submitted)
        if missing:
            msg = (
                f'Input {input_id} of {fullname} #{number} declares {", ".join(sorted(declared))} but got '
                f'no value for {", ".join(missing)}. Omitted parameters settle with null rather than their '
                f'declared defaults, so pass every declared parameter.'
            )
            raise ValueError(msg)

    if action == 'abort':
        jenkins_action = 'abort'
    else:
        jenkins_action = 'proceed' if parameters else 'proceedEmpty'

    try:
        client.submit_build_input(
            fullname=fullname, number=number, input_id=input_id, action=jenkins_action, parameters=parameters
        )
    except HTTPError as e:
        if discovery_error is not None:
            msg = (
                f'Submitting input {input_id} for {fullname} #{number} failed ({e}) and the pending inputs '
                f'could not be checked beforehand: {discovery_error}'
            )
        else:
            msg = (
                f'Submitting input {input_id} for {fullname} #{number} failed ({e}). The input may already '
                f'be settled — re-check with get_pending_inputs rather than retrying.'
            )
        raise ValueError(msg) from e

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

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
    number = _resolve_build_number(jenkins(ctx), fullname, number)

    return jenkins(ctx).get_build_artifact_url(fullname=fullname, number=number, relative_path=relative_path)
