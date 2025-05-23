from mcp.server.fastmcp import Context

from mcp_jenkins.server import client, mcp


@mcp.tool()
async def get_all_nodes(ctx: Context) -> list[dict]:
    """
    Get all nodes from Jenkins

    Returns:
        list[dict]: A list of all nodes
    """
    return [node.model_dump(exclude_none=True) for node in client(ctx).node.get_all_nodes()]


@mcp.tool()
async def get_node_config(ctx: Context, name: str) -> str:
    """
    Get node config from Jenkins

    Args:
        name: The name of the node

    Returns:
        str: The config of the node
    """
    return client(ctx).node.get_node_config(name)
