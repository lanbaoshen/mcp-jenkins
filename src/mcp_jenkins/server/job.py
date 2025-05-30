from mcp.server.fastmcp import Context

from mcp_jenkins.server import client, mcp


@mcp.tool()
async def get_all_jobs(ctx: Context) -> list[dict]:
    """
    Get all jobs from Jenkins

    Returns:
        list[dict]: A list of all jobs
    """
    return [job.model_dump(exclude_none=True) for job in client(ctx).job.get_all_jobs()]


@mcp.tool()
async def get_job_config(ctx: Context, fullname: str) -> str:
    """
    Get specific job config from Jenkins

    Args:
        fullname: The fullname of the job

    Returns:
        str: The config of the job
    """
    return client(ctx).job.get_job_config(fullname)


@mcp.tool()
async def search_jobs(
    ctx: Context,
    class_pattern: str = None,
    name_pattern: str = None,
    fullname_pattern: str = None,
    url_pattern: str = None,
    color_pattern: str = None,
) -> list[dict]:
    """
    Search job by specific field

    Args:
        class_pattern: The pattern of the _class
        name_pattern: The pattern of the name
        fullname_pattern: The pattern of the fullname
        url_pattern: The pattern of the url
        color_pattern: The pattern of the color

    Returns:
        list[dict]: A list of all jobs
    """
    return [
        job.model_dump(exclude_none=True)
        for job in client(ctx).job.search_jobs(
            class_pattern=class_pattern,
            name_pattern=name_pattern,
            fullname_pattern=fullname_pattern,
            url_pattern=url_pattern,
            color_pattern=color_pattern,
        )
    ]


@mcp.tool()
async def get_job_info(ctx: Context, fullname: str) -> dict:
    """
    Get specific job info from Jenkins

    Args:
        fullname: The fullname of the job

    Returns:
        dict: The job info
    """
    return client(ctx).job.get_job_info(fullname).model_dump(exclude_none=True)


@mcp.tool()
async def get_multibranch_jobs(
    ctx: Context, class_pattern: str = None, name_pattern: str = None, fullname_pattern: str = None
) -> list[dict]:
    """
    Get all multibranch pipeline jobs from Jenkins, optionally filtered by patterns

    Args:
        class_pattern: Optional regex pattern to filter by job class
        name_pattern: Optional regex pattern to filter by job name
        fullname_pattern: Optional regex pattern to filter by job fullname

    Returns:
        List[dict]: A list of multibranch pipeline jobs
    """
    # Set default class pattern to match multibranch pipelines if not specified
    if class_pattern is None:
        class_pattern = '.*WorkflowMultiBranchProject$'

    jobs = client(ctx).job.search_jobs(
        class_pattern=class_pattern,
        name_pattern=name_pattern,
        fullname_pattern=fullname_pattern,
    )

    return [job.model_dump(exclude_none=True) for job in jobs]


@mcp.tool()
async def get_multibranch_branches(ctx: Context, fullname: str) -> list[dict]:
    """
    Get all branches for a specific multibranch pipeline job

    Args:
        fullname: The fullname of the multibranch pipeline job

    Returns:
        List[dict]: A list of branch jobs within the multibranch pipeline
    """
    job_info = client(ctx).job.get_job_info(fullname)

    if not hasattr(job_info, 'jobs') or job_info.jobs is None:
        return []

    return [job.model_dump(exclude_none=True) for job in job_info.jobs]


@mcp.tool()
async def scan_multibranch_pipeline(ctx: Context, fullname: str) -> str:
    """
    Trigger a scan of a multibranch pipeline to discover new branches

    Args:
        fullname: The fullname of the multibranch pipeline job

    Returns:
        str: Status message indicating scan was triggered
    """
    jenkins = client(ctx)._jenkins

    # The API endpoint for scanning a multibranch pipeline
    scan_url = f'{jenkins.server}/job/{fullname.replace("/", "/job/")}/build?delay=0sec'

    # Use the jenkins_request method to perform the POST request
    response = jenkins.jenkins_request(requests_session=jenkins.requests, url=scan_url, method='POST')

    if response.status_code < 400:
        return f'Successfully triggered scan for multibranch pipeline: {fullname}'
    else:
        return f'Failed to trigger scan. Status code: {response.status_code}'
