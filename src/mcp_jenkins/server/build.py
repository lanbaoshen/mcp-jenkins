from mcp.server.fastmcp import Context

from mcp_jenkins.server import client, mcp


@mcp.tool()
async def get_running_builds(ctx: Context) -> list[dict]:
    """
    Get all running builds from Jenkins

    Returns:
        list[Build]: A list of all running builds
    """
    return [build.model_dump(exclude_none=True) for build in client(ctx).build.get_running_builds()]


@mcp.tool()
async def get_build_info(ctx: Context, fullname: str, build_number: int | None = None) -> dict:
    """
    Get specific build info from Jenkins

    Args:
        fullname: The fullname of the job
        build_number: The number of the build, if None, get the last build

    Returns:
        Build: The build info
    """
    if build_number is None:
        build_number = client(ctx).job.get_job_info(fullname).lastBuild.number
    return client(ctx).build.get_build_info(fullname, build_number).model_dump(exclude_none=True)


@mcp.tool()
async def build_job(ctx: Context, fullname: str, parameters: dict | None = None) -> int:
    """
    Build a job in Jenkins

    Args:
        fullname: The fullname of the job
        parameters: Update the default parameters of the job.
            If you want to use the default param, just set it to {}.
            If the job have no parameters, this can be None.

    Returns:
        The build number of the job
    """
    return client(ctx).build.build_job(fullname, parameters)
