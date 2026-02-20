import re
from collections.abc import Sequence
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.tools import Tool as FastMCPTool
from loguru import logger
from starlette.applications import Starlette
from starlette.middleware import Middleware as ASGIMiddleware

from mcp_jenkins.core import AuthMiddleware, LifespanContext, lifespan

__all__ = ['mcp']


class JenkinsMCP(FastMCP[LifespanContext]):
    async def list_tools(self, **kwargs: Any) -> Sequence[FastMCPTool]:  # noqa: ANN401
        """List available tools, filtering based on lifespan context (e.g. read-only mode)

        Returns:
            Filtered sequence of available tools
        """
        all_tools = list(await super().list_tools(**kwargs))

        request_context = self._mcp_server.request_context
        if request_context is None or request_context.lifespan_context is None:
            logger.warning('Lifespan context not available during list_tools call.')
            return all_tools

        jenkins_lifespan_context: LifespanContext = request_context.lifespan_context
        filtered_tools: list[FastMCPTool] = []

        for tool in all_tools:
            if not tool:
                continue

            if jenkins_lifespan_context.read_only and 'read' not in tool.tags:
                logger.debug(f'Excluding tool [{tool.name}] due to read-only mode')
                continue

            if jenkins_lifespan_context.tool_regex and not re.search(
                jenkins_lifespan_context.tool_regex, tool.name
            ):
                logger.debug(f'Excluding tool [{tool.name}] due to tool_regex filter')
                continue

            filtered_tools.append(tool)

        return filtered_tools

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

# Import tool modules to register them with the MCP server
# This must happen after mcp is created so the @mcp.tool() decorators can reference it
from mcp_jenkins.server import build, item, node, queue  # noqa: F401, E402
