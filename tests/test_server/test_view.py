import pytest

from mcp_jenkins.server import view


@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()

    mocker.patch('mcp_jenkins.server.view.jenkins', return_value=mock_jenkins)

    yield mock_jenkins


@pytest.mark.asyncio
async def test_get_all_views(mock_jenkins, mocker):
    mock_jenkins.get_views.return_value = [
        {'name': 'All', 'url': 'https://example.com/view/All/'},
        {'name': 'frontend', 'url': 'https://example.com/view/frontend/'},
    ]

    result = await view.get_all_views(mocker.Mock())

    assert result == [
        {'name': 'All', 'url': 'https://example.com/view/All/'},
        {'name': 'frontend', 'url': 'https://example.com/view/frontend/'},
    ]
    mock_jenkins.get_views.assert_called_once()


@pytest.mark.asyncio
async def test_get_view(mock_jenkins, mocker):
    mock_jenkins.get_view.return_value = {
        'name': 'frontend',
        'jobs': [
            {'name': 'build-ui', 'url': 'https://example.com/job/build-ui/', 'color': 'blue'},
            {'name': 'lint-check', 'url': 'https://example.com/job/lint-check/', 'color': 'red'},
        ],
    }

    result = await view.get_view(mocker.Mock(), view_path='frontend')

    assert result == {
        'name': 'frontend',
        'jobs': [
            {'name': 'build-ui', 'url': 'https://example.com/job/build-ui/', 'color': 'blue'},
            {'name': 'lint-check', 'url': 'https://example.com/job/lint-check/', 'color': 'red'},
        ],
    }
    mock_jenkins.get_view.assert_called_once_with(view_path='frontend', depth=0)


@pytest.mark.asyncio
async def test_get_view_nested(mock_jenkins, mocker):
    mock_jenkins.get_view.return_value = {
        'name': 'nightly',
        'views': [
            {'name': 'nightly linux'},
            {'name': 'nightly windows'},
        ],
    }

    result = await view.get_view(mocker.Mock(), view_path='frontend/nightly')

    assert result['name'] == 'nightly'
    assert len(result['views']) == 2
    mock_jenkins.get_view.assert_called_once_with(view_path='frontend/nightly', depth=0)


@pytest.mark.asyncio
async def test_get_view_with_depth(mock_jenkins, mocker):
    mock_jenkins.get_view.return_value = {
        'name': 'frontend',
        'jobs': [{'name': 'build-ui', 'url': 'https://example.com/job/build-ui/', 'color': 'blue'}],
    }

    await view.get_view(mocker.Mock(), view_path='frontend', depth=1)

    mock_jenkins.get_view.assert_called_once_with(view_path='frontend', depth=1)
