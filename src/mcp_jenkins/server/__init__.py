import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal

from mcp.server.fastmcp import Context
from mcp.server.fastmcp import FastMCP as _FastMCP
from mcp.types import AnyFunction

from mcp_jenkins.jenkins import JenkinsClient


class FastMCP(_FastMCP):
    def tool(
        self, name: str | None = None, description: str | None = None, tag: Literal['read', 'write'] = 'read'
    ) -> Callable[[AnyFunction], AnyFunction]:
        """Decorator to register a tool.

        Tools can optionally request a Context object by adding a parameter with the
        Context type annotation. The context provides access to MCP capabilities like
        logging, progress reporting, and resource access.

        Args:
            name: Optional name for the tool (defaults to function name)
            description: Optional description of what the tool does
            tag: Optional tag to indicate if the tool is read-only or write-capable.
                Defaults to None, which means it can be either.

        Example:
            @server.tool()
            def my_tool(x: int) -> str:
                return str(x)

            @server.tool()
            def tool_with_context(x: int, ctx: Context) -> str:
                ctx.info(f"Processing {x}")
                return str(x)

            @server.tool()
            async def async_tool(x: int, context: Context) -> str:
                await context.report_progress(50, 100)
                return str(x)
        """
        # Check if user passed function directly instead of calling decorator
        if callable(name):
            raise TypeError(
                'The @tool decorator was used incorrectly. Did you forget to call it? Use @tool() instead of @tool'
            )

        def decorator(fn: AnyFunction) -> AnyFunction:
            alias_name = name or os.getenv('tool_alias').replace('[fn]', fn.__name__)
            # Not in read-only mode
            if os.getenv('read_only', 'false') == 'false':
                self.add_tool(fn, name=alias_name)
            # In read-only mode
            elif tag == 'read':
                self.add_tool(fn, name=alias_name)
            return fn

        return decorator


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


mcp = FastMCP('mcp-jenkins', lifespan=jenkins_lifespan)

# Import the job and build modules here to avoid circular imports
from mcp_jenkins.server import build, job, node, queue_item  # noqa: E402, F401
