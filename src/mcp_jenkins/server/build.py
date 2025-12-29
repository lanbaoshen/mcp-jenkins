from typing import Literal

from jenkins import JenkinsException
from fastmcp import Context

from mcp_jenkins.server import client, mcp


@mcp.tool(tags={"jenkins", "read"})
async def get_running_builds(ctx: Context) -> list[dict]:
    """
    Get all running builds from Jenkins

    Returns:
        list[dict]: A list of all running builds
    """
    return [build.model_dump(exclude_none=True) for build in client(ctx).build.get_running_builds()]


@mcp.tool(tags={"jenkins", "read"})
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


@mcp.tool(tags={"jenkins", "read"})
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


@mcp.tool(tags={"jenkins", "write"})
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


@mcp.tool(tags={"jenkins", "read"})
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


@mcp.tool(tags={"jenkins", "write"})
async def stop_build(ctx: Context, fullname: str, build_number: int) -> None:
    """
    Stop a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        build_number: The number of the build to stop
    """
    return client(ctx).build.stop_build(fullname, build_number)


@mcp.tool(tags={"jenkins", "read"})
async def get_test_results(
    ctx: Context,
    fullname: str,
    build_number: int | None = None,
    status_filter: list[Literal['PASSED', 'SKIPPED', 'FAILED', 'FIXED', 'REGRESSION']] | None = None,
) -> dict:
    """
    Get test results from a specific build in Jenkins

    Args:
        fullname: The fullname of the job
        build_number: The number of the build, if None, get the last build
        status_filter: Filter test cases by status. Can be one or more of: PASSED, SKIPPED, FAILED, FIXED, REGRESSION

    Returns:
        dict: The test results including pass/fail counts and detailed test case information
    """
    if build_number is None:
        build_number = client(ctx).job.get_job_info(fullname).lastBuild.number

    try:
        test_report = client(ctx).build.get_test_report(fullname, build_number)
    except JenkinsException:
        # Return empty test results if no test report is available
        return {'failCount': 0, 'skipCount': 0, 'passCount': 0, 'totalCount': 0, 'duration': 0.0, 'suites': []}

    # If test_report is None, return empty results
    if test_report is None:
        return {'failCount': 0, 'skipCount': 0, 'passCount': 0, 'totalCount': 0, 'duration': 0.0, 'suites': []}

    # Apply status filtering if specified
    if status_filter:
        # Create a new test report with filtered test cases
        filtered_suites = []
        filtered_fail_count = 0
        filtered_skip_count = 0
        filtered_pass_count = 0
        filtered_total_count = 0

        for suite in test_report.suites:
            filtered_cases = [case for case in suite.cases if case.status in status_filter]

            if filtered_cases:  # Only include suites that have matching test cases
                # Count test results in filtered cases
                for case in filtered_cases:
                    if case.status == 'PASSED':
                        filtered_pass_count += 1
                    elif case.status == 'FAILED' or case.status == 'REGRESSION':
                        filtered_fail_count += 1
                    elif case.status == 'SKIPPED':
                        filtered_skip_count += 1
                    elif case.status == 'FIXED':
                        filtered_pass_count += 1  # FIXED tests are considered passing
                    filtered_total_count += 1

                # Create a new suite with filtered cases
                filtered_suite = suite.model_copy()
                filtered_suite.cases = filtered_cases
                filtered_suites.append(filtered_suite)

        # Create a new test report with filtered data
        filtered_report = test_report.model_copy()
        filtered_report.suites = filtered_suites
        filtered_report.failCount = filtered_fail_count
        filtered_report.skipCount = filtered_skip_count
        filtered_report.passCount = filtered_pass_count
        filtered_report.totalCount = filtered_total_count

        return filtered_report.model_dump(exclude_none=True)

    return test_report.model_dump(exclude_none=True)
