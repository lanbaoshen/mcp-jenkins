import os

# Set the necessary environment variables to avoid import errors.
os.environ['tool_alias'] = '[fn]'

from unittest.mock import MagicMock, patch

import pytest
from jenkins import JenkinsException

from mcp_jenkins.server.build import get_test_results


@pytest.mark.asyncio
async def test_get_test_results_jenkins_exception():
    """Test get_test_results returns empty results when JenkinsException is raised"""
    # Create a mock context
    mock_ctx = MagicMock()

    # Mock the client and build objects
    mock_client = MagicMock()
    mock_build = MagicMock()
    mock_client.build = mock_build
    mock_ctx.client = mock_client

    # Set up the mock to raise JenkinsException
    mock_build.get_test_report.side_effect = JenkinsException('Test exception')

    # Patch the client function to return our mock client
    with patch('mcp_jenkins.server.build.client', return_value=mock_client):
        # Call the function
        result = await get_test_results(mock_ctx, fullname='folder-one/job-two', build_number=110)

        # Verify the result
        expected = {'failCount': 0, 'skipCount': 0, 'passCount': 0, 'totalCount': 0, 'duration': 0.0, 'suites': []}
        assert result == expected
