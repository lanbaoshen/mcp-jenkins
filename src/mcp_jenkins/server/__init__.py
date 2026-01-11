from loguru import logger
from starlette.types import ASGIApp, Receive, Scope, Send


class JenkinsAuthMiddleware:
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
