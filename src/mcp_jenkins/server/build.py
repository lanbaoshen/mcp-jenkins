from typing import Literal

from mcp.server.fastmcp import Context

from mcp_jenkins.server import client, mcp


@mcp.tool(tag='read')
async def get_running_builds(ctx: Context) -> list[dict]:
    """
    Get all running builds from Jenkins

    Returns:
        list[dict]: A list of all running builds
    """
    return [build.model_dump(exclude_none=True) for build in client(ctx).build.get_running_builds()]


@mcp.tool(tag='read')
async def get_build_info(ctx: Context, fullname: str, build_number: int | None = None) -> dict:
    """
    Get specific build info from Jenkins

    Args:
        fullname: The fullname of the job
        build_number: The number of the build, if None, get the last build

    Returns:
        dict: The build info
    """
    if build_number is None:
        build_number = client(ctx).job.get_job_info(fullname).lastBuild.number
    return client(ctx).build.get_build_info(fullname, build_number).model_dump(exclude_none=True)


@mcp.tool(tag='read')
async def get_build_sourcecode(ctx: Context, fullname: str, build_number: int | None = None) -> str:
    """
    Get the pipeline source code of a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        build_number: The number of the build, if None, get the last build

    Returns:
        str: The source code of the build
    """
    if build_number is None:
        build_number = client(ctx).job.get_job_info(fullname).lastBuild.number
    return client(ctx).build.get_build_sourcecode(fullname, build_number)


@mcp.tool(tag='write')
async def build_job(ctx: Context, fullname: str, parameters: dict = None) -> int:
    """
    Build a job in Jenkins

    Args:
        fullname: The fullname of the job
        parameters: Update the default parameters of the job.

    Returns:
        The queue item number of the job, only valid for about five minutes after the job completes
    """
    return client(ctx).build.build_job(fullname, parameters)


@mcp.tool(tag='read')
async def get_build_logs(
    ctx: Context,
    fullname: str,
    build_number: str,
    pattern: str = None,
    limit: int = 100,
    seq: Literal['asc', 'desc'] = 'asc',
) -> str:
    """
    Get logs from a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        build_number: The number of the build
        pattern: A pattern to filter the logs
        limit: The maximum number of lines to retrieve
        seq: Priority order of log returns

    Returns:
        str: The logs of the build
    """
    build_number = int(build_number)
    return client(ctx).build.get_build_logs(fullname, build_number, pattern, limit, seq)


@mcp.tool(tag='write')
async def stop_build(ctx: Context, fullname: str, build_number: int) -> None:
    """
    Stop a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        build_number: The number of the build to stop
    """
    return client(ctx).build.stop_build(fullname, build_number)
