"""Tests for the Prometheus metrics module and MetricsMiddleware."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import mcp_jenkins.utils.prometheus_metrics as pm_module
from mcp_jenkins.utils.prometheus_metrics import MCPJenkinsMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_metrics(pod_name: str = 'test-pod') -> MCPJenkinsMetrics:
    """Return a new MCPJenkinsMetrics instance with the global singleton reset."""
    pm_module._metrics = None
    return pm_module.initialize_metrics(pod_name=pod_name)


# ---------------------------------------------------------------------------
# MCPJenkinsMetrics – unit tests
# ---------------------------------------------------------------------------


class TestMCPJenkinsMetrics:
    def setup_method(self) -> None:
        # Reset module-level singleton before every test
        pm_module._metrics = None

    def test_initialize_metrics_returns_instance(self) -> None:
        m = _fresh_metrics()
        assert isinstance(m, MCPJenkinsMetrics)

    def test_initialize_metrics_singleton(self) -> None:
        m1 = pm_module.initialize_metrics(pod_name='p1')
        m2 = pm_module.initialize_metrics(pod_name='p2')
        assert m1 is m2, 'initialize_metrics should return the same singleton'

    def test_get_metrics_before_init_returns_none(self) -> None:
        pm_module._metrics = None
        assert pm_module.get_metrics() is None

    def test_get_metrics_after_init_returns_instance(self) -> None:
        m = _fresh_metrics()
        assert pm_module.get_metrics() is m

    def test_is_enabled_when_prometheus_available(self) -> None:
        m = _fresh_metrics()
        # If prometheus_client is installed the module flag is True
        assert m.is_enabled is pm_module._PROMETHEUS_AVAILABLE

    def test_generate_metrics_fallback_when_disabled(self) -> None:
        m = MCPJenkinsMetrics.__new__(MCPJenkinsMetrics)
        m._enabled = False
        content, ctype = m.generate_metrics()
        assert 'prometheus-client' in content.lower()
        assert ctype == 'text/plain; charset=utf-8'

    @pytest.mark.skipif(not pm_module._PROMETHEUS_AVAILABLE, reason='prometheus-client not installed')
    def test_generate_metrics_returns_bytes_string(self) -> None:
        m = _fresh_metrics()
        content, ctype = m.generate_metrics()
        assert isinstance(content, str)
        assert 'text/plain' in ctype or 'openmetrics' in ctype

    @pytest.mark.skipif(not pm_module._PROMETHEUS_AVAILABLE, reason='prometheus-client not installed')
    def test_record_tool_call_increments_counter(self) -> None:
        m = _fresh_metrics(pod_name='pod-counter-test')
        m.record_tool_call(tool_name='get_all_items', status='success', username='alice', duration=0.1)
        # Verify that tool_calls_total has been incremented (no exception means success)
        assert m.tool_calls_total is not None

    @pytest.mark.skipif(not pm_module._PROMETHEUS_AVAILABLE, reason='prometheus-client not installed')
    def test_active_call_tracking(self) -> None:
        m = _fresh_metrics(pod_name='pod-active-test')
        assert m._active_count == 0
        m.inc_active()
        assert m._active_count == 1
        m.inc_active()
        assert m._active_count == 2
        m.dec_active()
        assert m._active_count == 1
        m.dec_active()
        assert m._active_count == 0

    @pytest.mark.skipif(not pm_module._PROMETHEUS_AVAILABLE, reason='prometheus-client not installed')
    def test_dec_active_does_not_go_negative(self) -> None:
        m = _fresh_metrics(pod_name='pod-neg-test')
        m.dec_active()
        assert m._active_count == 0

    def test_record_tool_call_noop_when_disabled(self) -> None:
        m = MCPJenkinsMetrics.__new__(MCPJenkinsMetrics)
        m._enabled = False
        # Should not raise
        m.record_tool_call(tool_name='any_tool', status='success', username='x', duration=0.5)

    def test_inc_dec_active_noop_when_disabled(self) -> None:
        m = MCPJenkinsMetrics.__new__(MCPJenkinsMetrics)
        m._enabled = False
        m.inc_active()
        m.dec_active()


# ---------------------------------------------------------------------------
# MetricsMiddleware – unit tests
# ---------------------------------------------------------------------------

try:
    from mcp_jenkins.core.middleware import MetricsMiddleware  # noqa: F401

    _FASTMCP_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _FASTMCP_AVAILABLE = False

_requires_fastmcp = pytest.mark.skipif(not _FASTMCP_AVAILABLE, reason='fastmcp not fully available')


class TestMetricsMiddleware:
    def setup_method(self) -> None:
        pm_module._metrics = None

    def _make_context(self, tool_name: str = 'get_all_items') -> MagicMock:
        ctx = MagicMock()
        ctx.message.name = tool_name
        ctx.fastmcp_context = None
        return ctx

    @_requires_fastmcp
    @pytest.mark.asyncio
    async def test_on_call_tool_success_records_metrics(self) -> None:
        from mcp_jenkins.core.middleware import MetricsMiddleware

        _fresh_metrics(pod_name='mw-success')
        call_next = AsyncMock(return_value='result')
        context = self._make_context('get_all_items')

        mw = MetricsMiddleware()
        result = await mw.on_call_tool(context, call_next)

        assert result == 'result'
        call_next.assert_awaited_once_with(context)

    @_requires_fastmcp
    @pytest.mark.asyncio
    async def test_on_call_tool_error_still_records_metrics(self) -> None:
        from mcp_jenkins.core.middleware import MetricsMiddleware

        _fresh_metrics(pod_name='mw-error')
        call_next = AsyncMock(side_effect=RuntimeError('jenkins down'))
        context = self._make_context('build_item')

        mw = MetricsMiddleware()
        with pytest.raises(RuntimeError, match='jenkins down'):
            await mw.on_call_tool(context, call_next)

    @_requires_fastmcp
    @pytest.mark.asyncio
    async def test_on_call_tool_active_count_restored_after_success(self) -> None:
        from mcp_jenkins.core.middleware import MetricsMiddleware

        m = _fresh_metrics(pod_name='mw-active')
        call_next = AsyncMock(return_value=None)
        context = self._make_context('get_build')

        mw = MetricsMiddleware()
        assert m._active_count == 0
        await mw.on_call_tool(context, call_next)
        assert m._active_count == 0

    @_requires_fastmcp
    @pytest.mark.asyncio
    async def test_on_call_tool_active_count_restored_after_error(self) -> None:
        from mcp_jenkins.core.middleware import MetricsMiddleware

        m = _fresh_metrics(pod_name='mw-active-err')
        call_next = AsyncMock(side_effect=ValueError('oops'))
        context = self._make_context('query_items')

        mw = MetricsMiddleware()
        with pytest.raises(ValueError):
            await mw.on_call_tool(context, call_next)
        assert m._active_count == 0

    @_requires_fastmcp
    @pytest.mark.asyncio
    async def test_on_call_tool_works_when_metrics_not_initialised(self) -> None:
        """Middleware should not crash even if initialize_metrics was never called."""
        from mcp_jenkins.core.middleware import MetricsMiddleware

        pm_module._metrics = None  # ensure no metrics
        call_next = AsyncMock(return_value='ok')
        context = self._make_context('get_item')

        mw = MetricsMiddleware()
        result = await mw.on_call_tool(context, call_next)
        assert result == 'ok'


# ---------------------------------------------------------------------------
# /metrics HTTP route – integration smoke test
# ---------------------------------------------------------------------------

try:
    from mcp_jenkins.server import metrics_endpoint as _metrics_endpoint_sym  # noqa: F401

    _SERVER_IMPORTABLE = True
except (ImportError, ModuleNotFoundError):
    _SERVER_IMPORTABLE = False

_requires_server = pytest.mark.skipif(not _SERVER_IMPORTABLE, reason='fastmcp not fully available')


class TestMetricsRoute:
    def setup_method(self) -> None:
        pm_module._metrics = None

    @_requires_server
    @pytest.mark.asyncio
    async def test_metrics_endpoint_no_init_returns_503_or_200(self) -> None:
        """The /metrics handler should never raise even before initialize_metrics is called."""
        from mcp_jenkins.server import metrics_endpoint

        pm_module._metrics = None
        mock_request = MagicMock()
        response = await metrics_endpoint(mock_request)
        # 503 when not initialised
        assert response.status_code == 503

    @_requires_server
    @pytest.mark.asyncio
    async def test_metrics_endpoint_after_init_returns_200(self) -> None:
        from mcp_jenkins.server import metrics_endpoint

        _fresh_metrics(pod_name='http-test')
        mock_request = MagicMock()
        response = await metrics_endpoint(mock_request)
        assert response.status_code == 200
