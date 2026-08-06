import pytest

from mcp_jenkins.jenkins.model.build import Artifact, Build, BuildReplay, PendingInput
from mcp_jenkins.jenkins.model.item import Folder, Job
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
async def test_get_pending_inputs(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_pending_inputs.return_value = [
        PendingInput(
            id='Deploy',
            message='Deploy to prod?',
            proceedText='Deploy',
            inputs=[{'name': 'TARGET', 'type': 'StringParameterDefinition'}],
        )
    ]

    assert await build.get_pending_inputs(mocker.Mock(), fullname='job1') == [
        {
            'id': 'Deploy',
            'message': 'Deploy to prod?',
            'proceedText': 'Deploy',
            'inputs': [{'name': 'TARGET', 'type': 'StringParameterDefinition'}],
        }
    ]
    mock_jenkins.get_build_pending_inputs.assert_called_once_with(fullname='job1', number=1)


@pytest.mark.asyncio
async def test_get_pending_inputs_with_number(mock_jenkins, mocker):
    mock_jenkins.get_build_pending_inputs.return_value = [PendingInput(id='Deploy')]

    assert await build.get_pending_inputs(mocker.Mock(), fullname='job1', number=5) == [{'id': 'Deploy', 'inputs': []}]
    mock_jenkins.get_item.assert_not_called()
    mock_jenkins.get_build_pending_inputs.assert_called_once_with(fullname='job1', number=5)


@pytest.mark.asyncio
async def test_get_pending_inputs_empty(mock_jenkins, mocker):
    mock_jenkins.get_build_pending_inputs.return_value = []

    assert await build.get_pending_inputs(mocker.Mock(), fullname='job1', number=5) == []


@pytest.mark.asyncio
async def test_get_pending_inputs_no_build(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value = Job(_class='hudson.model.Job', name='job1', url='url', color='notbuilt')

    with pytest.raises(ValueError, match='No build found for job: job1'):
        await build.get_pending_inputs(mocker.Mock(), fullname='job1')


@pytest.mark.asyncio
async def test_submit_input_auto_resolves_number_and_input_id(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_pending_inputs.return_value = [PendingInput(id='Deploy')]

    assert await build.submit_input(mocker.Mock(), fullname='job1') == {
        'fullname': 'job1',
        'number': 1,
        'inputId': 'Deploy',
        'action': 'proceed',
    }
    mock_jenkins.submit_build_input.assert_called_once_with(
        fullname='job1', number=1, input_id='Deploy', action='proceedEmpty', parameters=None
    )


@pytest.mark.asyncio
async def test_submit_input_with_parameters(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value.lastBuild.number = 1
    mock_jenkins.get_build_pending_inputs.return_value = [PendingInput(id='Deploy')]

    await build.submit_input(mocker.Mock(), fullname='job1', parameters={'APPROVE': True, 'TARGET': 'prod'})

    mock_jenkins.submit_build_input.assert_called_once_with(
        fullname='job1',
        number=1,
        input_id='Deploy',
        action='proceed',
        parameters={'APPROVE': True, 'TARGET': 'prod'},
    )


@pytest.mark.asyncio
async def test_submit_input_with_explicit_input_id(mock_jenkins, mocker):
    await build.submit_input(mocker.Mock(), fullname='job1', number=7, input_id='Deploy')

    mock_jenkins.get_item.assert_not_called()
    mock_jenkins.get_build_pending_inputs.assert_not_called()
    mock_jenkins.submit_build_input.assert_called_once_with(
        fullname='job1', number=7, input_id='Deploy', action='proceedEmpty', parameters=None
    )


@pytest.mark.asyncio
async def test_submit_input_abort(mock_jenkins, mocker):
    assert await build.submit_input(mocker.Mock(), fullname='job1', number=7, input_id='Deploy', action='abort') == {
        'fullname': 'job1',
        'number': 7,
        'inputId': 'Deploy',
        'action': 'abort',
    }
    mock_jenkins.submit_build_input.assert_called_once_with(
        fullname='job1', number=7, input_id='Deploy', action='abort', parameters=None
    )


@pytest.mark.asyncio
async def test_submit_input_abort_with_parameters(mock_jenkins, mocker):
    with pytest.raises(ValueError, match='cannot be combined'):
        await build.submit_input(
            mocker.Mock(), fullname='job1', number=7, input_id='Deploy', action='abort', parameters={'A': 'b'}
        )

    mock_jenkins.submit_build_input.assert_not_called()


@pytest.mark.asyncio
async def test_submit_input_no_pending_inputs(mock_jenkins, mocker):
    mock_jenkins.get_build_pending_inputs.return_value = []

    with pytest.raises(ValueError, match='No pending input for job1 #1'):
        await build.submit_input(mocker.Mock(), fullname='job1', number=1)

    mock_jenkins.submit_build_input.assert_not_called()


@pytest.mark.asyncio
async def test_submit_input_multiple_pending_inputs(mock_jenkins, mocker):
    mock_jenkins.get_build_pending_inputs.return_value = [PendingInput(id='Deploy'), PendingInput(id='Rollback')]

    with pytest.raises(ValueError, match='Multiple pending inputs') as exc_info:
        await build.submit_input(mocker.Mock(), fullname='job1', number=1)

    assert 'Deploy' in str(exc_info.value)
    assert 'Rollback' in str(exc_info.value)
    mock_jenkins.submit_build_input.assert_not_called()


@pytest.mark.asyncio
async def test_submit_input_no_build(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value = Job(_class='hudson.model.Job', name='job1', url='url', color='notbuilt')

    with pytest.raises(ValueError, match='No build found for job: job1'):
        await build.submit_input(mocker.Mock(), fullname='job1')

    mock_jenkins.submit_build_input.assert_not_called()


@pytest.mark.asyncio
async def test_submit_input_on_item_without_last_build(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value = Folder(_class='com.cloudbees...Folder', name='folder1', url='url', jobs=[])

    with pytest.raises(ValueError, match='No build found for job: folder1'):
        await build.submit_input(mocker.Mock(), fullname='folder1')

    mock_jenkins.submit_build_input.assert_not_called()


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
