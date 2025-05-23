from mcp.server.fastmcp import Context

from mcp_jenkins.server import client, mcp


@mcp.tool()
async def get_all_queue_items(ctx: Context) -> list[dict]:
    """
    Get all items in Jenkins queue

    Returns:
        list[dict]: A list of all items in the Jenkins queue
    """
    return [item.model_dump(exclude_none=True) for item in client(ctx).queue_item.get_all_queue_items()]


@mcp.tool()
async def get_queue_item(ctx: Context, id_: int) -> dict:
    """
    Get a specific item in Jenkins queue

    Args:
        id_: The id of the queue item

    Returns:
        dict: The queue item
    """
    return client(ctx).queue_item.get_queue_item(id_).model_dump(exclude_none=True)


@mcp.tool()
async def cancel_queue_item(ctx: Context, id_: int) -> None:
    """
    Cancel a specific item in Jenkins queue

    Args:
        id_: The id of the queue item
    """
    client(ctx).queue_item.cancel_queue_item(id_)
