import asyncio
import os
import sys
from pathlib import Path

import click
from loguru import logger

try:
    LOG_DIR = Path.home() / '.mcp_jenkins'
    logger.add(LOG_DIR / 'log.log', rotation='10 MB')
except Exception as e:  # noqa: BLE001
    logger.error(f'Failed to set up logger directory: {e}')

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@click.command()
@click.option('--jenkins-url', required=False)
@click.option('--jenkins-username', required=False)
@click.option('--jenkins-password', required=False)
@click.option('--jenkins-timeout', default=5)
@click.option(
    '--jenkins-verify-ssl/--no-jenkins-verify-ssl',
    default=True,
    help='Whether to verify SSL certificates, default is True',
)
@click.option('--read-only', default=False, is_flag=True, help='Whether to run in read-only mode, default is False')
@click.option('--tool-regex', default='', help='Regex pattern to enable specific tools')
@click.option(
    '--jenkins-session-singleton/--no-jenkins-session-singleton',
    default=True,
    help='In the same session, does it share the Jenkins request instance, '
    'significantly reducing the number of instantiations and crumb requests',
)
@click.option('--transport', type=click.Choice(['stdio', 'sse', 'streamable-http']), default='stdio')
@click.option('--host', default='0.0.0.0', help='Host to bind to for SSE or Streamable HTTP transport')  # noqa: S104
@click.option('--port', default=9887, help='Port to listen on for SSE or Streamable HTTP transport')
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
    os.environ['read_only'] = str(read_only).lower()
    os.environ['tool_regex'] = tool_regex
    os.environ['jenkins_session_singleton'] = str(jenkins_session_singleton).lower()

    from mcp_jenkins.server import mcp

    if transport == 'stdio':
        asyncio.run(mcp.run_async(transport=transport))
    elif transport in ('sse', 'streamable-http'):
        asyncio.run(mcp.run_async(transport=transport, host=host, port=port))


if __name__ == '__main__':
    main()
