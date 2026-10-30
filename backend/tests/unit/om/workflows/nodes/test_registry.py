"""Unit tests for the workflow node type registry."""

from collections.abc import Generator
from typing import Any

import pytest
from pydantic import BaseModel

from om.workflows.nodes.base import NodeCapabilities
from om.workflows.nodes.base import NodeTypeSpec
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.base import UpgradeContext
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.nodes.registry import NodeUpgradeError
from om.workflows.nodes.registry import UnknownNodeTypeError


class _NoopRunner:
    def run(self, node: Any, ctx: Any) -> Generator[Any, None, StepOutcome]:
        return StepOutcome(status=StepStatus.COMPLETED)
        yield  # pragma: no cover - makes this a generator


class _GreetV1(BaseModel):
    name: str


class _GreetV2(BaseModel):
    first_name: str
    excited: bool = False


class _GreetV3(BaseModel):
    first_name: str
    excited: bool = False
    language: str


def _spec(version: int, model: type[BaseModel], **kwargs: Any) -> NodeTypeSpec:
    return NodeTypeSpec(
        node_type="greet",
        version=version,
        label="Greet",
        description="Says hello.",
        category="test",
        config_model=model,
        runner=_NoopRunner(),
        **kwargs,
    )


def _v1_to_v2(config: dict[str, Any], _ctx: UpgradeContext) -> dict[str, Any]:
    return {"first_name": config["name"], "excited": False}


@pytest.fixture
def registry() -> NodeTypeRegistry:
    reg = NodeTypeRegistry()
    reg.register(_spec(1, _GreetV1))
    reg.register(_spec(2, _GreetV2, upgrade_from_previous=_v1_to_v2))
    return reg


class TestRegistration:
    def test_lookup_by_type_and_version(self, registry: NodeTypeRegistry) -> None:
        assert registry.get("greet", 1).config_model is _GreetV1
        assert registry.get("greet", 2).config_model is _GreetV2
        assert registry.latest("greet").version == 2
        assert registry.versions("greet") == [1, 2]
        assert registry.types() == ["greet"]

    def test_resolve_none_means_latest(self, registry: NodeTypeRegistry) -> None:
        assert registry.resolve("greet", None).version == 2
        assert registry.resolve("greet", 1).version == 1

    def test_duplicate_version_rejected(self, registry: NodeTypeRegistry) -> None:
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_spec(2, _GreetV2))

    def test_versions_must_increase(self) -> None:
        reg = NodeTypeRegistry()
        reg.register(_spec(2, _GreetV2))
        with pytest.raises(ValueError, match="increasing order"):
            reg.register(_spec(1, _GreetV1))

    def test_invalid_spec_rejected(self) -> None:
        with pytest.raises(ValueError):
            _spec(0, _GreetV1)
        with pytest.raises(ValueError):
            NodeTypeSpec(
                node_type="bad name!",
                version=1,
                label="x",
                description="x",
                category="x",
                config_model=_GreetV1,
                runner=_NoopRunner(),
            )


class TestStrictLookup:
    def test_unknown_type(self, registry: NodeTypeRegistry) -> None:
        with pytest.raises(UnknownNodeTypeError, match="Unknown node type"):
            registry.get("missing", 1)
        assert registry.is_registered("missing", 1) is False

    def test_unknown_version_does_not_fall_back(
        self, registry: NodeTypeRegistry
    ) -> None:
        with pytest.raises(UnknownNodeTypeError, match="no version 9"):
            registry.get("greet", 9)


class TestUpgrades:
    def test_upgrade_to_latest(self, registry: NodeTypeRegistry) -> None:
        result = registry.upgrade_config("greet", 1, {"name": "Ada"})
        assert result.from_version == 1
        assert result.to_version == 2
        assert result.config == {"first_name": "Ada", "excited": False}

    def test_upgrade_same_version_is_validation_only(
        self, registry: NodeTypeRegistry
    ) -> None:
        result = registry.upgrade_config("greet", 2, {"first_name": "Ada"})
        assert result.to_version == 2
        assert result.config == {"first_name": "Ada", "excited": False}

    def test_upgrade_chain_runs_every_hop(self) -> None:
        reg = NodeTypeRegistry()
        reg.register(_spec(1, _GreetV1))
        reg.register(_spec(2, _GreetV2, upgrade_from_previous=_v1_to_v2))
        reg.register(
            _spec(
                3,
                _GreetV3,
                upgrade_from_previous=lambda c, _ctx: {**c, "language": "en"},
            )
        )
        result = reg.upgrade_config("greet", 1, {"name": "Ada"})
        assert result.to_version == 3
        assert result.config == {
            "first_name": "Ada",
            "excited": False,
            "language": "en",
        }

    def test_breaking_version_cannot_auto_upgrade(self) -> None:
        reg = NodeTypeRegistry()
        reg.register(_spec(1, _GreetV1))
        reg.register(_spec(2, _GreetV2))  # no upgrade function → breaking
        with pytest.raises(NodeUpgradeError, match="breaking change"):
            reg.upgrade_config("greet", 1, {"name": "Ada"})

    def test_downgrade_rejected(self, registry: NodeTypeRegistry) -> None:
        with pytest.raises(NodeUpgradeError, match="downgrade"):
            registry.upgrade_config("greet", 2, {"first_name": "A"}, to_version=1)

    def test_upgraded_config_is_validated(self) -> None:
        reg = NodeTypeRegistry()
        reg.register(_spec(1, _GreetV1))
        reg.register(_spec(2, _GreetV2, upgrade_from_previous=lambda c, _ctx: c))
        with pytest.raises(ValueError):  # pydantic ValidationError
            reg.upgrade_config("greet", 1, {"name": "Ada"})

    def test_upgrade_context_is_passed(self) -> None:
        seen: list[UpgradeContext] = []

        def upgrader(c: dict[str, Any], ctx: UpgradeContext) -> dict[str, Any]:
            seen.append(ctx)
            return {"first_name": ctx.step_order_to_node_key[c["order"]]}

        class _V1(BaseModel):
            order: int

        reg = NodeTypeRegistry()
        reg.register(_spec(1, _V1))
        reg.register(_spec(2, _GreetV2, upgrade_from_previous=upgrader))
        ctx = UpgradeContext(step_order_to_node_key={3: "n_abc"})
        result = reg.upgrade_config("greet", 1, {"order": 3}, context=ctx)
        assert result.config["first_name"] == "n_abc"
        assert seen == [ctx]


class TestCatalog:
    def test_catalog_describes_versions(self, registry: NodeTypeRegistry) -> None:
        (info,) = registry.catalog()
        assert info.type == "greet"
        assert info.latest_version == 2
        assert [v.version for v in info.versions] == [1, 2]
        v2 = info.versions[1]
        assert v2.upgradable_from_previous is True
        assert v2.modes == ["sequential"]
        assert "first_name" in v2.config_schema["properties"]

    def test_catalog_can_hide_deprecated(self) -> None:
        reg = NodeTypeRegistry()
        reg.register(_spec(1, _GreetV1, deprecated=True))
        reg.register(_spec(2, _GreetV2, upgrade_from_previous=_v1_to_v2))
        (info,) = reg.catalog(include_deprecated=False)
        assert [v.version for v in info.versions] == [2]

    def test_capabilities_exposed(self) -> None:
        reg = NodeTypeRegistry()
        reg.register(
            _spec(
                1,
                _GreetV1,
                capabilities=NodeCapabilities(
                    modes=frozenset({"sequential", "llm_decision"}),
                    can_pause=True,
                ),
            )
        )
        (info,) = reg.catalog()
        assert info.versions[0].modes == ["llm_decision", "sequential"]
        assert info.versions[0].can_pause is True


class TestPresentJsonOutput:
    def test_single_string_field_is_shown_as_text(self) -> None:
        from om.workflows.nodes.base import present_json_output

        assert present_json_output('{"plan": "## Trip plan"}') == "## Trip plan"

    def test_other_json_is_formatted(self) -> None:
        from om.workflows.nodes.base import present_json_output

        assert present_json_output('{"a": 1, "b": 2}') == '```json\n{\n  "a": 1,\n  "b": 2\n}\n```'
        assert present_json_output('["x"]').startswith("```json")

    def test_plain_text_is_unchanged(self) -> None:
        from om.workflows.nodes.base import present_json_output

        assert present_json_output("hello") == "hello"
