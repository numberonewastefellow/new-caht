"""Every dynamic-factory `module_path` string must resolve.

`connectors/factory.py` and `federated_connectors/factory.py` build connectors by
`importlib.import_module(mapping.module_path)` + `getattr(module, class_name)` at
RUNTIME. The registries hold ~105 (+ federated) `module_path="onyx.connectors...."`
strings that never fail at startup -- only when that connector is instantiated. This
resolves every one (rename-agnostic, MIT-or-EE + env tolerant).

Complements the existing `tests/unit/onyx/connectors/test_connector_factory.py`, whose
`module_path.startswith("onyx.connectors.")` literal must flip to the new root at
rename time; this suite instead reads the current registry with no hardcoded root.
"""

from __future__ import annotations

import pytest

from tests.unit.migration_safety.conftest import import_module_status
from tests.unit.migration_safety.conftest import qualified
from tests.unit.migration_safety.conftest import resolve_symbol

_REGISTRIES = [
    ("connectors.registry", "CONNECTOR_CLASS_MAP"),
    ("federated_connectors.registry", "FEDERATED_CONNECTOR_CLASS_MAP"),
]


@pytest.mark.parametrize("module_suffix,map_name", _REGISTRIES)
def test_factory_module_paths_resolve(module_suffix: str, map_name: str) -> None:
    status, registry_mod = import_module_status(qualified(module_suffix))
    if status == "namespace":
        raise AssertionError(f"Namespace error importing {module_suffix}: {registry_mod}")
    if status == "env":
        pytest.skip(f"Env gap importing {module_suffix}: {registry_mod}")

    class_map = getattr(registry_mod, map_name)
    assert class_map, f"{map_name} is empty"

    namespace_failures: list[str] = []
    env_skips: list[str] = []
    for source, mapping in class_map.items():
        result = resolve_symbol(mapping.module_path, mapping.class_name)
        if result in ("namespace", "missing_attr"):
            namespace_failures.append(
                f"{source}: {mapping.module_path}.{mapping.class_name} [{result}]"
            )
        elif result == "env":
            env_skips.append(f"{source}: {mapping.module_path}")

    if env_skips:
        print(f"[{map_name}] env-tolerated {len(env_skips)} mappings")

    assert not namespace_failures, (
        f"Unresolvable {map_name} module paths (missed rename / dead string):\n"
        + "\n".join(sorted(namespace_failures))
    )
