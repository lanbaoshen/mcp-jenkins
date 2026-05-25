from typing import Any, Literal

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware as ASGIMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mcp_jenkins.core import AuthMiddleware, LifespanContext, lifespan

__all__ = ['mcp']


class JenkinsMCP(FastMCP[LifespanContext]):
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


@mcp.custom_route('/healthz', methods=['GET'])
async def healthz(_request: Request) -> PlainTextResponse:
    """Liveness probe endpoint. Always returns 200 for kubernetes health checks."""
    return PlainTextResponse('OK', status_code=200)


# Import tool modules to register them with the MCP server
# This must happen after mcp is created so the @mcp.tool() decorators can reference it
from mcp_jenkins.server import build, item, node, plugin, queue, view  # noqa: F401, E402
