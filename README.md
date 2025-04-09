# MCP Jenkins
![PyPI Version](https://img.shields.io/pypi/v/mcp-jenkins)
![PyPI - Downloads](https://img.shields.io/pypi/dm/mcp-jenkins)
[![PyPI Downloads](https://static.pepy.tech/badge/mcp-jenkins)](https://pepy.tech/projects/mcp-jenkins)
![License](https://img.shields.io/github/license/lanbaoshen/mcp-jenkins)
[![smithery badge](https://smithery.ai/badge/@lanbaoshen/mcp-jenkins)](https://smithery.ai/server/@lanbaoshen/mcp-jenkins)

The Model Context Protocol (MCP) is an open-source implementation that bridges Jenkins with AI language models following Anthropic's MCP specification. This project enables secure, contextual AI interactions with Jenkins tools while maintaining data privacy and security.

## Setup Guide

### Installation
Choose one of these installation methods:
```
# Using uv (recommended)
pip install uv
uvx mcp-jenkins

# Using pip
pip install mcp-jenkins

# Using Smithery
npx -y @smithery/cli@latest install @lanbaoshen/mcp-jenkins --client claude
```

### Configuration and Usage

#### Cursor
1. Open Cursor Settings
2. Navigate to MCP
3. Click + Add new global MCP server

This will create or edit the ~/.cursor/mcp.json file with your MCP server configuration.
```shell
{
  "mcpServers": {
    "mcp-jenkins": {
      "command": "uvx",
      "args": [
        "mcp-jenkins",
        "--jenkins-url=xxx",
        "--jenkins-username=xxx",
        "--jenkins-password=xxx"
      ]
    }
  }
}
```

#### line arguments
```shell
# Stdio Mode
uvx mcp-jenkins --jenkins-url xxx --jenkins-username xxx --jenkins-password xxx

# SSE Mode
uvx mcp-jenkins --jenkins-url xxx --jenkins-username xxx --jenkins-password xxx --transport sse --port 9887
```

#### AutoGen
<details>
<summary>Install and exec</summary>

Install autogen:
```shell
pip install "autogen-ext[azure,ollama,openai,mcp]" autogen-chat
```

Run python scripts:
```python
import asyncio

from autogen_ext.tools.mcp import StdioMcpToolAdapter, StdioServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken


async def main() -> None:
    # Create server params for the remote MCP service
    server_params = StdioServerParams(
        command='uvx',
        args=[
            'mcp-jenkins',
            '--jenkins-username',
            'xxx',
            '--jenkins-password',
            'xxx',
            '--jenkins-url',
            'xxx'
        ],
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

</details>

## Available Tools
| Tool               | Description                  |
|--------------------|------------------------------|
| get_all_jobs       | Get all jobs                 |
| get_job_config     | Get job config               |
| search_jobs        | Search job by specific field |
| get_running_builds | Get running builds           |
| get_build_info     | Get build info               |


## Development & Debugging
```shell
# Using MCP Inspector
# For installed package
npx @modelcontextprotocol/inspector uvx mcp-jenkins --jenkins-url xxx --jenkins-username xxx --jenkins-password xxx

# For local development version
npx @modelcontextprotocol/inspector uv --directory /path/to/your/mcp-jenkins run mcp-jenkins --jenkins-url xxx --jenkins-username xxx --jenkins-password xxx
```

## License
Licensed under MIT - see [LICENSE](LICENSE) file. This is not an official Jenkins product.
