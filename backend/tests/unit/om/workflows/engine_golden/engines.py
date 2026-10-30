"""Pluggable engine implementations for the golden harness.

Select with ``ENGINE_IMPL=<name>`` (default ``legacy``). Every implementation
has the signature of ``om.workflows.workflow_engine.run_workflow`` and must be
a generator of ``Packet`` objects. To compare a new engine against the same
goldens, register it here and run::

    ENGINE_IMPL=v2 python -m pytest tests/unit/om/workflows/engine_golden -q
"""

from __future__ import annotations

import os
from collections.abc import Callable
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

EngineFn = Callable[..., Generator[Any, None, None]]


def _run_with_engine_flag(v2: bool, **kwargs: Any) -> Generator[Any, None, None]:
    """Run run_workflow() with the sequential engine pinned to legacy or v2.

    The flag is patched on the module (not via the environment) because
    ``WORKFLOW_ENGINE_V2`` is read once at import time from app_configs.
    """
    from om.workflows import workflow_engine

    with patch.object(workflow_engine, "WORKFLOW_ENGINE_V2", v2):
        yield from workflow_engine.run_workflow(**kwargs)


def _legacy(**kwargs: Any) -> Generator[Any, None, None]:
    return _run_with_engine_flag(False, **kwargs)


def _v2(**kwargs: Any) -> Generator[Any, None, None]:
    """The node-registry coordinator (om/workflows/sequential.py)."""
    return _run_with_engine_flag(True, **kwargs)


ENGINES: dict[str, EngineFn] = {
    "legacy": _legacy,
    "v2": _v2,
}


def engine_impl_name() -> str:
    return os.environ.get("ENGINE_IMPL", "legacy").strip() or "legacy"


def get_engine(name: str | None = None) -> EngineFn:
    name = name or engine_impl_name()
    if name not in ENGINES:
        raise KeyError(f"Unknown ENGINE_IMPL={name!r}; known: {sorted(ENGINES)}")
    return ENGINES[name]
