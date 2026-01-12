import re
from typing import Any, Literal

from fastmcp import Context, FastMCP
from fastmcp.tools import Tool as FastMCPTool
from loguru import logger
from mcp.types import Tool as MCPTool
from starlette.applications import Starlette
from starlette.middleware import Middleware as ASGIMiddleware

from mcp_jenkins.core import AuthMiddleware, LifespanContext, lifespan
from mcp_jenkins.jenkins import Jenkins

__all__ = ['mcp', 'jenkins']


class JenkinsMCP(FastMCP):
    async def _list_tools_mcp(self) -> list[MCPTool]:
        """List available tools, filtering based on lifespan context (e.g. read-only mode)

        Returns:
            List of available mcp tools
        """
        request_context = self._mcp_server.request_context

        if request_context is None or request_context.lifespan_context is None:
            logger.warning('Lifespan context not available during _list_tools_mcp call.')
            return []

        jenkins_lifespan_context: LifespanContext = request_context.lifespan_context

        all_tools: dict[str, FastMCPTool] = await self.get_tools()
        mcp_tools: list[MCPTool] = []

        for registered_name, tool in all_tools.items():
            if not tool:
                continue

            if jenkins_lifespan_context.read_only and 'read' not in tool.tags:
                logger.debug(f'Excluding tool [{registered_name}] due to read-only mode')
                continue

            if jenkins_lifespan_context.tool_regex and not re.match(
                jenkins_lifespan_context.tool_regex, registered_name
            ):
                logger.debug(f'Excluding tool [{registered_name}] due to tool_regex filter')
                continue

            mcp_tools.append(tool.to_mcp_tool(name=registered_name))

        return mcp_tools

    def http_app(
        self,
        path: str | None = None,
        middleware: list[ASGIMiddleware] | None = None,
        transport: Literal['http', 'streamable-http', 'sse'] = 'http',
        **kwargs: Any,  # noqa: ANN401
    ) -> 'Starlette':
        """Override to add JenkinsAuthMiddleware"""
        jenkins_auth_mw = ASGIMiddleware(AuthMiddleware)

        final_middleware_list = [jenkins_auth_mw]
        if middleware:
            final_middleware_list.extend(middleware)

        return super().http_app(path=path, middleware=final_middleware_list, transport=transport, **kwargs)


mcp = JenkinsMCP('mcp-jenkins', lifespan=lifespan)


def jenkins(ctx: Context) -> 'Jenkins':
    return ctx.request_context.lifespan_context.jenkins


# Import tool modules to register them with the MCP server
# This must happen after mcp is created so the @mcp.tool() decorators can reference it
