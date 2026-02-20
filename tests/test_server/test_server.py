import pytest

from mcp_jenkins.server import JenkinsMCP


class TestJenkinsMCP:
    @pytest.mark.asyncio
    async def test_list_tools(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=False, tool_regex=''))),
        )

        read_tool = mocker.Mock(name='read_tool', tags={'read'})
        read_tool.name = 'read_tool'
        write_tool = mocker.Mock(name='write_tool', tags={'write'})
        write_tool.name = 'write_tool'

        parent_list_tools = mocker.patch(
            'fastmcp.FastMCP.list_tools',
            new_callable=mocker.AsyncMock,
            return_value=[read_tool, write_tool],
        )

        tools = await jm.list_tools()
        assert tools == [read_tool, write_tool]

    @pytest.mark.asyncio
    async def test_list_tools_read_only(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=True, tool_regex=''))),
        )

        read_tool = mocker.Mock(name='read_tool', tags={'read'})
        read_tool.name = 'read_tool'
        write_tool = mocker.Mock(name='write_tool', tags={'write'})
        write_tool.name = 'write_tool'

        mocker.patch(
            'fastmcp.FastMCP.list_tools',
            new_callable=mocker.AsyncMock,
            return_value=[read_tool, write_tool],
        )

        tools = await jm.list_tools()
        assert tools == [read_tool]

    @pytest.mark.asyncio
    async def test_list_tools_not_tool(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=False, tool_regex=''))),
        )

        write_tool = mocker.Mock(name='write_tool', tags={'write'})
        write_tool.name = 'write_tool'

        mocker.patch(
            'fastmcp.FastMCP.list_tools',
            new_callable=mocker.AsyncMock,
            return_value=[None, write_tool],
        )

        tools = await jm.list_tools()
        assert tools == [write_tool]

    @pytest.mark.asyncio
    async def test_list_tools_no_context(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(jm, '_mcp_server', mocker.Mock(request_context=None))

        read_tool = mocker.Mock(name='read_tool', tags={'read'})
        read_tool.name = 'read_tool'

        mocker.patch(
            'fastmcp.FastMCP.list_tools',
            new_callable=mocker.AsyncMock,
            return_value=[read_tool],
        )

        tools = await jm.list_tools()
        assert tools == [read_tool]

    @pytest.mark.asyncio
    async def test_list_tools_regex(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(
                request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=False, tool_regex='^read_.*$'))
            ),
        )

        read_tool = mocker.Mock(name='read_tool', tags={'read'})
        read_tool.name = 'read_tool'
        write_tool = mocker.Mock(name='write_tool', tags={'write'})
        write_tool.name = 'write_tool'

        mocker.patch(
            'fastmcp.FastMCP.list_tools',
            new_callable=mocker.AsyncMock,
            return_value=[read_tool, write_tool],
        )

        tools = await jm.list_tools()
        assert tools == [read_tool]

    @pytest.mark.asyncio
    async def test_list_tools_regex_no_match(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')
        mocker.patch.object(
            jm,
            '_mcp_server',
            mocker.Mock(
                request_context=mocker.Mock(lifespan_context=mocker.Mock(read_only=True, tool_regex='^nonexistent_.*$'))
            ),
        )

        read_tool = mocker.Mock(name='read_tool', tags={'read'})
        read_tool.name = 'read_tool'
        write_tool = mocker.Mock(name='write_tool', tags={'write'})
        write_tool.name = 'write_tool'

        mocker.patch(
            'fastmcp.FastMCP.list_tools',
            new_callable=mocker.AsyncMock,
            return_value=[read_tool, write_tool],
        )

        tools = await jm.list_tools()
        assert tools == []

    def test_http_app(self, mocker):
        jm = JenkinsMCP('mcp-jenkins-test')

        mock_wm = mocker.Mock()
        mocker.patch('mcp_jenkins.server.ASGIMiddleware', return_value=mock_wm)

        assert jm.http_app(path='/mcp', middleware=[mock_wm], transport='http').user_middleware.count(mock_wm) == 2
