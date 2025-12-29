import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Any

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_request
from mcp.types import AnyFunction
from starlette.requests import Request

from mcp_jenkins.jenkins import JenkinsClient


class JenkinsHeaderMiddleware:
    """ASGI-compliant middleware to extract Jenkins credentials from X-Jenkins-* headers."""
    
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """ASGI-compliant middleware following official ASGI specification."""
        import sys
        
        if scope["type"] != "http":
            # For non-HTTP requests, pass through directly
            await self.app(scope, receive, send)
            return

        # Ensure state exists in scope (don't copy, modify in place)
        if "state" not in scope:
            scope["state"] = {}

        # Parse headers from scope (headers are byte tuples per ASGI spec)
        headers_bytes = dict(scope.get("headers", []))
        
        # Extract Jenkins headers
        jenkins_url_bytes = headers_bytes.get(b"x-jenkins-url")
        jenkins_username_bytes = headers_bytes.get(b"x-jenkins-username")
        jenkins_password_bytes = headers_bytes.get(b"x-jenkins-password")
        
        # Convert bytes to strings
        jenkins_url = jenkins_url_bytes.decode("latin-1") if jenkins_url_bytes else None
        jenkins_username = jenkins_username_bytes.decode("latin-1") if jenkins_username_bytes else None
        jenkins_password = jenkins_password_bytes.decode("latin-1") if jenkins_password_bytes else None
        
        # Store in scope state (modify in place so Starlette Request can access it)
        scope["state"]["jenkins_url"] = jenkins_url
        scope["state"]["jenkins_username"] = jenkins_username
        scope["state"]["jenkins_password"] = jenkins_password
        
        print(f"[JENKINS-MIDDLEWARE] Captured headers - URL: {jenkins_url}, Username: {jenkins_username}", file=sys.stderr)
        
        # Call next middleware/app with original scope (now modified)
        await self.app(scope, receive, send)


def client(ctx: Context) -> JenkinsClient:
    import sys
    
    # Try to get Jenkins credentials from request state (set by middleware)
    jenkins_url = None
    jenkins_username = None
    jenkins_password = None
    
    try:
        request: Request = get_http_request()
        print(f"[DEBUG] Got HTTP request: {request.url}", file=sys.stderr)
        print(f"[DEBUG] Request.state attributes: {dir(request.state)}", file=sys.stderr)
        
        # Access credentials from request.state (populated by JenkinsHeaderMiddleware)
        if hasattr(request.state, 'jenkins_url'):
            jenkins_url = request.state.jenkins_url
            jenkins_username = request.state.jenkins_username
            jenkins_password = request.state.jenkins_password
            print(f"[DEBUG] Credentials from request.state - URL: {jenkins_url}, Username: {jenkins_username}", file=sys.stderr)
        else:
            print(f"[DEBUG] request.state does not have jenkins_url attribute", file=sys.stderr)
    except Exception as e:
        print(f"[DEBUG] No HTTP request context available (normal during initialization): {e}", file=sys.stderr)
    
    # Fallback to environment variables
    jenkins_url = jenkins_url or os.getenv('jenkins_url')
    jenkins_username = jenkins_username or os.getenv('jenkins_username')
    jenkins_password = jenkins_password or os.getenv('jenkins_password')
    jenkins_timeout = int(os.getenv('jenkins_timeout', 5))
    
    source = "headers" if hasattr(locals().get('request', None), 'state') and hasattr(getattr(locals().get('request', None), 'state', None), 'jenkins_url') else "environment variables"
    print(f"[DEBUG] Using credentials from: {source}", file=sys.stderr)
    print(f"[DEBUG] Final jenkins_url: {jenkins_url}", file=sys.stderr)
    print(f"[DEBUG] Final jenkins_username: {jenkins_username}", file=sys.stderr)
    print(f"[DEBUG] jenkins_password is set: {bool(jenkins_password)}", file=sys.stderr)

    if not all([jenkins_url, jenkins_username, jenkins_password]):
        raise ValueError(
            'Jenkins credentials not provided. '
            'Please provide them via X-Jenkins-* headers or CLI arguments (--jenkins-url, --jenkins-username, --jenkins-password).'
        )

    return JenkinsClient(
        url=jenkins_url,
        username=jenkins_username,
        password=jenkins_password,
        timeout=jenkins_timeout,
    )


class JenkinsMCP(FastMCP):
    """Custom FastMCP server class for Jenkins integration with header-based authentication."""

    def http_app(
        self,
        path: str | None = None,
        middleware: list | None = None,
        transport: Literal["streamable-http", "sse"] = "streamable-http",
        stateless_http: bool = False,
        **kwargs: Any,
    ):
        """Override http_app to add Jenkins header middleware."""
        from starlette.middleware import Middleware
        
        jenkins_mw = Middleware(JenkinsHeaderMiddleware)
        final_middleware_list = [jenkins_mw]
        if middleware:
            final_middleware_list.extend(middleware)
        
        return super().http_app(
            path=path,
            middleware=final_middleware_list,
            transport=transport,
            stateless_http=stateless_http,
            **kwargs,
        )


# Create MCP server
mcp = JenkinsMCP('mcp-jenkins')

# Import tool modules to register them with the MCP server
# This must happen after mcp is created so the @mcp.tool() decorators can reference it
from mcp_jenkins.server import build, job, node, queue_item  # noqa: E402, F401
