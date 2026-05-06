import asyncio
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import click
from loguru import logger

if TYPE_CHECKING:
    pass

try:
    LOG_DIR = Path.home() / '.mcp_jenkins'
    logger.add(LOG_DIR / 'log.log', rotation='10 MB')
except Exception as e:  # noqa: BLE001
    logger.error(f'Failed to set up logger directory: {e}')

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _run_stdio(mcp: 'object', metrics_port: int) -> None:  # noqa: ANN001
    """Run the MCP server over stdio, optionally serving /metrics on a side-car port."""
    from fastmcp import FastMCP as _FastMCP

    if metrics_port > 0:
        import uvicorn
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import Response
        from starlette.routing import Route

        from mcp_jenkins.utils.prometheus_metrics import get_metrics, initialize_metrics

        initialize_metrics()

        async def metrics_handler(request: Request) -> Response:
            m = get_metrics()
            if m is None:
                return Response(
                    content='# Metrics not initialised yet.\n',
                    media_type='text/plain; charset=utf-8',
                    status_code=503,
                )
            content, content_type = m.generate_metrics()
            return Response(content=content, media_type=content_type)

        metrics_app = Starlette(routes=[Route('/metrics', metrics_handler, methods=['GET'])])
        config = uvicorn.Config(metrics_app, host='0.0.0.0', port=metrics_port, log_level='warning')  # noqa: S104
        server = uvicorn.Server(config)
        # Run both the MCP stdio server and the metrics HTTP server concurrently
        import asyncio as _asyncio

        await _asyncio.gather(
            cast(_FastMCP, mcp).run_async(transport='stdio'),
            server.serve(),
        )
    else:
        await cast(_FastMCP, mcp).run_async(transport='stdio')



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
@click.option(
    '--metrics-port',
    default=0,
    help=(
        'Port for a standalone Prometheus /metrics HTTP server. '
        'Only used with --transport stdio. '
        'Set to 0 (default) to disable the standalone server.'
    ),
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
    metrics_port: int,
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
        asyncio.run(_run_stdio(mcp, metrics_port))
    elif transport in ('sse', 'streamable-http'):
        asyncio.run(mcp.run_async(transport=transport, host=host, port=port))


if __name__ == '__main__':
    main()
