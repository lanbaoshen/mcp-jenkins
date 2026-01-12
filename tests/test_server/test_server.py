import pytest

from mcp_jenkins.server import JenkinsMCP, jenkins


class TestJenkinsMCP:
    @pytest.mark.asyncio
    async def test_list_tools_mcp(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=False, tool_regex=''))),
        )
        mocker.patch.object(
            jm,
            'get_tools',
            return_value=mocker.AsyncMock(
                items=lambda: {
                    'read_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='read_tool_obj'), tags=['read']),
                    'write_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='write_tool_obj'), tags=['write']),
                }.items()
            ),
        )
        tools = await jm._list_tools_mcp()
        assert tools == ['read_tool_obj', 'write_tool_obj']

    @pytest.mark.asyncio
    async def test_list_tools_mcp_read_only(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=True, tool_regex=''))),
        )
        mocker.patch.object(
            jm,
            'get_tools',
            return_value=mocker.AsyncMock(
                items=lambda: {
                    'read_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='read_tool_obj'), tags=['read']),
                    'write_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='write_tool_obj'), tags=['write']),
                }.items()
            ),
        )
        tools = await jm._list_tools_mcp()
        assert tools == ['read_tool_obj']

    @pytest.mark.asyncio
    async def test_list_tools_mcp_not_tool(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=False, tool_regex=''))),
        )
        mocker.patch.object(
            jm,
            'get_tools',
            return_value=mocker.AsyncMock(
                items=lambda: {
                    'none': None,
                    'write_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='write_tool_obj'), tags=['write']),
                }.items()
            ),
        )
        tools = await jm._list_tools_mcp()
        assert tools == ['write_tool_obj']

    @pytest.mark.asyncio
    async def test_list_tools_mcp_no_context(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(jm, '_mcp_server', mocker.Mock(request_context=None))
        tools = await jm._list_tools_mcp()
        assert tools == []

    @pytest.mark.asyncio
    async def test_list_tools_mcp_regex(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(
                request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=False, tool_regex='^read_.*$'))
            ),
        )
        mocker.patch.object(
            jm,
            'get_tools',
            return_value=mocker.AsyncMock(
                items=lambda: {
                    'read_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='read_tool_obj'), tags=['read']),
                    'write_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='write_tool_obj'), tags=['write']),
                }.items()
            ),
        )
        tools = await jm._list_tools_mcp()
        assert tools == ['read_tool_obj']

    @pytest.mark.asyncio
    async def test_list_tools_mcp_regex_no_match(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(
                request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=True, tool_regex='^nonexistent_.*$'))
            ),
        )
        mocker.patch.object(
            jm,
            'get_tools',
            return_value=mocker.AsyncMock(
                items=lambda: {
                    'read_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='read_tool_obj'), tags=['read']),
                    'write_tool': mocker.Mock(to_mcp_tool=mocker.Mock(return_value='write_tool_obj'), tags=['write']),
                }.items()
            ),
        )
        tools = await jm._list_tools_mcp()
        assert tools == []

    def test_http_app(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')

        mock_wm = mocker.Mock()
        mocker.patch('mcp_jenkins.server.ASGIMiddleware', return_value=mock_wm)

        assert jm.http_app(path='/mcp', middleware=[mock_wm], transport='http').user_middleware.count(mock_wm) == 2


def test_jenkins(mocker):
    mock_jenkins = mocker.Mock()
    assert (
        jenkins(mocker.Mock(request_context=mocker.Mock(lifespan_context=mocker.Mock(jenkins=mock_jenkins))))
        == mock_jenkins
    )
