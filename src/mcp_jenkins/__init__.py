import os

import click
from mcp.server.transport_security import TransportSecuritySettings


@click.command()
@click.option('--jenkins-url', required=True)
@click.option('--jenkins-username', required=True)
@click.option('--jenkins-password', required=True)
@click.option('--jenkins-timeout', default=5)
@click.option('--read-only', default=False, is_flag=True, help='Whether to run in read-only mode, default is False')
@click.option('--transport', type=click.Choice(['stdio', 'sse', 'streamable-http']), default='stdio')
@click.option('--port', default=9887, help='Port to listen on for SSE transport')
@click.option('--host', default='127.0.0.1', help='Host to bind to for SSE/streamable-http transport')
@click.option('--stateless-http', default=False, is_flag=True, help='Enable stateless HTTP mode for AgentCore Runtime compatibility')
@click.option(
    '--tool-alias',
    default='[fn]',
    help='The alias name for the server tool, use [fn] to replace with the origin tool name. '
    'For example: If set to [fn]_on_commit_server, '
    'the `get_running_builds` tool will be `get_running_builds_on_commit_server`.',
)
def main(
    jenkins_url: str,
    jenkins_username: str,
    jenkins_password: str,
    jenkins_timeout: int,
    read_only: bool,  # noqa: FBT001
    transport: str,
    port: int,
    host: str,
    stateless_http: bool,  # noqa: FBT001
    tool_alias: str,
) -> None:
    """
    Jenkins' functionality for MCP
    """
    if '[fn]' not in tool_alias:
        raise ValueError('Tool alias must contain [fn] placeholder')

    if all([jenkins_url, jenkins_username, jenkins_password, jenkins_timeout]):
        os.environ['jenkins_url'] = jenkins_url
        os.environ['jenkins_username'] = jenkins_username
        os.environ['jenkins_password'] = jenkins_password
        os.environ['jenkins_timeout'] = str(jenkins_timeout)
        os.environ['tool_alias'] = tool_alias
        os.environ['read_only'] = str(read_only).lower()
    else:
        raise ValueError('Please provide valid jenkins_url, jenkins_username, and jenkins_password')

    from mcp_jenkins.server import mcp

    if transport in ['sse', 'streamable-http']:
        mcp.settings.port = port
        mcp.settings.host = host
        mcp.settings.stateless_http = stateless_http
        # AgentCore Runtime compatibility: Disable Host header validation when stateless_http is enabled
        if stateless_http:
            mcp.settings.transport_security = TransportSecuritySettings(
                enable_dns_rebinding_protection=False
            )
    mcp.run(transport=transport)


if __name__ == '__main__':
    main()
