from fastmcp import Context

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.server import mcp


@mcp.tool(tags=['read'])
async def get_build_log_progressive(
    ctx: Context,
    fullname: str,
    number: int | None = None,
    start: int = 0,
) -> dict:
    """Get build console output with byte-offset pagination.

    Unlike get_build_console_output which returns the full log at once, this tool
    supports incremental retrieval via the start parameter — useful for large build
    logs that are impractical to fetch in a single request.

    Args:
        fullname: The fullname of the job
        number: The build number. If None, uses the last build.
        start: Byte offset to start reading from. Use 0 for the beginning,
               or the next_start value from a previous response to continue.

    Returns:
        A dict with 'output' (log text from the given offset), 'next_start'
        (byte offset for the next request), and 'has_more_data' (whether
        more output is available, e.g. the build is still running).
    """
    if number is None:
        number = jenkins(ctx).get_item(fullname=fullname, depth=1).lastBuild.number

    return jenkins(ctx).get_build_console_output_progressive(fullname=fullname, number=number, start=start)
