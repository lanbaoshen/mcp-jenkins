import pytest

from mcp_jenkins.jenkins.rest_endpoint import RestEndpoint


def test_rest_endpoint_new():
    assert RestEndpoint('api/json?depth={depth}')._fields == {'depth'}
    assert RestEndpoint('api/json')._fields == set()


def test_rest_endpoint_call():
    endpoint = RestEndpoint('api/json?depth={depth}')

    assert endpoint(depth=0) == 'api/json?depth=0'


def test_rest_endpoint_call_missing():
    endpoint = RestEndpoint('api/json?depth={depth}')

    with pytest.raises(KeyError) as exc_info:
        endpoint()

    assert str(exc_info.value) == '"Missing: {\'depth\'}"'
