from click.testing import CliRunner

from mcp_jenkins import main


def test_main_stdio(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(main, ['--transport', 'stdio'])

    mock_mcp.run_async.assert_called_once_with(transport='stdio')


def test_main_sse(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(main, ['--transport', 'sse', '--host', '127.0.0.1', '--port', '9887'])
    mock_mcp.run_async.assert_called_once_with(transport='sse', host='127.0.0.1', port=9887)


def test_main_streamable_http(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(main, ['--transport', 'streamable-http', '--host', '127.0.0.1', '--port', '9887'])
    mock_mcp.run_async.assert_called_once_with(transport='streamable-http', host='127.0.0.1', port=9887)


def test_main(mocker):
    mocker.patch('mcp_jenkins.asyncio')
    mock_mcp = mocker.patch('mcp_jenkins.server.mcp')

    CliRunner().invoke(
        main,
        [
            '--transport',
            'stdio',
            '--jenkins-url',
            'https://example.com',
            '--jenkins-username',
            'username',
            '--jenkins-password',
            'password',
            '--jenkins-timeout',
            '30',
        ],
    )

    mock_mcp.run_async.assert_called_once_with(transport='stdio')
