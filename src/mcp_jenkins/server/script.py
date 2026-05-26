from fastmcp import Context

from mcp_jenkins.core.lifespan import jenkins
from mcp_jenkins.server import mcp


@mcp.tool(tags={'write'})
async def run_groovy_script(ctx: Context, script: str) -> str:
    """Execute an arbitrary Groovy script on Jenkins.

    This tool provides access to Jenkins internal features that are not available via REST API.

    Args:
        script: The Groovy script code to execute.

    Returns:
        The result of the script execution.

    Examples:
        # Basic usage:
        run_groovy_script(script='println Jenkins.instance.version')

        # Access Jenkins information:
        run_groovy_script(
            script='''
                def version = Jenkins.instance.version
                def mode = Jenkins.instance.mode
                return "Version: ${version}, Mode: ${mode}"
            '''
        )
    """
    return jenkins(ctx).run_script(script=script)
