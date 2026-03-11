import pytest

from mcp_jenkins.server import build_log


@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()

    mocker.patch('mcp_jenkins.server.build_log.jenkins', return_value=mock_jenkins)

    yield mock_jenkins


@pytest.mark.asyncio
async def test_get_build_log_progressive(mock_jenkins, mocker):
    mock_jenkins.get_build_console_output_progressive.return_value = {
        'output': 'Build started\nStep 1...',
        'next_start': 1024,
        'has_more_data': True,
    }

    result = await build_log.get_build_log_progressive(mocker.Mock(), fullname='job1', number=42, start=0)

    assert result == {
        'output': 'Build started\nStep 1...',
        'next_start': 1024,
        'has_more_data': True,
    }
    mock_jenkins.get_build_console_output_progressive.assert_called_once_with(fullname='job1', number=42, start=0)


@pytest.mark.asyncio
async def test_get_build_log_progressive_default_number(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 5
    mock_jenkins.get_build_console_output_progressive.return_value = {
        'output': 'Finished: SUCCESS',
        'next_start': 2048,
        'has_more_data': False,
    }

    result = await build_log.get_build_log_progressive(mocker.Mock(), fullname='job1')

    assert result == {
        'output': 'Finished: SUCCESS',
        'next_start': 2048,
        'has_more_data': False,
    }
    mock_jenkins.get_build_console_output_progressive.assert_called_once_with(fullname='job1', number=5, start=0)


@pytest.mark.asyncio
async def test_get_build_log_progressive_with_offset(mock_jenkins, mocker):
    mock_jenkins.get_build_console_output_progressive.return_value = {
        'output': 'Step 2...\nFinished: SUCCESS',
        'next_start': 4096,
        'has_more_data': False,
    }

    result = await build_log.get_build_log_progressive(mocker.Mock(), fullname='job1', number=42, start=1024)

    assert result == {
        'output': 'Step 2...\nFinished: SUCCESS',
        'next_start': 4096,
        'has_more_data': False,
    }
    mock_jenkins.get_build_console_output_progressive.assert_called_once_with(fullname='job1', number=42, start=1024)
