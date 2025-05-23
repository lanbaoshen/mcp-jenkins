import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import AnyFunction

from mcp_jenkins.jenkins import JenkinsClient


@dataclass
class JenkinsContext:
    client: JenkinsClient


@asynccontextmanager
async def jenkins_lifespan(server: FastMCP) -> AsyncIterator[JenkinsContext]:
    try:
        jenkins_url = os.getenv('jenkins_url')
        jenkins_username = os.getenv('jenkins_username')
        jenkins_password = os.getenv('jenkins_password')
        jenkins_timeout = int(os.getenv('jenkins_timeout'))

        client = JenkinsClient(
            url=jenkins_url,
            username=jenkins_username,
            password=jenkins_password,
            timeout=jenkins_timeout,
        )

        # Provide context to the application
        yield JenkinsContext(client=client)
    finally:
        # Cleanup resources if needed
        pass


def client(ctx: Context) -> JenkinsClient:
    return ctx.request_context.lifespan_context.client


def enhance_mcp_tool(self) -> Callable[[AnyFunction], AnyFunction]:  # noqa: ANN001
    def decorator(fn: AnyFunction) -> AnyFunction:
        alias_name = os.getenv('tool_alias').replace('[fn]', fn.__name__)
        self.add_tool(fn, name=alias_name)
        return fn

    return decorator


mcp = FastMCP('mcp-jenkins', lifespan=jenkins_lifespan)
# Register the tool decorator with the FastMCP instance
mcp.tool = enhance_mcp_tool.__get__(mcp, type(mcp))


# Import the job and build modules here to avoid circular imports
from mcp_jenkins.server import build, job, node, queue_item  # noqa: E402, F401
