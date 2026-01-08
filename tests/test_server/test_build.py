"""
Unit tests for mcp_jenkins.server.build.get_test_results function.

Tests the get_test_results MCP tool function exception handling.
"""
import os

# Set the necessary environment variables to avoid import errors.
os.environ['tool_alias'] = '[fn]'

from unittest.mock import MagicMock

import pytest
from jenkins import JenkinsException

from mcp_jenkins.server.build import get_test_results


@pytest.mark.asyncio
async def test_get_test_results_jenkins_exception(monkeypatch):
    
    # Create mock objects
    mock_jenkins_client = MagicMock()
    mock_build = MagicMock()
    mock_jenkins_client.build = mock_build
    
    # Configure the mock to raise JenkinsException when get_test_report is called
    mock_build.get_test_report.side_effect = JenkinsException('Test exception')

    # Create a function that returns our mock client
    def mock_client_func(ctx):
        return mock_jenkins_client
    
    # Use monkeypatch to replace the client function
    monkeypatch.setattr('mcp_jenkins.server.build.client', mock_client_func)
    
    # Create a mock context
    mock_ctx = MagicMock()
    
    # Act: Call the function under test
    result = await get_test_results.fn(
        mock_ctx, 
        fullname='folder-one/job-two', 
        build_number=110
    )

    # Assert: Verify the result matches empty test report structure
    expected = {
        'failCount': 0, 
        'skipCount': 0, 
        'passCount': 0, 
        'totalCount': 0, 
        'duration': 0.0, 
        'suites': []
    }
    assert result == expected
    
    # Verify that get_test_report was called with correct parameters
    mock_build.get_test_report.assert_called_once_with('folder-one/job-two', 110)


