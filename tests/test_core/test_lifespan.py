import pytest

from mcp_jenkins.core.lifespan import jenkins, lifespan
from mcp_jenkins.jenkins import Jenkins


class TestLifespan:
    @pytest.fixture(autouse=True, scope='class')
    def mock_jenkins(self, class_mocker):
        class_mocker.patch(
            'mcp_jenkins.core.lifespan.jenkins',
            return_value=Jenkins(
                url='https://jenkins.example.com',
                username='username',
                password='password',
                timeout=5,
                verify_ssl=True,
            ),
        )

    @pytest.mark.asyncio
    async def test_lifespan_context(self, mocker):
        def getenv(key: str, default=None):
            env = {
                'jenkins_url': None,
                'jenkins_username': 'username',
                'jenkins_password': None,
                'jenkins_timeout': '5',
                'jenkins_verify_ssl': 'true',
                'read_only': 'true',
                'tool_regex': 'true',
                'jenkins_session_singleton': 'true',
            }
            return env.get(key, default)

        mocker.patch('mcp_jenkins.core.lifespan.os', mocker.Mock(getenv=getenv))
        async with lifespan(mocker.Mock) as context:
            assert context.jenkins_url is None
            assert context.jenkins_username == 'username'
            assert context.jenkins_password is None
            assert context.jenkins_timeout == 5
            assert context.jenkins_verify_ssl is True
            assert context.read_only is True
            assert context.tool_regex == 'true'
            assert context.jenkins_session_singleton is True


class TestJenkins:
    @pytest.fixture(autouse=True)
    def mock_jenkins(self, mocker):
        return mocker.patch('mcp_jenkins.core.lifespan.Jenkins')

    @pytest.fixture
    def mock_get_http_request(self, mocker):
        return mocker.patch('mcp_jenkins.core.lifespan.get_http_request')

    @pytest.fixture
    def mock_ctx(self, mocker):
        return mocker.Mock(
            request_context=mocker.Mock(
                lifespan_context=mocker.Mock(
                    jenkins_url='https://jenkins.example.com',
                    jenkins_username='username',
                    jenkins_password='password',
                    jenkins_timeout=5,
                    jenkins_verify_ssl=True,
                    jenkins_session_singleton=False,
                )
            )
        )

    def test_runtime_error(self, mock_jenkins, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError('Not available http request')

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com',
            username='username',
            password='password',
            timeout=5,
            verify_ssl=True,
        )

    def test_exception(self, mock_jenkins, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = Exception('Some other error')

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com',
            username='username',
            password='password',
            timeout=5,
            verify_ssl=True,
        )

    def test_retrieves_from_request_state(self, mock_jenkins, mock_get_http_request, mock_ctx, mocker):
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(
                jenkins_url='https://jenkins.fromrstate.com',
                jenkins_username='state-username',
                jenkins_password='state-password',
            )
        )

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.fromrstate.com',
            username='state-username',
            password='state-password',
            timeout=5,
            verify_ssl=True,
        )

    def test_missing_auth(self, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError('Not available http request')
        mock_ctx.request_context.lifespan_context.jenkins_username = None

        with pytest.raises(ValueError):
            jenkins(mock_ctx)

    def test_ctx_jenkins_exists(self, mock_jenkins, mock_get_http_request, mock_ctx, mocker):
        existing_jenkins = mocker.Mock()

        mock_ctx.request_context.lifespan_context.jenkins_session_singleton = True
        mock_ctx.session.jenkins = existing_jenkins

        assert jenkins(mock_ctx) == existing_jenkins
        mock_jenkins.assert_not_called()
