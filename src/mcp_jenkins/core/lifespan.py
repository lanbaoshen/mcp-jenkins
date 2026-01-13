import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import get_http_request
from loguru import logger
from pydantic import BaseModel, ConfigDict

from mcp_jenkins.jenkins import Jenkins


class LifespanContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    jenkins_url: str | None
    jenkins_username: str | None
    jenkins_password: str | None
    jenkins_timeout: int = 5
    jenkins_verify_ssl: bool = True

    read_only: bool = False
    tool_regex: str = ''
    jenkins_session_singleton: bool = True


@asynccontextmanager
async def lifespan(app: FastMCP[LifespanContext]) -> AsyncIterator['LifespanContext']:
    jenkins_url = os.getenv('jenkins_url')
    jenkins_username = os.getenv('jenkins_username')
    jenkins_password = os.getenv('jenkins_password')

    jenkins_timeout = int(os.getenv('jenkins_timeout', '5'))
    jenkins_verify_ssl = os.getenv('jenkins_verify_ssl', 'true').lower() == 'true'
    jenkins_session_singleton = os.getenv('jenkins_session_singleton', 'true').lower() == 'true'

    read_only = os.getenv('read_only', 'false').lower() == 'true'
    tool_regex = os.getenv('tool_regex', '')

    yield LifespanContext(
        jenkins_url=jenkins_url,
        jenkins_username=jenkins_username,
        jenkins_password=jenkins_password,
        jenkins_timeout=jenkins_timeout,
        jenkins_verify_ssl=jenkins_verify_ssl,
        jenkins_session_singleton=jenkins_session_singleton,
        read_only=read_only,
        tool_regex=tool_regex,
    )


def jenkins(ctx: Context) -> Jenkins:
    if ctx.request_context.lifespan_context.jenkins_session_singleton and getattr(ctx.session, 'jenkins', None):
        return ctx.session.jenkins

    jenkins_url = ctx.request_context.lifespan_context.jenkins_url
    jenkins_username = ctx.request_context.lifespan_context.jenkins_username
    jenkins_password = ctx.request_context.lifespan_context.jenkins_password

    jenkins_timeout = ctx.request_context.lifespan_context.jenkins_timeout
    jenkins_verify_ssl = ctx.request_context.lifespan_context.jenkins_verify_ssl

    try:
        requests = get_http_request()

        jenkins_url = getattr(requests.state, 'jenkins_url', jenkins_url)
        jenkins_username = getattr(requests.state, 'jenkins_username', jenkins_username)
        jenkins_password = getattr(requests.state, 'jenkins_password', jenkins_password)

        logger.debug(f'Retrieved Jenkins auth from request state - url: {jenkins_url}, username: {jenkins_username}')
    except RuntimeError as e:
        logger.debug(f'No HTTP request context available, falling back to environment variables: {e}')
    except Exception as e:  # noqa: BLE001
        logger.error(
            f'Unexpected error retrieving Jenkins auth from request, falling back to environment variables: {e}'
        )

    if not all((jenkins_url, jenkins_username, jenkins_password)):
        msg = (
            'Jenkins authentication details are missing. '
            'Please provide them via x-jenkins-* headers '
            'or CLI arguments (--jenkins-url, --jenkins-username, --jenkins-password).'
        )
        raise ValueError(msg)

    logger.info(
        f'Creating Jenkins client with url: '
        f'{jenkins_url}, username: {jenkins_username}, timeout: {jenkins_timeout}, verify_ssl: {jenkins_verify_ssl}'
    )

    ctx.session.jenkins = Jenkins(
        url=jenkins_url,
        username=jenkins_username,
        password=jenkins_password,
        timeout=jenkins_timeout,
        verify_ssl=jenkins_verify_ssl,
    )

    return ctx.session.jenkins
