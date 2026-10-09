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

    def test_url_only_creates_anonymous_client(self, mock_jenkins, mock_get_http_request, mock_ctx, mocker):
        mock_logger = mocker.patch('mcp_jenkins.core.lifespan.logger')
        mock_get_http_request.side_effect = RuntimeError('Not available http request')
        mock_ctx.request_context.lifespan_context.jenkins_username = None
        mock_ctx.request_context.lifespan_context.jenkins_password = None

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com',
            username=None,
            password=None,
            timeout=5,
            verify_ssl=True,
        )
        mock_logger.info.assert_any_call(
            'No Jenkins credentials provided, accessing https://jenkins.example.com anonymously'
        )

    def test_empty_credentials_mean_anonymous(self, mock_jenkins, mock_get_http_request, mock_ctx, mocker):
        mock_logger = mocker.patch('mcp_jenkins.core.lifespan.logger')
        mock_get_http_request.side_effect = RuntimeError('Not available http request')
        mock_ctx.request_context.lifespan_context.jenkins_username = ''
        mock_ctx.request_context.lifespan_context.jenkins_password = ''

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once()
        mock_logger.info.assert_any_call(
            'No Jenkins credentials provided, accessing https://jenkins.example.com anonymously'
        )

    def test_username_without_password(self, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError('Not available http request')
        mock_ctx.request_context.lifespan_context.jenkins_password = None

        with pytest.raises(ValueError, match='username and password must be provided together'):
            jenkins(mock_ctx)

    def test_missing_url(self, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError('Not available http request')
        mock_ctx.request_context.lifespan_context.jenkins_url = None

        with pytest.raises(ValueError, match='the URL is required'):
            jenkins(mock_ctx)

    def test_username_from_env_password_from_header(self, mock_jenkins, mock_get_http_request, mock_ctx, mocker):
        mock_ctx.request_context.lifespan_context.jenkins_password = None
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(
                jenkins_url=None,
                jenkins_username=None,
                jenkins_password='header-password',
            )
        )

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com',
            username='username',
            password='header-password',
            timeout=5,
            verify_ssl=True,
        )

    def test_ctx_jenkins_exists(self, mock_jenkins, mock_get_http_request, mock_ctx, mocker):
        existing_jenkins = mocker.Mock()

        mock_ctx.request_context.lifespan_context.jenkins_session_singleton = True
        mock_ctx.session.jenkins = existing_jenkins

        assert jenkins(mock_ctx) == existing_jenkins
        mock_jenkins.assert_not_called()
