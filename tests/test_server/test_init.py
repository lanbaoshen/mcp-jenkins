import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

# 设置必要的环境变量以避免导入错误
os.environ['tool_alias'] = '[fn]'

from mcp_jenkins import main


def test_transport_streamable_http_valid():
    """测试transport参数接受'streamable-http'值"""
    with patch('mcp_jenkins.jenkins.JenkinsClient'), patch('mcp_jenkins.server.mcp') as mock_mcp:
        mock_mcp.run = MagicMock()
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                '--jenkins-url',
                'http://localhost',
                '--jenkins-username',
                'user',
                '--jenkins-password',
                'pass',
                '--tool-alias',
                '[fn]',
                '--transport',
                'streamable-http',
            ],
        )
        assert result.exit_code == 0
        mock_mcp.run.assert_called_once_with(transport='streamable-http')


def test_transport_streamable_http_sets_port():
    """测试transport为'streamable-http'时正确设置端口"""
    with patch('mcp_jenkins.jenkins.JenkinsClient'), patch('mcp_jenkins.server.mcp') as mock_mcp:
        mock_settings = MagicMock()
        mock_mcp.settings = mock_settings
        mock_mcp.run = MagicMock()

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                '--jenkins-url',
                'http://localhost',
                '--jenkins-username',
                'user',
                '--jenkins-password',
                'pass',
                '--tool-alias',
                '[fn]',
                '--transport',
                'streamable-http',
                '--port',
                '9888',
            ],
        )
        assert result.exit_code == 0
        assert mock_settings.port == 9888
        mock_mcp.run.assert_called_once_with(transport='streamable-http')
