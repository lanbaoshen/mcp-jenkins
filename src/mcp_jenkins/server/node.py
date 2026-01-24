from fastmcp import Context

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.server import mcp


@mcp.tool(tags=['read'])
async def get_all_nodes(ctx: Context) -> list[dict]:
    """Get all nodes from Jenkins

    Returns:
        A list of all nodes
    """
    return [node.model_dump(exclude={'executors'}) for node in jenkins(ctx).get_nodes(depth=0)]


@mcp.tool(tags=['read'])
async def get_node(ctx: Context, name: str) -> dict:
    """Get a specific node from Jenkins

    Contains executor about the node.

    Args:
        name: The name of the node

    Returns:
        The node
    """
    return jenkins(ctx).get_node(name=name, depth=2).model_dump(exclude_none=True)


@mcp.tool(tags=['read'])
async def get_node_config(ctx: Context, name: str) -> str:
    """Get node config from Jenkins

    Args:
        name: The name of the node

    Returns:
        The config of the node
    """
    return jenkins(ctx).get_node_config(name=name)


@mcp.tool(tags=['write'])
async def update_node_config(ctx: Context, name: str, config: str) -> None:
    """Update node configuration in Jenkins

    Args:
        name: The name of the node
        config: The new configuration as an XML string
    """
    jenkins(ctx).update_node_config(name=name, config=config)
