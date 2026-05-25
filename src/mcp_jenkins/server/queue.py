import asyncio
import time

from fastmcp import Context

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.server import mcp


@mcp.tool(tags=['read'])
async def get_all_queue_items(ctx: Context) -> list[dict]:
    """Get all items in Jenkins queue

    Returns:
        A list of all items in the Jenkins queue
    """
    return [item.model_dump(exclude_none=True, exclude={'task'}) for item in jenkins(ctx).get_queue().items]


@mcp.tool(tags=['read'])
async def get_queue_item(ctx: Context, id: int) -> dict:
    """Get a specific item in Jenkins queue by id

    Args:
        id: The id of the queue item

    Returns:
        The queue item
    """
    item = jenkins(ctx).get_queue_item(id=id, depth=1)
    return item.model_dump(exclude_none=True)


@mcp.tool(tags=['write'])
async def cancel_queue_item(ctx: Context, id: int) -> None:
    """Cancel a specific item in Jenkins queue by id

    Args:
        id: The id of the queue item
    """
    jenkins(ctx).cancel_queue_item(id=id)


@mcp.tool(tags=['read'])
async def get_queue_to_build(
    ctx: Context,
    queue_item_id: int,
    timeout: int = 600,
    poll_interval: int = 5,
) -> dict:
    """Poll the Jenkins queue until a build is assigned to the queue item.

    Server-side polling — agent calls once, gets result when build is assigned or timeout.

    Args:
        queue_item_id: The queue item ID returned by build_item()
        timeout: Max seconds to wait (default: 600)
        poll_interval: Seconds between polls (default: 5)

    Returns:
        Dict with status and build_number if completed, or TIMED_OUT with elapsed_seconds.
    """
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            return {
                'status': 'TIMED_OUT',
                'queue_item_id': queue_item_id,
                'elapsed_seconds': int(elapsed),
            }

        queue_item = jenkins(ctx).get_queue_item_raw(id=queue_item_id)

        build_info = queue_item.get('build')
        if build_info:
            build_number = build_info.get('number')
            return {
                'status': 'COMPLETED',
                'build_number': build_number,
                'queue_item_id': queue_item_id,
                'elapsed_seconds': int(elapsed),
            }

        await asyncio.sleep(poll_interval)
