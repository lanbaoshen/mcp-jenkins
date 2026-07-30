import asyncio
import os
import sys
from pathlib import Path

import click
from dotenv import find_dotenv, load_dotenv
from loguru import logger

try:
    LOG_DIR = Path.home() / '.mcp_jenkins'
    logger.add(LOG_DIR / 'log.log', rotation='10 MB')
except Exception as e:  # noqa: BLE001
    logger.error(f'Failed to set up logger directory: {e}')

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _load_env_file(ctx: click.Context, param: click.Parameter, value: str | None) -> str | None:  # noqa: ARG001
    # Eager so JENKINS_* variables from the file are visible to the other options' envvar lookups below.
    # find_dotenv(usecwd=True) is used instead of load_dotenv()'s own discovery, which locates the
    # .env file relative to the caller's source file rather than the current working directory.
    load_dotenv(dotenv_path=value or find_dotenv(usecwd=True))
    return value


@click.command()
@click.option(
    '--env-file',
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    is_eager=True,
    expose_value=False,
    callback=_load_env_file,
    help='Path to a .env file to load configuration from. If omitted, a .env file in the current '
    'directory (or a parent directory) is loaded automatically if present.',
)
@click.option('--jenkins-url', required=False, envvar='JENKINS_URL')
@click.option('--jenkins-username', required=False, envvar='JENKINS_USERNAME')
@click.option('--jenkins-password', required=False, envvar='JENKINS_PASSWORD')
@click.option('--jenkins-timeout', default=5, envvar='JENKINS_TIMEOUT')
@click.option(
    '--jenkins-verify-ssl/--no-jenkins-verify-ssl',
    default=True,
    envvar='JENKINS_VERIFY_SSL',
    help='Whether to verify SSL certificates, default is True',
)
@click.option(
    '--read-only',
    default=False,
    is_flag=True,
    help='Whether to run in read-only mode, default is False',
)
@click.option(
    '--tool-regex',
    default='',
    help='(Deprecated) Regex pattern to enable specific tools',
)
@click.option(
    '--jenkins-session-singleton/--no-jenkins-session-singleton',
    default=True,
    help='In the same session, does it share the Jenkins request instance, '
    'significantly reducing the number of instantiations and crumb requests',
)
@click.option(
    '--transport',
    type=click.Choice(['stdio', 'sse', 'streamable-http']),
    default='stdio',
)
@click.option(
    '--host',
    default='0.0.0.0',
    help='Host to bind to for SSE or Streamable HTTP transport',
)  # noqa: S104
@click.option(
    '--port',
    default=9887,
    help='Port to listen on for SSE or Streamable HTTP transport',
)
def main(
    jenkins_url: str,
    jenkins_username: str,
    jenkins_password: str,
    jenkins_timeout: int,
    jenkins_verify_ssl: bool,  # noqa: FBT001
    read_only: bool,  # noqa: FBT001
    tool_regex: str,
    jenkins_session_singleton: bool,  # noqa: FBT001
    transport: str,
    host: str,
    port: int,
) -> None:
    if jenkins_url:
        os.environ['jenkins_url'] = jenkins_url
    if jenkins_username:
        os.environ['jenkins_username'] = jenkins_username
    if jenkins_password:
        os.environ['jenkins_password'] = jenkins_password

    os.environ['jenkins_timeout'] = str(jenkins_timeout)
    os.environ['jenkins_verify_ssl'] = str(jenkins_verify_ssl).lower()
    os.environ['jenkins_session_singleton'] = str(jenkins_session_singleton).lower()

    from mcp_jenkins.server import mcp

    if read_only:
        mcp.enable(tags={'read'}, only=True)

    if tool_regex:
        logger.warning('The [--tool-regex] option is deprecated and will be removed in future versions.')

    if transport == 'stdio':
        asyncio.run(mcp.run_async(transport=transport))
    elif transport in ('sse', 'streamable-http'):
        asyncio.run(mcp.run_async(transport=transport, host=host, port=port))


if __name__ == '__main__':
    main()
