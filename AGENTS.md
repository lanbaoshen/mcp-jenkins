# mcp-jenkins

Bridges Jenkins CI with AI language models via Anthropic's Model Context Protocol (MCP). Jenkins operations are exposed as MCP tools that LLM clients invoke.

## Build and Test

```bash
# Install (requires uv)
uv sync --group dev

# Run tests with coverage
uv run pytest --cov=src

# Lint and format
uv run ruff check .
uv run ruff format .

# Pre-commit (runs tests + ruff)
pre-commit run --all-files
```

## Architecture

```
src/mcp_jenkins/
├── __init__.py          # CLI entry point (click)
├── core/                # Lifespan context + ASGI auth middleware
├── jenkins/             # Jenkins REST client + URL templates + Pydantic models
└── server/              # MCP tool definitions (@mcp.tool decorators)
```

**Credential resolution** (in `core/lifespan.py`): session singleton cache → HTTP request headers (`x-jenkins-url`, `x-jenkins-username`, `x-jenkins-password`) → env vars set from CLI args. Always call `jenkins(ctx)` inside tool functions to obtain the client; never instantiate `Jenkins` directly.

**Read-only mode:** Tools that mutate Jenkins state must carry `tags=['write']`. Tools tagged `'read'` remain available when `--read-only` is passed. Every new tool must have exactly one of these two tags.

## Conventions

### Adding a new MCP tool

1. Add the function in the appropriate `server/*.py` module (or create a new module and import it in `server/__init__.py`).
2. Decorate with `@mcp.tool(tags=['read'])` or `@mcp.tool(tags=['write'])`.
3. First argument must be `ctx: Context`; all subsequent arguments are keyword-only domain params.
4. Return `model.model_dump(exclude_none=True)` (or a `list` / `dict` of such).
5. Use `jenkins(ctx)` to get the Jenkins client — never store it in module-level state.

```python
from mcp_jenkins.server import mcp
from mcp_jenkins.core import jenkins

@mcp.tool(tags=['read'])
async def get_something(ctx: Context, fullname: str) -> dict:
    """Short description.

    Args:
        ctx: MCP context.
        fullname: Full job name, e.g. "folder/job".

    Returns:
        Serialised model dict.
    """
    return jenkins(ctx).get_something(fullname=fullname).model_dump(exclude_none=True)
```

### Adding a new REST endpoint

- Add a `RestEndpoint('{field}/...')` constant in `jenkins/rest_endpoint.py`.
- Add the corresponding method in `jenkins/rest_client.py` using keyword-only parameters.
- Add a Pydantic model in `jenkins/model/` if the response introduces new fields. Field names must match Jenkins JSON keys exactly (no aliasing except `_class` → `class_`).

### Testing

Mirror the module path: `src/mcp_jenkins/server/build.py` → `tests/test_server/test_build.py`.

Every `test_server/*.py` must use this fixture:

```python
@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()
    mocker.patch('mcp_jenkins.server.<module>.jenkins', return_value=mock_jenkins)
    yield mock_jenkins
```

Tool tests are `async` and use `@pytest.mark.asyncio`. Pass `mocker.Mock()` as `ctx`. Assert on the returned `dict` and verify the Jenkins client call with `assert_called_once_with(...)`.

## Key References

- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution workflow and commit message format
- [docker/DOCKER.md](docker/DOCKER.md) — running via Docker / docker-compose
- [README.md](README.md) — full tool inventory and client configuration examples
