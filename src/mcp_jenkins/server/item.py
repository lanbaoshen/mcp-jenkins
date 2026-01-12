from typing import Literal

from fastmcp import Context

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.server import mcp


@mcp.tool(tags=['read'])
async def get_all_jobs(ctx: Context) -> list[dict]:
    """Get all jobs from Jenkins

    Returns:
        A list of jobs
    """
    return [item.model_dump(exclude_none=True) for item in jenkins(ctx).get_items()]


@mcp.tool(tags=['read'])
async def get_job(ctx: Context, fullname: str) -> dict:
    """Get specific job from Jenkins

    Args:
        fullname: The fullname of the job

    Returns:
        The job
    """
    return jenkins(ctx).get_item(fullname=fullname).model_dump(exclude_none=True)


@mcp.tool(tags=['read'])
async def get_job_config(ctx: Context, fullname: str) -> str:
    """Get specific job config from Jenkins

    Args:
        fullname: The fullname of the job

    Returns:
        The config of the job
    """
    return jenkins(ctx).get_item_config(fullname=fullname)


@mcp.tool(tags=['read'])
async def query_jobs(
    ctx: Context,
    class_pattern: str = None,
    fullname_pattern: str = None,
    color_pattern: str = None,
) -> list[dict]:
    """Query jobs from Jenkins

    Args:
        class_pattern: The pattern of the _class
        fullname_pattern: The pattern of the fullname
        color_pattern: The pattern of the color

    Returns:
        A list of jobs
    """
    return [
        item.model_dump(exclude_none=True)
        for item in jenkins(ctx).query_items(
            class_pattern=class_pattern,
            fullname_pattern=fullname_pattern,
            color_pattern=color_pattern,
        )
    ]


@mcp.tool(tags=['write'])
async def build_job(
    ctx: Context, fullname: str, build_type: Literal['build', 'buildWithParameters'], params: dict = None
) -> int:
    """Build a job in Jenkins

    Args:
        fullname: The fullname of the job
        params: Update the default parameters of the job.
        build_type: If your job is configured with parameters, you must use 'buildWithParameters' as build_type.

    Returns:
        The queue job number of the job.
    """
    return jenkins(ctx).build_item(fullname=fullname, build_type=build_type, params=params)
