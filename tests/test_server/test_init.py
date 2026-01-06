import os
import pytest
from unittest.mock import MagicMock, patch, Mock, AsyncMock

from click.testing import CliRunner

# Set the necessary environment variables to avoid import errors.
os.environ['tool_alias'] = '[fn]'

# Mock the tool modules before importing mcp_jenkins to prevent tool registration during tests
import sys
sys.modules['mcp_jenkins.server.build'] = Mock()
sys.modules['mcp_jenkins.server.job'] = Mock()
sys.modules['mcp_jenkins.server.node'] = Mock()
sys.modules['mcp_jenkins.server.queue_item'] = Mock()

from mcp_jenkins import main
from mcp_jenkins.server import JenkinsHeaderMiddleware, client


def test_transport_streamable_http_valid():
    """Test that the `transport` parameter accepts the value 'streamable-http'"""
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
    """Test that the `port` is correctly set when the `transport` is 'streamable-http'"""
    with patch('mcp_jenkins.jenkins.JenkinsClient'), patch('mcp_jenkins.server.mcp') as mock_mcp, \
         patch('fastmcp.settings') as mock_settings:
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
        mock_mcp.run.assert_called_once_with(transport='streamable-http')


@pytest.mark.asyncio
async def test_jenkins_header_middleware_extracts_credentials():
    """Test that JenkinsHeaderMiddleware extracts credentials from HTTP headers"""
    # Create a mock ASGI app
    mock_app = AsyncMock()
    
    middleware = JenkinsHeaderMiddleware(mock_app)
    
    # Create a mock scope with headers
    scope = {
        "type": "http",
        "headers": [
            (b"x-jenkins-url", b"https://jenkins.example.com"),
            (b"x-jenkins-username", b"testuser"),
            (b"x-jenkins-password", b"testpass"),
        ],
    }
    
    mock_receive = AsyncMock()
    mock_send = AsyncMock()
    
    # Call the middleware
    await middleware(scope, mock_receive, mock_send)
    
    # Verify that the state was set correctly
    assert "state" in scope
    assert scope["state"]["jenkins_url"] == "https://jenkins.example.com"
    assert scope["state"]["jenkins_username"] == "testuser"
    assert scope["state"]["jenkins_password"] == "testpass"
    
    # Verify the app was called
    mock_app.assert_called_once_with(scope, mock_receive, mock_send)


@pytest.mark.asyncio
async def test_jenkins_header_middleware_handles_missing_headers():
    """Test that JenkinsHeaderMiddleware handles missing headers gracefully"""
    mock_app = AsyncMock()
    middleware = JenkinsHeaderMiddleware(mock_app)
    
    # Create a mock scope without Jenkins headers
    scope = {
        "type": "http",
        "headers": [],
    }
    
    mock_receive = AsyncMock()
    mock_send = AsyncMock()
    
    # Call the middleware
    await middleware(scope, mock_receive, mock_send)
    
    # Verify that state was created with None values
    assert "state" in scope
    assert scope["state"]["jenkins_url"] is None
    assert scope["state"]["jenkins_username"] is None
    assert scope["state"]["jenkins_password"] is None
    
    # Verify the app was called
    mock_app.assert_called_once()


@pytest.mark.asyncio
async def test_jenkins_header_middleware_non_http_request():
    """Test that JenkinsHeaderMiddleware passes through non-HTTP requests"""
    mock_app = AsyncMock()
    middleware = JenkinsHeaderMiddleware(mock_app)
    
    # Create a non-HTTP scope
    scope = {
        "type": "websocket",
    }
    
    mock_receive = AsyncMock()
    mock_send = AsyncMock()
    
    # Call the middleware
    await middleware(scope, mock_receive, mock_send)
    
    # Verify the app was called directly without modification
    mock_app.assert_called_once_with(scope, mock_receive, mock_send)
    # State should not be added for non-HTTP requests
    assert "state" not in scope


def test_client_uses_environment_variables_fallback():
    """Test that client() function falls back to environment variables"""
    # Set environment variables
    os.environ['jenkins_url'] = 'https://jenkins.test.com'
    os.environ['jenkins_username'] = 'envuser'
    os.environ['jenkins_password'] = 'envpass'
    os.environ['jenkins_timeout'] = '10'
    
    mock_ctx = MagicMock()
    
    # Mock get_http_request to raise exception (no HTTP context)
    with patch('mcp_jenkins.server.get_http_request', side_effect=Exception("No HTTP context")), \
         patch('mcp_jenkins.server.JenkinsClient') as mock_jenkins_client:
        
        # Call client function
        client(mock_ctx)
        
        # Verify JenkinsClient was created with environment variables
        mock_jenkins_client.assert_called_once_with(
            url='https://jenkins.test.com',
            username='envuser',
            password='envpass',
            timeout=10,
        )
    
    # Clean up environment variables
    del os.environ['jenkins_url']
    del os.environ['jenkins_username']
    del os.environ['jenkins_password']
    del os.environ['jenkins_timeout']


def test_client_prefers_headers_over_environment():
    """Test that client() function prefers HTTP headers over environment variables"""
    # Set environment variables
    os.environ['jenkins_url'] = 'https://jenkins.env.com'
    os.environ['jenkins_username'] = 'envuser'
    os.environ['jenkins_password'] = 'envpass'
    os.environ['jenkins_timeout'] = '5'
    
    mock_ctx = MagicMock()
    
    # Mock HTTP request with state containing header credentials
    mock_request = MagicMock()
    mock_request.state.jenkins_url = 'https://jenkins.header.com'
    mock_request.state.jenkins_username = 'headeruser'
    mock_request.state.jenkins_password = 'headerpass'
    mock_request.url = 'http://test.com'
    
    with patch('mcp_jenkins.server.get_http_request', return_value=mock_request), \
         patch('mcp_jenkins.server.JenkinsClient') as mock_jenkins_client:
        
        # Call client function
        client(mock_ctx)
        
        # Verify JenkinsClient was created with header credentials, not environment
        mock_jenkins_client.assert_called_once_with(
            url='https://jenkins.header.com',
            username='headeruser',
            password='headerpass',
            timeout=5,
        )
    
    # Clean up
    del os.environ['jenkins_url']
    del os.environ['jenkins_username']
    del os.environ['jenkins_password']
    del os.environ['jenkins_timeout']


def test_client_raises_error_when_no_credentials():
    """Test that client() raises ValueError when no credentials are provided"""
    mock_ctx = MagicMock()
    
    # Ensure no environment variables are set
    for key in ['jenkins_url', 'jenkins_username', 'jenkins_password']:
        os.environ.pop(key, None)
    
    # Mock get_http_request to raise exception (no HTTP context)
    with patch('mcp_jenkins.server.get_http_request', side_effect=Exception("No HTTP context")):
        
        # Verify that ValueError is raised
        with pytest.raises(ValueError, match="Jenkins credentials not provided"):
            client(mock_ctx)
