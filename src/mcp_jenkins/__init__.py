import os

import click


@click.command()
@click.option('--jenkins-url', required=False)
@click.option('--jenkins-username', required=False)
@click.option('--jenkins-password', required=False)
@click.option('--jenkins-timeout', default=5)
@click.option('--read-only', default=False, is_flag=True, help='Whether to run in read-only mode, default is False')
@click.option('--transport', type=click.Choice(['stdio', 'sse', 'streamable-http']), default='stdio')
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
    jenkins_password: str,
    jenkins_timeout: int,
    read_only: bool,  # noqa: FBT001
    transport: str,
    port: int,
    tool_alias: str,
) -> None:
    """
    Jenkins' functionality for MCP
    """

    print("[DEBUG] Starting mcp-jenkins main()")
    print(f"[DEBUG] tool_alias: {tool_alias}")
    print(f"[DEBUG] jenkins_url: {jenkins_url}")
    print(f"[DEBUG] jenkins_username: {jenkins_username}")
    print(f"[DEBUG] jenkins_timeout: {jenkins_timeout}")
    print(f"[DEBUG] read_only: {read_only}")
    print(f"[DEBUG] transport: {transport}")
    print(f"[DEBUG] port: {port}")

    if '[fn]' not in tool_alias:
        print("[ERROR] Tool alias must contain [fn] placeholder")
        raise ValueError('Tool alias must contain [fn] placeholder')

    if jenkins_url:
        os.environ['jenkins_url'] = jenkins_url
    if jenkins_username:
        os.environ['jenkins_username'] = jenkins_username
    if jenkins_password:
        os.environ['jenkins_password'] = jenkins_password

    os.environ['jenkins_timeout'] = str(jenkins_timeout)
    os.environ['tool_alias'] = tool_alias
    os.environ['read_only'] = str(read_only).lower()


    print("[DEBUG] Importing mcp from mcp_jenkins.server ...")
    from mcp_jenkins.server import mcp
    print("[DEBUG] mcp imported successfully.")


    if transport in ['sse', 'streamable-http']:
        print(f"[DEBUG] Setting mcp.settings.port = {port}")
        mcp.settings.port = port
    print(f"[DEBUG] Running mcp with transport={transport}")
    mcp.run(transport=transport)


if __name__ == '__main__':
    main()
