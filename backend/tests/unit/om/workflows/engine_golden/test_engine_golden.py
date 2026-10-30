"""Golden regression tests for the workflow engine.

    python -m pytest tests/unit/om/workflows/engine_golden -q            # compare
    GOLDEN_UPDATE=1 python -m pytest tests/unit/om/workflows/engine_golden -q   # regenerate
    ENGINE_IMPL=v2 python -m pytest tests/unit/om/workflows/engine_golden -q    # other engine

See README.md in this folder.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from tests.unit.om.workflows.engine_golden.engines import engine_impl_name
from tests.unit.om.workflows.engine_golden.engines import get_engine
from tests.unit.om.workflows.engine_golden.recorder import run_scenario
from tests.unit.om.workflows.engine_golden.scenarios import ALLOWED_DIFFS
from tests.unit.om.workflows.engine_golden.scenarios import all_scenarios
from tests.unit.om.workflows.engine_golden.scenarios import template_paths

GOLDEN_DIR = Path(__file__).parent / "golden"
SCENARIOS = all_scenarios()


def _update_mode() -> bool:
    return os.environ.get("GOLDEN_UPDATE", "").strip().lower() in {"1", "true", "yes"}


def _dump(data: Any) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def diff_paths(a: Any, b: Any, path: str = "") -> list[str]:
    """JSON paths where a and b differ (lists compared index by index)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in list(a) + [k for k in b if k not in a]:
            sub = f"{path}.{k}" if path else str(k)
            if k not in a or k not in b:
                out.append(sub)
            else:
                out.extend(diff_paths(a[k], b[k], sub))
        return out
    if isinstance(a, list) and isinstance(b, list):
        out = []
        for i in range(max(len(a), len(b))):
            sub = f"{path}[{i}]"
            if i >= len(a) or i >= len(b):
                out.append(sub)
            else:
                out.extend(diff_paths(a[i], b[i], sub))
        return out
    return [] if a == b else [path]


def path_matches(path: str, pattern: str) -> bool:
    """Glob over JSON paths: only '*' is special (matches anything, incl. '.'
    and brackets); '[0]' is literal (unlike fnmatch character classes)."""
    import re

    regex = ".*".join(re.escape(part) for part in pattern.split("*"))
    return re.fullmatch(regex, path) is not None


def allowed_patterns(scenario_name: str) -> list[str]:
    patterns: list[str] = []
    for key, entries in ALLOWED_DIFFS.items():
        if path_matches(scenario_name, key):
            patterns.extend(p for p, _reason in entries)
    return patterns


def _lookup(data: Any, path: str) -> Any:
    import re

    cur = data
    for tok in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        try:
            cur = cur[int(tok[1:-1])] if tok.startswith("[") else cur[tok]
        except (KeyError, IndexError, TypeError):
            return "<missing>"
    return cur


def test_every_template_has_a_scenario() -> None:
    names = {s.name for s in SCENARIOS}
    missing = [p.stem for p in template_paths() if p.stem not in names]
    assert not missing, f"templates without a golden scenario: {missing}"
    assert len(template_paths()) >= 47


def test_no_orphan_golden_files() -> None:
    names = {s.name for s in SCENARIOS}
    orphans = sorted(p.stem for p in GOLDEN_DIR.glob("*.json") if p.stem not in names)
    assert not orphans, f"golden files without a scenario (delete them): {orphans}"


def test_allowed_diffs_mechanism() -> None:
    names = {s.name for s in SCENARIOS}
    for key, entries in ALLOWED_DIFFS.items():
        assert any(path_matches(n, key) for n in names), f"ALLOWED_DIFFS key {key!r} matches no scenario"
        assert all(reason.strip() for _p, reason in entries), f"{key}: every entry needs a reason"
    golden = {"runs": [{"executions": [{"status": "completed", "id": 1}], "packets": [1, 2]}]}
    actual = {"runs": [{"executions": [{"status": "failed", "id": 1}], "packets": [1, 2, 3]}]}
    diffs = diff_paths(golden, actual)
    assert diffs == ["runs[0].executions[0].status", "runs[0].packets[2]"]
    pats = allowed_patterns("fx_timeout_slow_step")
    assert [d for d in diffs if not any(path_matches(d, p) for p in pats)] == ["runs[0].packets[2]"]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.name for s in SCENARIOS])
def test_engine_golden(scenario: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = engine_impl_name()
    actual = run_scenario(scenario, get_engine(impl), monkeypatch)
    golden_path = GOLDEN_DIR / f"{scenario.name}.json"

    if _update_mode():
        if impl != "legacy" and not os.environ.get("GOLDEN_UPDATE_FORCE"):
            pytest.fail("GOLDEN_UPDATE with ENGINE_IMPL != legacy would overwrite the "
                        "reference behaviour; set GOLDEN_UPDATE_FORCE=1 if you really mean it")
        GOLDEN_DIR.mkdir(exist_ok=True)
        golden_path.write_text(_dump(actual), encoding="utf-8", newline="\n")
        return

    assert golden_path.exists(), (
        f"missing golden {golden_path.name}; run with GOLDEN_UPDATE=1 (legacy engine)"
    )
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    actual = json.loads(_dump(actual))  # same JSON round-trip as the stored file

    diffs = diff_paths(expected, actual)
    if impl != "legacy":
        patterns = allowed_patterns(scenario.name)
        diffs = [d for d in diffs if not any(path_matches(d, p) for p in patterns)]
    if diffs:
        shown = "\n".join(
            f"  {d}\n    golden: {json.dumps(_lookup(expected, d))[:300]}\n"
            f"    actual: {json.dumps(_lookup(actual, d))[:300]}"
            for d in diffs[:25]
        )
        pytest.fail(
            f"{scenario.name}: {len(diffs)} difference(s) vs golden (ENGINE_IMPL={impl}):\n{shown}"
            + ("\n  ..." if len(diffs) > 25 else "")
        )
