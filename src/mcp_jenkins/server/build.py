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
async def get_build_console_output(ctx: Context, fullname: str, number: int | None = None) -> str:
    """Get the console output of a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build, if None, get the last build

    Returns:
        The console output of the build
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return jenkins(ctx).get_build_console_output(fullname=fullname, number=number)


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


@mcp.tool(tags=['write'])
async def stop_build(ctx: Context, fullname: str, number: int) -> None:
    """Stop a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        number: The number of the build to stop
    """
    return jenkins(ctx).stop_build(fullname=fullname, number=number)
