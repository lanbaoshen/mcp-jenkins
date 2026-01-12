import pytest

from mcp_jenkins.jenkins.model.build import Build, BuildReplay
from mcp_jenkins.server import build


@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()

    mocker.patch('mcp_jenkins.server.build.jenkins', return_value=mock_jenkins)

    yield mock_jenkins


@pytest.mark.asyncio
async def test_get_running_builds(mock_jenkins, mocker):
    build1 = Build(number=1, url='1', building=True, timestamp=1234567890)
    build2 = Build(number=2, url='2', building=True, timestamp=1234567891)
    mock_jenkins.get_running_builds.return_value = [build1, build2]

    assert await build.get_running_builds.fn(mocker.Mock()) == [
        {'number': 1, 'url': '1', 'building': True, 'timestamp': 1234567890},
        {'number': 2, 'url': '2', 'building': True, 'timestamp': 1234567891},
    ]


@pytest.mark.asyncio
async def test_get_build(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build.return_value = Build(number=1, url='1', building=False, timestamp=1234567890)

    assert await build.get_build.fn(mocker.Mock(), fullname='job1') == {
        'number': 1,
        'url': '1',
        'building': False,
        'timestamp': 1234567890,
    }


@pytest.mark.asyncio
async def test_get_build_scripts(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_replay.return_value = BuildReplay(scripts=['script1', 'script2'])

    assert await build.get_build_scripts.fn(mocker.Mock(), fullname='job1') == ['script1', 'script2']


@pytest.mark.asyncio
async def test_get_build_console_output(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_console_output.return_value = 'Console output here'

    assert await build.get_build_console_output.fn(mocker.Mock(), fullname='job1') == 'Console output here'


@pytest.mark.asyncio
async def test_get_build_test_reports(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_test_report.return_value = {'reports': ['report1', 'report2']}

    assert await build.get_build_test_report.fn(mocker.Mock(), fullname='job1') == {'reports': ['report1', 'report2']}


@pytest.mark.asyncio
async def test_stop_build(mock_jenkins, mocker):
    await build.stop_build.fn(mocker.Mock(), fullname='job1', number=1)
    mock_jenkins.stop_build.assert_called_once_with(fullname='job1', number=1)
