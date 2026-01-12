import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from loguru import logger
from pydantic import BaseModel, ConfigDict, HttpUrl

from mcp_jenkins.jenkins import Jenkins


class LifespanContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    read_only: bool = False
    tool_regex: str = ''

    jenkins: Jenkins


@asynccontextmanager
async def lifespan(app: FastMCP[LifespanContext]) -> AsyncIterator['LifespanContext']:
    read_only = os.getenv('read_only', 'false').lower() == 'true'
    tool_regex = os.getenv('tool_regex', '')

    yield LifespanContext(read_only=read_only, tool_regex=tool_regex, jenkins=_jenkins())


def _jenkins() -> Jenkins:
    jenkins_url = jenkins_username = jenkins_password = None

    try:
        requests = get_http_request()
        logger.debug(f'Got HTTP request: {requests.url}')
        logger.debug(f'Request.state attributes: {dir(requests.state)}')

        jenkins_url = requests.state.jenkins_url
        jenkins_username = requests.state.jenkins_username
        jenkins_password = requests.state.jenkins_password

        logger.debug(f'Retrieved Jenkins auth from request state - url: {jenkins_url}, username: {jenkins_username}')
    except RuntimeError as e:
        logger.debug(f'No HTTP request context available, falling back to environment variables: {e}')
    except Exception as e:  # noqa: BLE001
        logger.error(
            f'Unexpected error retrieving Jenkins auth from request, falling back to environment variables: {e}'
        )

    jenkins_url = jenkins_url or os.getenv('jenkins_url')
    jenkins_username = jenkins_username or os.getenv('jenkins_username')
    jenkins_password = jenkins_password or os.getenv('jenkins_password')

    jenkins_timeout = int(os.getenv('jenkins_timeout', '5'))
    jenkins_verify_ssl = os.getenv('jenkins_verify_ssl', 'true').lower() == 'true'

    if not all((jenkins_url, jenkins_username, jenkins_password)):
        msg = (
            'Jenkins authentication details are missing. '
            'Please provide them via X-Jenkins-* headers '
            'or CLI arguments (--jenkins-url, --jenkins-username, --jenkins-password).'
        )
        raise ValueError(msg)

    logger.info(
        f'Creating Jenkins client with url: '
        f'{jenkins_url}, username: {jenkins_username}, timeout: {jenkins_timeout}, verify_ssl: {jenkins_verify_ssl}'
    )

    return Jenkins(
        url=HttpUrl(jenkins_url),
        username=jenkins_username,
        password=jenkins_password,
        timeout=jenkins_timeout,
        verify_ssl=jenkins_verify_ssl,
    )
