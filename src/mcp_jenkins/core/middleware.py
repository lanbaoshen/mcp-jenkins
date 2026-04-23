import time
from typing import Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from loguru import logger
from mcp.types import CallToolRequestParams
from starlette.types import ASGIApp, Receive, Scope, Send


def _username_from_context(fastmcp_context: Any) -> str:
    """Extract the Jenkins username from a FastMCP context, falling back to 'anonymous'."""
    try:
        # Try per-request auth header first (HTTP transport)
        from fastmcp.server.dependencies import get_http_request

        req = get_http_request()
        username = getattr(req.state, 'jenkins_username', None)
        if username:
            return username
    except Exception:  # noqa: BLE001
        pass

    try:
        # Fall back to lifespan-level credentials (env / CLI args)
        username = fastmcp_context.request_context.lifespan_context.jenkins_username
        if username:
            return username
    except Exception:  # noqa: BLE001
        pass

    return 'anonymous'


class MetricsMiddleware(Middleware):
    """FastMCP middleware that records per-tool Prometheus metrics.

    Tracks:
    * total tool invocations (``mcp_jenkins_tool_calls_total``)
    * tool execution duration (``mcp_jenkins_tool_duration_seconds``)
    * active concurrent calls (``mcp_jenkins_active_tool_calls``)
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, Any],
    ) -> Any:
        from mcp_jenkins.utils.prometheus_metrics import get_metrics

        metrics = get_metrics()
        tool_name: str = context.message.name
        username: str = _username_from_context(context.fastmcp_context)

        if metrics is not None:
            metrics.inc_active()

        start = time.perf_counter()
        status = 'success'
        try:
            result = await call_next(context)
            return result
        except Exception:
            status = 'error'
            raise
        finally:
            duration = time.perf_counter() - start
            if metrics is not None:
                metrics.record_tool_call(
                    tool_name=tool_name,
                    status=status,
                    username=username,
                    duration=duration,
                )
                metrics.dec_active()

            logger.debug(
                f'[METRICS] tool={tool_name} status={status} '
                f'duration={duration:.3f}s user={username}'
            )


class AuthMiddleware:
    """ASGI-compliant middleware to extract Jenkins auth from X-Jenkins-* headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Pass through non-HTTP requests directly per ASGI spec
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # According to ASGI spec, middleware should copy scope when modifying it
        scope_copy: Scope = dict(scope)

        # Ensure state exists in scope - this is where Starlette stores request state
        if 'state' not in scope_copy:
            scope_copy['state'] = {}

        # Parse headers from scope (headers are byte tuples per ASGI spec)
        headers = dict(scope_copy.get('headers', []))

        jenkins_url_bytes = headers.get(b'x-jenkins-url')
        jenkins_username_bytes = headers.get(b'x-jenkins-username')
        jenkins_password_bytes = headers.get(b'x-jenkins-password')

        # Convert bytes to strings (ASGI headers are always bytes)
        jenkins_url = jenkins_url_bytes.decode('latin-1') if jenkins_url_bytes else None
        jenkins_username = jenkins_username_bytes.decode('latin-1') if jenkins_username_bytes else None
        jenkins_password = jenkins_password_bytes.decode('latin-1') if jenkins_password_bytes else None

        # Store in scope state (modify in place so Starlette Request can access it)
        scope_copy['state']['jenkins_url'] = jenkins_url
        scope_copy['state']['jenkins_username'] = jenkins_username
        scope_copy['state']['jenkins_password'] = jenkins_password

        logger.debug(f'[JENKINS-AUTH-MIDDLEWARE] Captured headers - url: {jenkins_url}, username: {jenkins_username}')

        # Call the next application with modified scope and safe send wrapper
        await self.app(scope_copy, receive, send)
