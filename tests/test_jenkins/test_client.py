from unittest.mock import MagicMock, patch

import pytest

from mcp_jenkins.jenkins._client import JenkinsClient


@pytest.mark.parametrize('ssl_verify', [True, False])
def test_ssl_verify_setting(ssl_verify):
    with patch('mcp_jenkins.jenkins._client.Jenkins') as mock_jenkins_class:
        mock_jenkins_instance = MagicMock()
        mock_jenkins_class.return_value = mock_jenkins_instance

        JenkinsClient(url='http://localhost', username='user', password='pass', ssl_verify=ssl_verify)

        assert mock_jenkins_instance._session.verify is ssl_verify
