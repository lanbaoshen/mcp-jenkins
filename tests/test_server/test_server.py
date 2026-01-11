import pytest

from mcp_jenkins.server import JenkinsAuthMiddleware


class TestJenkinsAuthMiddleware:
    @pytest.mark.asyncio
    async def test_call(self, mocker):
        mock_app, mock_receive, mock_send = mocker.AsyncMock(), mocker.AsyncMock(), mocker.AsyncMock()
        middleware = JenkinsAuthMiddleware(mock_app)

        scope = {
            'type': 'http',
            'headers': [
                (b'x-jenkins-url', b'https://jenkins.example.com'),
                (b'x-jenkins-username', b'username'),
                (b'x-jenkins-password', b'password'),
            ],
        }

        await middleware(scope, mock_receive, mock_send)

        mock_app.assert_called_once_with(
            {
                'type': 'http',
                'headers': [
                    (b'x-jenkins-url', b'https://jenkins.example.com'),
                    (b'x-jenkins-username', b'username'),
                    (b'x-jenkins-password', b'password'),
                ],
                'state': {
                    'jenkins_url': 'https://jenkins.example.com',
                    'jenkins_username': 'username',
                    'jenkins_password': 'password',
                },
            },
            mock_receive,
            mock_send,
        )

    @pytest.mark.asyncio
    async def test_call_missing_headers(self, mocker):
        mock_app, mock_receive, mock_send = mocker.AsyncMock(), mocker.AsyncMock(), mocker.AsyncMock()
        middleware = JenkinsAuthMiddleware(mock_app)

        scope = {
            'type': 'http',
        }

        await middleware(scope, mock_receive, mock_send)

        mock_app.assert_called_once_with(
            {
                'type': 'http',
                'state': {
                    'jenkins_url': None,
                    'jenkins_username': None,
                    'jenkins_password': None,
                },
            },
            mock_receive,
            mock_send,
        )

    @pytest.mark.asyncio
    async def test_call_non_http(self, mocker):
        mock_app, mock_receive, mock_send = mocker.AsyncMock(), mocker.AsyncMock(), mocker.AsyncMock()
        middleware = JenkinsAuthMiddleware(mock_app)

        scope = {
            'type': 'websocket',
        }

        await middleware(scope, mock_receive, mock_send)

        mock_app.assert_called_once_with(scope, mock_receive, mock_send)
