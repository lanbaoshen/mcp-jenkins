"""Prometheus metrics collection for the MCP Jenkins server.

Tracks tool usage (counter + latency histogram) and active concurrent calls.
Degrades gracefully when prometheus-client is not installed.

Usage::

    from mcp_jenkins.utils.prometheus_metrics import initialize_metrics, get_metrics

    metrics = initialize_metrics()          # call once at startup
    content, ctype = metrics.generate_metrics()  # serve at /metrics
"""

from __future__ import annotations

import os
import time
from typing import Any

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False


def _safe_metric(metric_class: type[Any], *args: Any, **kwargs: Any) -> Any | None:
    """Create a Prometheus metric, returning None if prometheus-client is missing.

    Handles the case where a metric with the same name was already registered
    (e.g. during tests that re-import modules) by finding and returning the
    existing collector via the registry's reverse name mapping.
    """
    if not _PROMETHEUS_AVAILABLE:
        return None
    try:
        return metric_class(*args, **kwargs)
    except ValueError as exc:
        if 'Duplicated timeseries' in str(exc):
            metric_name = args[0] if args else kwargs.get('name')
            # Use the registry's reverse name→collector map for reliable lookup
            names_to_collectors: dict = getattr(REGISTRY, '_names_to_collectors', {})
            if metric_name in names_to_collectors:
                return names_to_collectors[metric_name]
            # Fallback: iterate the forward collector→names mapping
            for collector in REGISTRY._collector_to_names:
                if getattr(collector, '_name', None) == metric_name:
                    return collector
            return None
        raise


_TOOL_DURATION_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)


class MCPJenkinsMetrics:
    """Prometheus metrics collector for the MCP Jenkins server.

    Metrics exposed:

    * ``mcp_jenkins_tool_calls_total``  – Counter  (tool_name, status, username, pod)
    * ``mcp_jenkins_tool_duration_seconds`` – Histogram (tool_name, username, pod)
    * ``mcp_jenkins_active_tool_calls`` – Gauge  (pod)
    """

    def __init__(self, pod_name: str | None = None) -> None:
        if not _PROMETHEUS_AVAILABLE:
            self._enabled = False
            return

        self._enabled = True
        self.pod_name: str = pod_name or os.environ.get('HOSTNAME', 'unknown')

        # How many times each tool has been called, broken down by outcome
        self.tool_calls_total = _safe_metric(
            Counter,
            'mcp_jenkins_tool_calls_total',
            'Total MCP tool invocations',
            ['tool_name', 'status', 'username', 'pod'],
        )

        # How long each tool call takes end-to-end
        self.tool_duration_seconds = _safe_metric(
            Histogram,
            'mcp_jenkins_tool_duration_seconds',
            'End-to-end MCP tool call duration in seconds',
            ['tool_name', 'username', 'pod'],
            buckets=_TOOL_DURATION_BUCKETS,
        )

        # Number of tool calls currently in-flight on this pod
        self.active_tool_calls = _safe_metric(
            Gauge,
            'mcp_jenkins_active_tool_calls',
            'Number of MCP tool calls currently executing',
            ['pod'],
        )

        self._active_count: int = 0

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def record_tool_call(
        self,
        tool_name: str,
        status: str,
        username: str,
        duration: float,
    ) -> None:
        """Increment counters / observe histogram after a tool call completes.

        Args:
            tool_name: Name of the MCP tool that was invoked.
            status:    ``"success"`` or ``"error"``.
            username:  The Jenkins username associated with the request, or
                       ``"anonymous"`` when not available.
            duration:  Wall-clock time in seconds for the full tool call.
        """
        if not self._enabled:
            return

        if self.tool_calls_total is not None:
            self.tool_calls_total.labels(
                tool_name=tool_name,
                status=status,
                username=username,
                pod=self.pod_name,
            ).inc()

        if self.tool_duration_seconds is not None:
            self.tool_duration_seconds.labels(
                tool_name=tool_name,
                username=username,
                pod=self.pod_name,
            ).observe(duration)

    def inc_active(self) -> None:
        """Increment the active-calls gauge (call when a tool call starts)."""
        if not self._enabled:
            return
        self._active_count += 1
        if self.active_tool_calls is not None:
            self.active_tool_calls.labels(pod=self.pod_name).set(self._active_count)

    def dec_active(self) -> None:
        """Decrement the active-calls gauge (call when a tool call finishes)."""
        if not self._enabled:
            return
        self._active_count = max(0, self._active_count - 1)
        if self.active_tool_calls is not None:
            self.active_tool_calls.labels(pod=self.pod_name).set(self._active_count)

    def generate_metrics(self) -> tuple[str, str]:
        """Produce a Prometheus-formatted scrape payload.

        Returns:
            ``(content, content_type)`` ready to send as an HTTP response.
            When prometheus-client is not installed both values are plain-text
            informational strings so the server can still respond on
            ``/metrics`` without crashing.
        """
        if not self._enabled:
            return (
                '# Prometheus metrics not available – '
                'install prometheus-client to enable them.\n',
                'text/plain; charset=utf-8',
            )
        return generate_latest().decode('utf-8'), CONTENT_TYPE_LATEST

    @property
    def is_enabled(self) -> bool:
        """``True`` when prometheus-client is installed and metrics are active."""
        return self._enabled


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_metrics: MCPJenkinsMetrics | None = None


def initialize_metrics(pod_name: str | None = None) -> MCPJenkinsMetrics:
    """Create (or return) the global :class:`MCPJenkinsMetrics` instance.

    Safe to call multiple times – the first call wins.

    Args:
        pod_name: Identifier for this pod/process.  Defaults to the
                  ``HOSTNAME`` environment variable or ``"unknown"``.

    Returns:
        The initialised :class:`MCPJenkinsMetrics` singleton.
    """
    global _metrics
    if _metrics is not None:
        return _metrics
    _metrics = MCPJenkinsMetrics(pod_name=pod_name)
    return _metrics


def get_metrics() -> MCPJenkinsMetrics | None:
    """Return the global metrics instance, or ``None`` if not yet initialised."""
    return _metrics
