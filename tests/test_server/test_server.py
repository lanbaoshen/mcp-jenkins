import pytest

from mcp_jenkins.server import JenkinsAuthMiddleware, client


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


class TestClient:
    @pytest.fixture(autouse=True)
    def mock_jenkins(self, mocker):
        return mocker.patch('mcp_jenkins.server.Jenkins')

    @pytest.fixture
    def mock_get_http_request(self, mocker):
        return mocker.patch('mcp_jenkins.server.get_http_request')

    @pytest.fixture
    def mock_os(self, mocker):
        def getenv(key: str, default=None):
            env = {
                'jenkins_url': 'https://jenkins.example.com',
                'jenkins_username': 'username',
                'jenkins_password': 'password',
            }
            return env.get(key, default)

        return mocker.patch('mcp_jenkins.server.os', mocker.Mock(getenv=getenv))

    def test_runtime_error(self, mock_jenkins, mock_get_http_request, mock_os, mocker):
        mock_get_http_request.side_effect = RuntimeError('Not available http request')

        client(mocker.Mock())

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com', username='username', password='password', timeout=5, verify_ssl=True
        )

    def test_exception(self, mock_jenkins, mock_get_http_request, mock_os, mocker):
        mock_get_http_request.side_effect = Exception('Some other error')

        client(mocker.Mock())

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com', username='username', password='password', timeout=5, verify_ssl=True
        )

    def test_retrieves_from_request_state(self, mock_jenkins, mock_get_http_request, mock_os, mocker):
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(
                jenkins_url='https://jenkins.fromrstate.com',
                jenkins_username='state-username',
                jenkins_password='state-password',
            )
        )

        client(mocker.Mock())

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.fromrstate.com',
            username='state-username',
            password='state-password',
            timeout=5,
            verify_ssl=True,
        )

    def test_missing_auth(self, mock_get_http_request, mocker):
        def getenv(key: str, default=None):
            env = {
                'jenkins_url': None,
                'jenkins_username': None,
                'jenkins_password': None,
                'jenkins_timeout': '5',
                'jenkins_verify_ssl': 'true',
            }
            return env.get(key, default)

        mock_get_http_request.side_effect = RuntimeError('Not available http request')
        mocker.patch('mcp_jenkins.server.os', mocker.Mock(getenv=getenv))

        with pytest.raises(ValueError):
            client(mocker.Mock())
