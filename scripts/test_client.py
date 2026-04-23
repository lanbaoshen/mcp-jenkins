r"""
Interactive smoke-test client for the running mcp-jenkins server.

Usage
-----
1. Start the server in one terminal:
       .venv\Scripts\python -m mcp_jenkins ^
           --transport streamable-http ^
           --jenkins-url http://your-jenkins ^
           --jenkins-username your-user ^
           --jenkins-password your-token

2. In a second terminal run this script:
       .venv\Scripts\python scripts/test_client.py

   Optional env vars:
       MCP_URL          - server base URL      (default: http://localhost:9887)
       JENKINS_URL      - forwarded in headers (optional)
       JENKINS_USERNAME - forwarded in headers (optional)
       JENKINS_PASSWORD - forwarded in headers (optional)
"""

import asyncio
import json
import os
import sys

MCP_URL = os.environ.get("MCP_URL", "http://localhost:9887")
JENKINS_URL = os.environ.get("JENKINS_URL", "")
JENKINS_USERNAME = os.environ.get("JENKINS_USERNAME", "")
JENKINS_PASSWORD = os.environ.get("JENKINS_PASSWORD", "")


def _hdr() -> dict:
    h = {}
    if JENKINS_URL:
        h["x-jenkins-url"] = JENKINS_URL
    if JENKINS_USERNAME:
        h["x-jenkins-username"] = JENKINS_USERNAME
    if JENKINS_PASSWORD:
        h["x-jenkins-password"] = JENKINS_PASSWORD
    return h


async def main() -> None:
    try:
        from fastmcp import Client
        from fastmcp.client.transports.http import StreamableHttpTransport
    except ImportError:
        print("ERROR: fastmcp not installed – run:  uv pip install fastmcp")
        sys.exit(1)

    transport_url = f"{MCP_URL}/mcp/"
    print(f"\nConnecting to  {transport_url}\n{'='*55}")

    headers = _hdr()
    if headers:
        print(f"Jenkins headers: {list(headers.keys())}\n")

    transport = StreamableHttpTransport(transport_url, headers=headers)
    async with Client(transport) as client:
        # ── 1. List tools ──────────────────────────────────────────
        tools = await client.list_tools()
        print(f"Tools available ({len(tools)}):")
        for t in tools:
            desc = (t.description or "").split("\n")[0][:70]
            print(f"  • {t.name:<35} {desc}")

        # ── 2. Check /metrics endpoint ─────────────────────────────
        print(f"\n{'='*55}")
        print("Checking /metrics endpoint …")
        import urllib.request

        try:
            req = urllib.request.urlopen(f"{MCP_URL}/metrics", timeout=5)  # noqa: S310
            body = req.read().decode()
            lines = [l for l in body.splitlines() if not l.startswith("#")][:8]
            print(f"  HTTP {req.status}  – first non-comment lines:")
            for line in lines:
                print(f"    {line}")
        except Exception as exc:  # noqa: BLE001
            print(f"  /metrics not reachable ({exc})")

        # ── 3. Optional: call a tool interactively ─────────────────
        if len(sys.argv) > 1:
            tool_name = sys.argv[1]
            tool_args: dict = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
            print(f"\n{'='*55}")
            print(f"Calling tool '{tool_name}' with args {tool_args} …")
            result = await client.call_tool(tool_name, tool_args)
            for r in result:
                print(r)
        else:
            print(f"\n{'='*55}")
            print("Tip: pass a tool name (and JSON args) to call it:")
            print("  .venv\\Scripts\\python scripts\\test_client.py get_all_items")
            print('  .venv\\Scripts\\python scripts\\test_client.py get_item \'{"name":"my-job"}\'')


if __name__ == "__main__":
    asyncio.run(main())
