import pytest

from mcp_jenkins.jenkins._build import JenkinsBuild
from mcp_jenkins.models.build import Build

RUNNING_BUILDS = [
    {
        'name': 'RUN_JOB_LIST',
        'number': 2,
        'url': 'http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
        'node': '(master)',
        'executor': 4
    },
    {
        'name': 'weekly',
        'number': 39,
        'url': 'http://example.com/job/weekly/job/folder-one/job/job-two/39/',
        'node': '001',
        'executor': 0
    }
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
                    'value': 'Test Param'
                }
            ]
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
        'url': 'http://example.com/job/weekly/job/folder-one/job/job-two/109/'
    }
}


@pytest.fixture()
def jenkins_build(mock_jenkins):
    mock_jenkins.get_running_builds.return_value = RUNNING_BUILDS
    mock_jenkins.get_build_info.return_value = BUILD_INFO
    mock_jenkins.build_job.return_value = 1
    yield JenkinsBuild(mock_jenkins)


def test_to_model(jenkins_build):
    model = jenkins_build._to_model({
        'name': 'RUN_JOB_LIST',
        'number': 2,
        'url': 'http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
        'node': '(master)',
        'executor': 4
    })

    assert model == Build(
        name='RUN_JOB_LIST',
        number=2,
        url='http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
        node='(master)',
        executor=4
    )


def test_get_running_builds(jenkins_build):
    builds = jenkins_build.get_running_builds()

    assert len(builds) == 2
    assert builds[0] == Build(
        name='RUN_JOB_LIST',
        number=2,
        url='http://example.com/job/RUN_JOB_LIST/job/job-one/2/',
        node='(master)',
        executor=4
    )
    assert builds[1] == Build(
        name='weekly',
        number=39,
        url='http://example.com/job/weekly/job/folder-one/job/job-two/39/',
        node='001',
        executor=0
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
            url='http://example.com/job/weekly/job/folder-one/job/job-two/109/'
        )
    )


def test_build_job(jenkins_build):
    assert jenkins_build.build_job('job', parameters=None) == 1
