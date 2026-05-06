import base64

from fastmcp import Context

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.server import mcp


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
