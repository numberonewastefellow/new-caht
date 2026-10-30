"""Registry of workflow node types, keyed by ``(type, version)``.

The registry is the single place the engine, the API and the editors look up
node types. Lookups are strict: an unknown type or version raises instead of
silently falling back, so a saved workflow never runs with a different
implementation than the one it was saved with.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from om.workflows.nodes.base import NodeTypeSpec
from om.workflows.nodes.base import UpgradeContext


class UnknownNodeTypeError(LookupError):
    """Raised when a ``(type, version)`` pair is not registered."""


class NodeUpgradeError(ValueError):
    """Raised when a node config cannot be upgraded to the requested version."""


class NodeTypeVersionInfo(BaseModel):
    """Catalog entry for one version of a node type (served to the editors)."""

    version: int
    label: str
    description: str
    category: str
    config_schema: dict[str, Any]
    modes: list[str]
    can_pause: bool
    is_container: bool
    deprecated: bool
    # True when configs of the previous version convert automatically.
    upgradable_from_previous: bool


class NodeTypeInfo(BaseModel):
    """Catalog entry for a node type with all of its registered versions."""

    type: str
    latest_version: int
    versions: list[NodeTypeVersionInfo]


class NodeUpgradeResult(BaseModel):
    """A config converted to a newer version of its node type."""

    from_version: int
    to_version: int
    config: dict[str, Any]


class NodeTypeRegistry:
    """Holds every registered node type version.

    Versions of a type must be registered in increasing order; the upgrade
    chain walks consecutive registered versions.
    """

    def __init__(self) -> None:
        self._specs: dict[str, dict[int, NodeTypeSpec]] = {}

    # ── Registration ──────────────────────────────────────────────────────

    def register(self, spec: NodeTypeSpec) -> None:
        versions = self._specs.setdefault(spec.node_type, {})
        if spec.version in versions:
            raise ValueError(
                f"Node type {spec.node_type!r} version {spec.version} is already registered"
            )
        if versions and spec.version < max(versions):
            raise ValueError(
                f"Node type {spec.node_type!r}: register versions in increasing order "
                f"(got {spec.version} after {max(versions)})"
            )
        versions[spec.version] = spec

    # ── Lookup ────────────────────────────────────────────────────────────

    def types(self) -> list[str]:
        return sorted(self._specs)

    def versions(self, node_type: str) -> list[int]:
        return sorted(self._versions_of(node_type))

    def is_registered(self, node_type: str, version: int) -> bool:
        return version in self._specs.get(node_type, {})

    def get(self, node_type: str, version: int) -> NodeTypeSpec:
        spec = self._versions_of(node_type).get(version)
        if spec is None:
            raise UnknownNodeTypeError(
                f"Node type {node_type!r} has no version {version} "
                f"(registered: {self.versions(node_type)})"
            )
        return spec

    def latest(self, node_type: str) -> NodeTypeSpec:
        versions = self._versions_of(node_type)
        return versions[max(versions)]

    def resolve(self, node_type: str, version: int | None) -> NodeTypeSpec:
        """Return the requested version, or the latest one when ``version`` is None.

        ``None`` is only meaningful when *creating* a node; stored nodes always
        carry an explicit version.
        """
        if version is None:
            return self.latest(node_type)
        return self.get(node_type, version)

    # ── Upgrades ──────────────────────────────────────────────────────────

    def upgrade_config(
        self,
        node_type: str,
        from_version: int,
        config: Mapping[str, Any],
        context: UpgradeContext | None = None,
        to_version: int | None = None,
    ) -> NodeUpgradeResult:
        """Convert ``config`` from ``from_version`` up to ``to_version`` (default: latest).

        Applies each spec's ``upgrade_from_previous`` in order and validates the
        result against the target version's config model.

        Raises:
            UnknownNodeTypeError: The type or one of the versions is unknown.
            NodeUpgradeError: The target is older than the source, or a version
                on the way has no upgrade function (a breaking change).
        """
        source = self.get(node_type, from_version)
        target = self.latest(node_type) if to_version is None else self.get(
            node_type, to_version
        )
        if target.version < source.version:
            raise NodeUpgradeError(
                f"Cannot downgrade {node_type!r} from v{source.version} to v{target.version}"
            )

        ctx = context or UpgradeContext()
        current = dict(config)
        for version in self.versions(node_type):
            if not (source.version < version <= target.version):
                continue
            spec = self.get(node_type, version)
            if spec.upgrade_from_previous is None:
                raise NodeUpgradeError(
                    f"{node_type!r} v{version} is a breaking change: no automatic "
                    f"upgrade from the previous version"
                )
            current = spec.upgrade_from_previous(current, ctx)

        validated = target.validate_config(current)
        return NodeUpgradeResult(
            from_version=source.version,
            to_version=target.version,
            config=validated.model_dump(mode="json"),
        )

    # ── Catalog ───────────────────────────────────────────────────────────

    def catalog(self, include_deprecated: bool = True) -> list[NodeTypeInfo]:
        """Describe every registered node type for the editors."""
        result: list[NodeTypeInfo] = []
        for node_type in self.types():
            specs = [
                self.get(node_type, v)
                for v in self.versions(node_type)
            ]
            infos = [
                _version_info(spec)
                for spec in specs
                if include_deprecated or not spec.deprecated
            ]
            if not infos:
                continue
            result.append(
                NodeTypeInfo(
                    type=node_type,
                    latest_version=self.latest(node_type).version,
                    versions=infos,
                )
            )
        return result

    # ── Internals ─────────────────────────────────────────────────────────

    def _versions_of(self, node_type: str) -> dict[int, NodeTypeSpec]:
        versions = self._specs.get(node_type)
        if not versions:
            raise UnknownNodeTypeError(f"Unknown node type {node_type!r}")
        return versions


def _version_info(spec: NodeTypeSpec) -> NodeTypeVersionInfo:
    return NodeTypeVersionInfo(
        version=spec.version,
        label=spec.label,
        description=spec.description,
        category=spec.category,
        config_schema=spec.config_model.model_json_schema(),
        modes=sorted(spec.capabilities.modes),
        can_pause=spec.capabilities.can_pause,
        is_container=spec.capabilities.is_container,
        deprecated=spec.deprecated,
        upgradable_from_previous=spec.upgrade_from_previous is not None,
    )
