import pytest
from pydantic import HttpUrl

from mcp_jenkins.core.lifespan import _jenkins, lifespan
from mcp_jenkins.jenkins.rest_client import Jenkins


class TestLifespan:
    @pytest.fixture(autouse=True, scope='class')
    def mock_jenkins(self, class_mocker):
        class_mocker.patch(
            'mcp_jenkins.core.lifespan._jenkins',
            return_value=Jenkins(
                url=HttpUrl('https://jenkins.example.com'),
                username='username',
                password='password',
                timeout=5,
                verify_ssl=True,
            ),
        )

    @pytest.mark.asyncio
    async def test_lifespan_context(self, mocker):
        mocker.patch('mcp_jenkins.core.lifespan.os', mocker.Mock(getenv=lambda key, default: 'true'))
        async with lifespan(mocker.Mock) as context:
            assert context.read_only is True


class TestJenkins:
    @pytest.fixture(autouse=True)
    def mock_jenkins(self, mocker):
        return mocker.patch('mcp_jenkins.core.lifespan.Jenkins')

    @pytest.fixture
    def mock_get_http_request(self, mocker):
        return mocker.patch('mcp_jenkins.core.lifespan.get_http_request')

    @pytest.fixture
    def mock_os(self, mocker):
        def getenv(key: str, default=None):
            env = {
                'jenkins_url': 'https://jenkins.example.com',
                'jenkins_username': 'username',
                'jenkins_password': 'password',
            }
            return env.get(key, default)

        return mocker.patch('mcp_jenkins.core.lifespan.os', mocker.Mock(getenv=getenv))

    def test_runtime_error(self, mock_jenkins, mock_get_http_request, mock_os, mocker):
        mock_get_http_request.side_effect = RuntimeError('Not available http request')

        _jenkins()

        mock_jenkins.assert_called_once_with(
            url=HttpUrl('https://jenkins.example.com'),
            username='username',
            password='password',
            timeout=5,
            verify_ssl=True,
        )

    def test_exception(self, mock_jenkins, mock_get_http_request, mock_os, mocker):
        mock_get_http_request.side_effect = Exception('Some other error')

        _jenkins()

        mock_jenkins.assert_called_once_with(
            url=HttpUrl('https://jenkins.example.com'),
            username='username',
            password='password',
            timeout=5,
            verify_ssl=True,
        )

    def test_retrieves_from_request_state(self, mock_jenkins, mock_get_http_request, mock_os, mocker):
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(
                jenkins_url='https://jenkins.fromrstate.com',
                jenkins_username='state-username',
                jenkins_password='state-password',
            )
        )

        _jenkins()

        mock_jenkins.assert_called_once_with(
            url=HttpUrl('https://jenkins.fromrstate.com'),
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
        mocker.patch('mcp_jenkins.core.lifespan.os', mocker.Mock(getenv=getenv))

        with pytest.raises(ValueError):
            _jenkins()
