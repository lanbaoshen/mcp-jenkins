from unittest.mock import MagicMock

import pytest

from mcp_jenkins.jenkins import JenkinsClient


@pytest.fixture
def mock_jenkins_config():
    return {
        'username': 'test_user',
        'password': 'test_password',
        'url': 'http://localhost:8080',
    }


@pytest.fixture
def mock_jenkins_config_with_token():
    return {
        'username': 'test_user',
        'password': 'test_api_token_123456789',  # API token used as password
        'url': 'http://localhost:8080',
    }


@pytest.fixture
def mock_jenkins():
    mock_jenkins = MagicMock()
    yield mock_jenkins


@pytest.fixture
def jenkins_client(mock_jenkins, mock_jenkins_config):
    client = JenkinsClient(**mock_jenkins_config)
    client._jenkins = mock_jenkins
    yield client
