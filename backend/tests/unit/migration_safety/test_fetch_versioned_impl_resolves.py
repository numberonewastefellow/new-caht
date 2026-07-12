"""Every `fetch_versioned_implementation(...)` string target must resolve.

This is the dynamic-dispatch hub: ~166 call sites pass a `"onyx.<module>"` string +
attribute that are imported at RUNTIME, not statically. A missed rename leaves a
dead string that only fails when that code path fires. We AST-extract the literal
(module, attribute) pairs and resolve them.

Resolution mirrors the runtime contract:
  * `fetch_versioned_implementation` / `_with_fallback` -> the MIT `<module>` must
    exist and expose `<attribute>` (it is the always-present fallback).
  * `fetch_ee_implementation_or_noop` -> the impl lives in the EE mirror
    (`ee.<module>`); if that tree is present its attribute must resolve, otherwise
    the runtime returns a no-op, so a missing EE module is tolerated (skipped).

The scan reads current source, so it is rename-agnostic. After EE removal deletes
these helpers, the scan simply finds zero call sites and the test passes trivially.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from tests.unit.migration_safety.conftest import iter_source_files
from tests.unit.migration_safety.conftest import parse_source
from tests.unit.migration_safety.conftest import resolve_symbol

_FETCH_FUNCS = {
    "fetch_versioned_implementation",
    "fetch_versioned_implementation_with_fallback",
    "fetch_ee_implementation_or_noop",
}
_EE_NOOP = "fetch_ee_implementation_or_noop"


@dataclass(frozen=True)
class Target:
    func: str
    module: str
    attribute: str


def _literal(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_targets() -> tuple[list[Target], int]:
    targets: list[Target] = []
    dynamic = 0

    for path in iter_source_files():
        tree = parse_source(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name not in _FETCH_FUNCS:
                continue

            # module/attribute are the first two positional args, or kwargs.
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            module_node = node.args[0] if node.args else kw.get("module")
            attr_node = (
                node.args[1]
                if len(node.args) > 1
                else kw.get("attribute")
            )
            module = _literal(module_node)
            attribute = _literal(attr_node)
            if module is None or attribute is None:
                dynamic += 1
                continue
            targets.append(Target(name, module, attribute))

    return targets, dynamic


def test_no_dynamic_dispatch_survives_ee_removal() -> None:
    """The hub is GONE -- assert no call site came back.

    This assertion is inverted from what it was during the rename. Then, the job was
    "every dispatch string must resolve" (there were ~109 of them, and a missed rename
    left a dead string that only failed when that code path fired). EE removal deleted
    the hub and inlined every call site into a real import, so the invariant now is that
    ZERO remain: a reintroduced `fetch_versioned_implementation("om.x", "y")` would be a
    new string-keyed module path -- invisible to mypy, invisible to the import walk, and
    fatal only at runtime. That is the exact hazard this whole migration removed, so
    growing one back is a regression, not a neutral event.
    """
    targets, dynamic = _collect_targets()
    assert not targets and not dynamic, (
        "Dynamic dispatch reappeared. Import the symbol directly instead -- a module "
        "path in a string literal is checked by nothing:\n"
        + "\n".join(sorted(f"  {t.func}: {t.module}.{t.attribute}" for t in targets))
        + (f"\n  ...plus {dynamic} call site(s) with non-literal args" if dynamic else "")
    )


def test_fetch_versioned_targets_resolve() -> None:
    targets, dynamic = _collect_targets()
    if not targets:
        # Post-EE-removal steady state: nothing left to resolve. The real guard is
        # test_no_dynamic_dispatch_survives_ee_removal above.
        return
    print(f"[fetch_versioned] literal_targets={len(targets)} dynamic/skipped={dynamic}")

    failures: list[str] = []
    env_skips: list[str] = []

    for t in targets:
        # `resolve_symbol` accepts the MIT module OR its EE mirror -- covers both
        # MIT-resolvable and EE-only targets (external_permissions, enterprise_settings,
        # telemetry/posthog overrides, etc.). `fetch_ee_implementation_or_noop` targets
        # that resolve to neither are tolerated ONLY as env gaps, never as namespace.
        status = resolve_symbol(t.module, t.attribute)
        if status == "ok":
            continue
        if status == "env":
            env_skips.append(f"{t.func}: {t.module}.{t.attribute}")
            continue
        # namespace | missing_attr are real defects, EXCEPT ee-noop missing_attr,
        # which can legitimately vanish post-EE-removal (runtime returns no-op).
        if t.func == _EE_NOOP and status == "missing_attr":
            env_skips.append(f"{t.func}: {t.module}.{t.attribute} (noop)")
            continue
        failures.append(f"{t.func}: {t.module}.{t.attribute} [{status}]")

    if env_skips:
        print(f"[fetch_versioned] env/noop-tolerated {len(env_skips)} targets")

    assert not failures, (
        "Unresolvable fetch_versioned_* targets (missed rename / dead string):\n"
        + "\n".join(sorted(failures))
    )
