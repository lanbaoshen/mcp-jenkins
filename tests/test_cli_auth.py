import pytest
from click.testing import CliRunner

from mcp_jenkins import main


class TestCLIAuthentication:
    """Test CLI authentication options."""

    def test_password_authentication(self):
        """Test CLI with password authentication."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--jenkins-url', 'http://localhost:8080',
            '--jenkins-username', 'testuser',
            '--jenkins-password', 'testpass',
            '--help'  # Use help to avoid actually starting the server
        ])
        assert result.exit_code == 0

    def test_token_authentication(self):
        """Test CLI with token authentication."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--jenkins-url', 'http://localhost:8080',
            '--jenkins-username', 'testuser',
            '--jenkins-token', 'test_api_token_123',
            '--help'  # Use help to avoid actually starting the server
        ])
        assert result.exit_code == 0

    def test_missing_authentication(self):
        """Test CLI fails when no authentication is provided."""
        runner = CliRunner()
        with pytest.raises(ValueError, match='Please provide either --jenkins-password or --jenkins-token'):
            runner.invoke(main, [
                '--jenkins-url', 'http://localhost:8080',
                '--jenkins-username', 'testuser',
                # No password or token
            ], catch_exceptions=False)

    def test_both_password_and_token_provided(self):
        """Test CLI fails when both password and token are provided."""
        runner = CliRunner()
        with pytest.raises(ValueError, match='Please provide either --jenkins-password or --jenkins-token, not both'):
            runner.invoke(main, [
                '--jenkins-url', 'http://localhost:8080',
                '--jenkins-username', 'testuser',
                '--jenkins-password', 'testpass',
                '--jenkins-token', 'test_api_token_123',
            ], catch_exceptions=False)
