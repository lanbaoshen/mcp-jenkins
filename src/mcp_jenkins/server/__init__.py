from typing import Any, Literal

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware as ASGIMiddleware
from starlette.requests import Request
from starlette.responses import Response

from mcp_jenkins.core import AuthMiddleware, LifespanContext, MetricsMiddleware, lifespan

__all__ = ['mcp', 'metrics_endpoint']


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

# Register the FastMCP-level metrics middleware (tracks per-tool calls)
mcp.add_middleware(MetricsMiddleware())


# /metrics endpoint – serves Prometheus scrape output
@mcp.custom_route('/metrics', methods=['GET'])
async def metrics_endpoint(request: Request) -> Response:
    from mcp_jenkins.utils.prometheus_metrics import get_metrics

    m = get_metrics()
    if m is None:
        return Response(
            content='# Metrics not initialised yet.\n',
            media_type='text/plain; charset=utf-8',
            status_code=503,
        )
    content, content_type = m.generate_metrics()
    return Response(content=content, media_type=content_type)


# Import tool modules to register them with the MCP server
# This must happen after mcp is created so the @mcp.tool() decorators can reference it
from mcp_jenkins.server import build, item, node, plugin, queue, view  # noqa: F401, E402
