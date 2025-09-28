import os

import click


@click.command()
@click.option('--jenkins-url', required=True)
@click.option('--jenkins-username', required=True)
@click.option('--jenkins-password', help='Jenkins password (mutually exclusive with --jenkins-token)')
@click.option('--jenkins-token', help='Jenkins API token (mutually exclusive with --jenkins-password)')
@click.option('--jenkins-timeout', default=5)
@click.option('--read-only', default=False, is_flag=True, help='Whether to run in read-only mode, default is False')
@click.option('--transport', type=click.Choice(['stdio', 'sse']), default='stdio')
@click.option('--port', default=9887, help='Port to listen on for SSE transport')
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
    jenkins_password: str | None,
    jenkins_token: str | None,
    jenkins_timeout: int,
    read_only: bool,  # noqa: FBT001
    transport: str,
    port: int,
    tool_alias: str,
) -> None:
    """
    Jenkins' functionality for MCP
    """
    if '[fn]' not in tool_alias:
        raise ValueError('Tool alias must contain [fn] placeholder')

    # Validate authentication options
    if not jenkins_password and not jenkins_token:
        raise ValueError('Please provide either --jenkins-password or --jenkins-token')
    
    if jenkins_password and jenkins_token:
        raise ValueError('Please provide either --jenkins-password or --jenkins-token, not both')

    # Use token as password if provided (Jenkins API tokens work as passwords in HTTP Basic Auth)
    auth_password = jenkins_token if jenkins_token else jenkins_password

    if all([jenkins_url, jenkins_username, auth_password, jenkins_timeout]):
        os.environ['jenkins_url'] = jenkins_url
        os.environ['jenkins_username'] = jenkins_username
        os.environ['jenkins_password'] = auth_password
        os.environ['jenkins_timeout'] = str(jenkins_timeout)
        os.environ['tool_alias'] = tool_alias
        os.environ['read_only'] = str(read_only).lower()
    else:
        raise ValueError('Please provide valid jenkins_url, jenkins_username, and authentication credentials')

    from mcp_jenkins.server import mcp

    if transport == 'sse':
        mcp.settings.port = port
    mcp.run(transport=transport)


if __name__ == '__main__':
    main()
