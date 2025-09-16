import pytest

from mcp_jenkins.jenkins._build import JenkinsBuild
from mcp_jenkins.models.build import Build

RUNNING_BUILDS = [
    {
        'name': 'RUN_JOB_LIST',
        'number': 2,
        'url': 'http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
        'node': '(master)',
        'executor': 4,
    },
    {
        'name': 'weekly',
        'number': 39,
        'url': 'http://example.com/job/weekly/job/folder-one/job/job-two/39/',
        'node': '001',
        'executor': 0,
    },
]

BUILD_INFO = {
    '_class': 'org.jenkinsci.plugins.workflow.job.WorkflowRun',
    'actions': [
        {
            '_class': 'com.tikal.jenkins.plugins.multijob.MultiJobParametersAction',
            'parameters': [
                {
                    '_class': 'hudson.model.StringParameterValue',
                    'name': 'Param1',
                    'value': 'Test Param',
                }
            ],
        }
    ],
    'building': False,
    'duration': 10198378,
    'estimatedDuration': 24529283,
    'executor': None,
    'number': 110,
    'result': 'SUCCESS',
    'timestamp': 1743719665911,
    'url': 'http://example.com/job/weekly/job/folder-one/job/job-two/110/',
    'inProgress': False,
    'nextBuild': None,
    'previousBuild': {
        'number': 109,
        'url': 'http://example.com/job/weekly/job/folder-one/job/job-two/109/',
    },
}


@pytest.fixture()
def jenkins_build(mock_jenkins):
    mock_jenkins.get_running_builds.return_value = RUNNING_BUILDS
    mock_jenkins.get_build_info.return_value = BUILD_INFO
    mock_jenkins.build_job.return_value = 1
    mock_jenkins.stop_build.return_value = None
    mock_jenkins.get_job_info.return_value = {
        'property': [
            {
                '_class': 'hudson.model.ParametersDefinitionProperty',
                'parameterDefinitions': [],
            }
        ]
    }

    yield JenkinsBuild(mock_jenkins)


def test_to_model(jenkins_build):
    model = jenkins_build._to_model(
        {
            'name': 'RUN_JOB_LIST',
            'number': 2,
            'url': 'http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
            'node': '(master)',
            'executor': 4,
        }
    )

    assert model == Build(
        name='RUN_JOB_LIST',
        number=2,
        url='http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
        node='(master)',
        executor=4,
    )


def test_get_running_builds(jenkins_build):
    builds = jenkins_build.get_running_builds()

    assert len(builds) == 2
    assert builds[0] == Build(
        name='RUN_JOB_LIST',
        number=2,
        url='http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
        node='(master)',
        executor=4,
    )
    assert builds[1] == Build(
        name='weekly',
        number=39,
        url='http://example.com/job/weekly/job/folder-one/job/job-two/39/',
        node='001',
        executor=0,
    )


def test_get_build_info(jenkins_build):
    build = jenkins_build.get_build_info(fullname='folder-one/job-two', number=110)

    assert build == Build(
        number=110,
        url='http://example.com/job/weekly/job/folder-one/job/job-two/110/',
        executor=None,
        class_='org.jenkinsci.plugins.workflow.job.WorkflowRun',
        building=False,
        duration=10198378,
        estimatedDuration=24529283,
        result='SUCCESS',
        timestamp=1743719665911,
        inProgress=False,
        nextBuild=None,
        previousBuild=Build(
            number=109,
            url='http://example.com/job/weekly/job/folder-one/job/job-two/109/',
        ),
    )


def test_get_build_sourcecode_success(jenkins_build):
    # Example HTML with pipeline script in textarea
    html = """<html><body><textarea name="_.mainScript">pipeline {\n    agent any\n    stages {\n        stage(\"Build\") {\n            steps {\n                echo \"Building...\"\n            }\n        }\n    }\n}</textarea></body></html>"""  # noqa: E501
    jenkins_build._jenkins.server = 'http://localhost:8080/'
    jenkins_build._jenkins.jenkins_open.return_value = html

    sourcecode = jenkins_build.get_build_sourcecode('folder-one/job-two', 110)
    assert 'pipeline' in sourcecode
    assert 'stage("Build")' in sourcecode
    assert 'echo "Building..."' in sourcecode

    # Check that jenkins_open was called with the correct URL
    called_args = jenkins_build._jenkins.jenkins_open.call_args[0][0]
    assert called_args.method == 'GET'
    assert '/replay' in called_args.url


def test_get_build_sourcecode_no_script(jenkins_build):
    # HTML without textarea/script
    html = '<html><body><h1>No script here</h1></body></html>'
    jenkins_build._jenkins.server = 'http://localhost:8080/'
    jenkins_build._jenkins.jenkins_open.return_value = html

    sourcecode = jenkins_build.get_build_sourcecode('folder-one/job-two', 110)
    assert sourcecode == 'No Script found'


def test_build_job(jenkins_build):
    assert jenkins_build.build_job('job', parameters=None) == 1


def test_get_build_logs(jenkins_build):
    # Setup mock response
    expected_logs = 'Build started\nStep 1: Checkout\nBuild successful'
    jenkins_build._jenkins.get_build_console_output.return_value = expected_logs

    # Call the function
    logs = jenkins_build.get_build_logs(fullname='folder-one/job-two', number=110)

    # Verify the correct Jenkins API method was called with right parameters
    jenkins_build._jenkins.get_build_console_output.assert_called_once_with('folder-one/job-two', 110)

    # Verify the returned logs match the expected output
    assert logs == expected_logs


def test_get_build_logs_empty(jenkins_build):
    # Test handling of empty logs
    jenkins_build._jenkins.get_build_console_output.return_value = ''

    logs = jenkins_build.get_build_logs(fullname='folder-one/job-two', number=110)

    assert logs == ''
    jenkins_build._jenkins.get_build_console_output.assert_called_once_with('folder-one/job-two', 110)


def test_get_build_log_asc_pattern_limit(jenkins_build):
    jenkins_build._jenkins.get_build_console_output.return_value = '1 Foo\n2 Foo\n3 Foo\n'

    logs = jenkins_build.get_build_logs(fullname='folder-one/job-two', number=110, pattern='Foo', limit=1, seq='asc')

    assert logs == '1 Foo'
    jenkins_build._jenkins.get_build_console_output.assert_called_once_with('folder-one/job-two', 110)


def test_get_build_log_desc_pattern_limit(jenkins_build):
    jenkins_build._jenkins.get_build_console_output.return_value = '1 Foo\n2 Foo\n3 Foo\n'

    logs = jenkins_build.get_build_logs(fullname='folder-one/job-two', number=110, pattern='Foo', limit=2, seq='desc')

    assert logs == '2 Foo\n3 Foo'
    jenkins_build._jenkins.get_build_console_output.assert_called_once_with('folder-one/job-two', 110)


def test_get_build_logs_unicode(jenkins_build):
    # Test handling of logs with unicode characters
    expected_logs = 'Build started\n🚀 Deploying\n✅ Success\n❌ Failed step\n'
    jenkins_build._jenkins.get_build_console_output.return_value = expected_logs

    logs = jenkins_build.get_build_logs(fullname='folder-one/job-two', number=110)

    assert logs == expected_logs
    jenkins_build._jenkins.get_build_console_output.assert_called_once_with('folder-one/job-two', 110)


def test_get_build_logs_not_found(jenkins_build):
    # Test handling of non-existent build
    from jenkins import JenkinsException

    jenkins_build._jenkins.get_build_console_output.side_effect = JenkinsException('Build not found')

    with pytest.raises(JenkinsException, match='Build not found'):
        jenkins_build.get_build_logs(fullname='folder-one/job-two', number=999999)


def test_stop_build(jenkins_build):
    assert jenkins_build.stop_build(fullname='folder-one/job-two', number=110) is None
