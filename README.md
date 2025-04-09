# MCP Jenkins
[![smithery badge](https://smithery.ai/badge/@lanbaoshen/mcp-jenkins)](https://smithery.ai/server/@lanbaoshen/mcp-jenkins)
MCP server that integrates Jenkins

## Installation

### Installing via Smithery

To install mcp-jenkins for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@lanbaoshen/mcp-jenkins):

```bash
npx -y @smithery/cli install @lanbaoshen/mcp-jenkins --client claude
```

### Installing Manually
```
uvx mcp-jenkins

# or
pip install mcp-jenkins
```

## Usage

### Inspector
```
npx @modelcontextprotocol/inspector uvx mcp-jenkins --jenkins-url xxx --jenkins-username xxx --jenkins-password xxx

# or
npx @modelcontextprotocol/inspector uv run mcp-jenkins --jenkins-url xxx --jenkins-username xxx --jenkins-password xxx
```

### Optional Arguments
- `--jenkins-timeout`: Timeout for Jenkins API requests, default is 5 seconds
- `--transport`: [stdio|sse]
- `--port`: Port to listen on for SSE transport


### Available Tools

| Tool               | Description                  |
|--------------------|------------------------------|
| get_all_jobs       | Get all jobs                 |
| get_job_config     | Get job config               |
| search_jobs        | Search job by specific field |
| get_running_builds | Get running builds           |


### AutoGen
```python
import asyncio

from autogen_ext.tools.mcp import StdioMcpToolAdapter, StdioServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken


async def main() -> None:
    # Create server params for the remote MCP service
    server_params = StdioServerParams(
        command='uv',
        args=[
            'run',
            'mcp-jenkins',
            '--jenkins-username',
            'xxx',
            '--jenkins-password',
            'xxx',
            '--jenkins-url',
            'xxx'
        ],
        # command='uvx',
        # args=[
        #     'mcp-jenkins',
        #     '--jenkins-username',
        #     'xxx',
        #     '--jenkins-password',
        #     'xxx',
        #     '--jenkins-url',
        #     'xxx'
        # ],
    )

    # Get the translation tool from the server
    adapter = await StdioMcpToolAdapter.from_server_params(server_params, 'get_all_jobs')

    # Create an agent that can use the translation tool
    agent = AssistantAgent(
        name='jenkins_assistant',
        model_client=[Replace_with_your_model_client],
        tools=[adapter],
    )

    # Let the agent translate some text
    await Console(
        agent.run_stream(task='Get all jobs', cancellation_token=CancellationToken())
    )


if __name__ == "__main__":
    asyncio.run(main())
```


## Development
If you only want to use the mcp-server, you can skip this and below steps.

```shell
uv sync --frozen --all-extras --dev
```

```shell
# pre commit
pre-commit run --all-files
```

```shell
# UT
uv run pytest --cov=mcp_jenkins
```
