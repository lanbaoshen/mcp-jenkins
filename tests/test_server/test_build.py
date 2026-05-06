import pytest

from mcp_jenkins.jenkins.model.build import Artifact, Build, BuildReplay
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

    assert await build.get_running_builds(mocker.Mock()) == [
        {'number': 1, 'url': '1', 'building': True, 'timestamp': 1234567890},
        {'number': 2, 'url': '2', 'building': True, 'timestamp': 1234567891},
    ]


@pytest.mark.asyncio
async def test_get_build(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build.return_value = Build(number=1, url='1', building=False, timestamp=1234567890)

    assert await build.get_build(mocker.Mock(), fullname='job1') == {
        'number': 1,
        'url': '1',
        'building': False,
        'timestamp': 1234567890,
    }


@pytest.mark.asyncio
async def test_get_build_scripts(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_replay.return_value = BuildReplay(scripts=['script1', 'script2'])

    assert await build.get_build_scripts(mocker.Mock(), fullname='job1') == [
        'script1',
        'script2',
    ]


@pytest.mark.asyncio
async def test_get_build_console_output(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_console_output.return_value = 'Console output here'

    assert await build.get_build_console_output(mocker.Mock(), fullname='job1') == 'Console output here'
    mock_jenkins.get_build_console_output.assert_called_once_with(
        fullname='job1', number=1, pattern=None, offset=0, limit=None
    )


@pytest.mark.asyncio
async def test_get_build_console_output_with_number(mock_jenkins, mocker):
    mock_jenkins.get_build_console_output.return_value = 'output'

    assert await build.get_build_console_output(mocker.Mock(), fullname='job1', number=5) == 'output'
    mock_jenkins.get_item.assert_not_called()
    mock_jenkins.get_build_console_output.assert_called_once_with(
        fullname='job1', number=5, pattern=None, offset=0, limit=None
    )


@pytest.mark.asyncio
async def test_get_build_console_output_with_all_params(mock_jenkins, mocker):
    mock_jenkins.get_build_console_output.return_value = 'ERROR: boom'

    result = await build.get_build_console_output(
        mocker.Mock(), fullname='job1', number=3, pattern='ERROR', offset=1, limit=10
    )
    assert result == 'ERROR: boom'
    mock_jenkins.get_build_console_output.assert_called_once_with(
        fullname='job1', number=3, pattern='ERROR', offset=1, limit=10
    )


@pytest.mark.asyncio
async def test_get_build_console_output_no_build(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = None

    with pytest.raises(ValueError, match='No build found for job: job1'):
        await build.get_build_console_output(mocker.Mock(), fullname='job1')


@pytest.mark.asyncio
async def test_get_build_test_reports(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_test_report.return_value = {'reports': ['report1', 'report2']}

    assert await build.get_build_test_report(mocker.Mock(), fullname='job1') == {'reports': ['report1', 'report2']}


@pytest.mark.asyncio
async def test_get_build_parameters(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_parameters.return_value = {'BRANCH': 'main', 'DEBUG': True}

    assert await build.get_build_parameters(mocker.Mock(), fullname='job1') == {
        'BRANCH': 'main',
        'DEBUG': True,
    }


@pytest.mark.asyncio
async def test_stop_build(mock_jenkins, mocker):
    await build.stop_build(mocker.Mock(), fullname='job1', number=1)
    mock_jenkins.stop_build.assert_called_once_with(fullname='job1', number=1)


@pytest.mark.asyncio
async def test_get_all_build_artifacts(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_artifacts.return_value = [
        Artifact(
            fileName='index.html',
            relativePath='playwright-report/index.html',
            displayPath='playwright-report/index.html',
        ),
        Artifact(fileName='trace.zip', relativePath='trace.zip', displayPath='trace.zip'),
    ]

    assert await build.get_all_build_artifacts(mocker.Mock(), fullname='job1') == [
        {
            'fileName': 'index.html',
            'relativePath': 'playwright-report/index.html',
            'displayPath': 'playwright-report/index.html',
        },
        {'fileName': 'trace.zip', 'relativePath': 'trace.zip', 'displayPath': 'trace.zip'},
    ]


@pytest.mark.asyncio
async def test_get_all_build_artifacts_with_number(mock_jenkins, mocker):
    mock_jenkins.get_build_artifacts.return_value = []

    assert await build.get_all_build_artifacts(mocker.Mock(), fullname='job1', number=5) == []
    mock_jenkins.get_item.assert_not_called()
    mock_jenkins.get_build_artifacts.assert_called_once_with(fullname='job1', number=5)


@pytest.mark.asyncio
async def test_get_build_artifact_text(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_artifact.return_value = b'<html>report</html>'

    result = await build.get_build_artifact(
        mocker.Mock(), fullname='job1', relative_path='playwright-report/index.html'
    )
    assert result == {'content': '<html>report</html>', 'encoding': 'utf-8'}


@pytest.mark.asyncio
async def test_get_build_artifact_binary(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_artifact.return_value = bytes(range(256))

    result = await build.get_build_artifact(mocker.Mock(), fullname='job1', relative_path='trace.zip')
    assert result['encoding'] == 'base64'
    import base64

    assert base64.b64decode(result['content']) == bytes(range(256))


@pytest.mark.asyncio
async def test_get_build_artifact_with_number(mock_jenkins, mocker):
    mock_jenkins.get_build_artifact.return_value = b'data'

    result = await build.get_build_artifact(mocker.Mock(), fullname='job1', relative_path='file.txt', number=3)
    mock_jenkins.get_item.assert_not_called()
    mock_jenkins.get_build_artifact.assert_called_once_with(fullname='job1', number=3, relative_path='file.txt')
    assert result == {'content': 'data', 'encoding': 'utf-8'}


@pytest.mark.asyncio
async def test_get_build_artifact_url(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_artifact_url.return_value = 'https://jenkins.example.com/job/job1/1/artifact/trace.zip'

    result = await build.get_build_artifact_url(mocker.Mock(), fullname='job1', relative_path='trace.zip')
    assert result == 'https://jenkins.example.com/job/job1/1/artifact/trace.zip'


@pytest.mark.asyncio
async def test_get_build_artifact_url_with_number(mock_jenkins, mocker):
    mock_jenkins.get_build_artifact_url.return_value = 'https://jenkins.example.com/job/job1/5/artifact/report.html'

    result = await build.get_build_artifact_url(mocker.Mock(), fullname='job1', relative_path='report.html', number=5)
    mock_jenkins.get_item.assert_not_called()
    mock_jenkins.get_build_artifact_url.assert_called_once_with(fullname='job1', number=5, relative_path='report.html')
    assert result == 'https://jenkins.example.com/job/job1/5/artifact/report.html'
