import pytest

from mcp_jenkins.jenkins.model.item import Folder, Job
from mcp_jenkins.server import item


@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()

    mocker.patch('mcp_jenkins.server.item.jenkins', return_value=mock_jenkins)

    yield mock_jenkins


@pytest.mark.asyncio
async def test_get_all_items(mock_jenkins, mocker):
    mock_jenkins.get_items.return_value = [
        Job(fullname='job1', color='blue', name='job1', url='1', class_='Job'),
        Folder(fullname='job2', jobs=[], class_='Folder', name='folder', url='1'),
    ]

    assert await item.get_all_items.fn(mocker.Mock()) == [
        {'class_': 'Job', 'color': 'blue', 'fullname': 'job1', 'name': 'job1', 'url': '1'},
        {'class_': 'Folder', 'fullname': 'job2', 'jobs': [], 'name': 'folder', 'url': '1'},
    ]


@pytest.mark.asyncio
async def test_get_item(mock_jenkins, mocker):
    mock_jenkins.get_item.return_value = Job(fullname='job1', color='blue', name='job1', url='1', class_='Job')

    assert await item.get_item.fn(mocker.Mock(), fullname='job1') == {
        'class_': 'Job',
        'color': 'blue',
        'fullname': 'job1',
        'name': 'job1',
        'url': '1',
    }


@pytest.mark.asyncio
async def test_get_item_config(mock_jenkins, mocker):
    mock_jenkins.get_item_config.return_value = '<xml>config</xml>'

    assert await item.get_item_config.fn(mocker.Mock(), fullname='job1') == '<xml>config</xml>'


@pytest.mark.asyncio
async def test_update_item_config(mock_jenkins, mocker):
    config_xml = '<project><description>Updated</description></project>'
    mock_jenkins.update_item_config.return_value = None

    await item.update_item_config.fn(mocker.Mock(), fullname='job1', config=config_xml)

    mock_jenkins.update_item_config.assert_called_once_with(
        fullname='job1', config=config_xml
    )


@pytest.mark.asyncio
async def test_query_items(mock_jenkins, mocker):
    mock_jenkins.query_items.return_value = [
        Job(fullname='job1', color='blue', name='job1', url='1', class_='Job'),
    ]

    assert await item.query_items.fn(
        mocker.Mock(), class_pattern='.*', fullname_pattern='job.*', color_pattern='blue'
    ) == [
        {'class_': 'Job', 'color': 'blue', 'fullname': 'job1', 'name': 'job1', 'url': '1'},
    ]


@pytest.mark.asyncio
async def test_build_item(mock_jenkins, mocker):
    mock_jenkins.build_item.return_value = None

    await item.build_item.fn(
        mocker.Mock(), fullname='job1', params={'param1': 'value1'}, build_type='buildWithParameters'
    )

    mock_jenkins.build_item.assert_called_once_with(
        fullname='job1', params={'param1': 'value1'}, build_type='buildWithParameters'
    )
