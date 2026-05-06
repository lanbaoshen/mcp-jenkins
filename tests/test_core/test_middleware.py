import pytest

from mcp_jenkins.core import AuthMiddleware


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_call(self, mocker):
        mock_app, mock_receive, mock_send = (
            mocker.AsyncMock(),
            mocker.AsyncMock(),
            mocker.AsyncMock(),
        )
        middleware = AuthMiddleware(mock_app)

        scope = {
            'type': 'http',
            'headers': [
                (b'x-jenkins-url', b'https://jenkins.example.com'),
                (b'x-jenkins-username', b'username'),
                (b'x-jenkins-password', b'password'),
                (b'user-agent', b'copilot/1.0.34 (win32)'),
            ],
        }

        await middleware(scope, mock_receive, mock_send)

        args, kwargs = mock_app.call_args
        called_scope, called_receive, called_send = args
        assert called_scope == {
            'type': 'http',
            'headers': [
                (b'x-jenkins-url', b'https://jenkins.example.com'),
                (b'x-jenkins-username', b'username'),
                (b'x-jenkins-password', b'password'),
                (b'user-agent', b'copilot/1.0.34 (win32)'),
            ],
            'state': {
                'jenkins_url': 'https://jenkins.example.com',
                'jenkins_username': 'username',
                'jenkins_password': 'password',
                'user_agent': 'copilot/1.0.34 (win32)',
            },
        }
        assert called_receive is mock_receive
        assert callable(called_send)

    @pytest.mark.asyncio
    async def test_call_missing_headers(self, mocker):
        mock_app, mock_receive, mock_send = (
            mocker.AsyncMock(),
            mocker.AsyncMock(),
            mocker.AsyncMock(),
        )
        middleware = AuthMiddleware(mock_app)

        scope = {
            'type': 'http',
        }

        await middleware(scope, mock_receive, mock_send)

        args, kwargs = mock_app.call_args
        called_scope, called_receive, called_send = args
        assert called_scope == {
            'type': 'http',
            'state': {
                'jenkins_url': None,
                'jenkins_username': None,
                'jenkins_password': None,
                'user_agent': 'unknown',
            },
        }
        assert called_receive is mock_receive
        assert callable(called_send)

    @pytest.mark.asyncio
    async def test_call_non_http(self, mocker):
        mock_app, mock_receive, mock_send = (
            mocker.AsyncMock(),
            mocker.AsyncMock(),
            mocker.AsyncMock(),
        )
        middleware = AuthMiddleware(mock_app)

        scope = {
            'type': 'websocket',
        }

        await middleware(scope, mock_receive, mock_send)

        mock_app.assert_called_once_with(scope, mock_receive, mock_send)
