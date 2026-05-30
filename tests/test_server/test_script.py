import pytest

from mcp_jenkins.server import script


@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()
    mocker.patch('mcp_jenkins.server.script.jenkins', return_value=mock_jenkins)
    yield mock_jenkins


@pytest.mark.asyncio
async def test_run_groovy_script(mock_jenkins, mocker):
    mock_jenkins.run_script.return_value = 'Script result: success'

    result = await script.run_groovy_script(mocker.Mock(), script='println("test")')

    assert result == 'Script result: success'
    mock_jenkins.run_script.assert_called_once_with(script='println("test")')


@pytest.mark.asyncio
async def test_run_groovy_script_with_result_prefix(mock_jenkins, mocker):
    mock_jenkins.run_script.return_value = 'output only'

    result = await script.run_groovy_script(mocker.Mock(), script='return "output"')

    assert result == 'output only'
