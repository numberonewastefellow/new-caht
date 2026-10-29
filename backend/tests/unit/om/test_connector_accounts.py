import textwrap
from pathlib import Path

import pytest

from tests.connector_accounts import required_env
from tests.connector_accounts import skip_unprovisioned


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    suite = tmp_path / "suite"
    (suite / "slack").mkdir(parents=True)
    (suite / "conftest.py").write_text('import os\nX = os.environ["ROOT_TOKEN"]\n')
    (suite / "slack" / "conftest.py").write_text('import os\nY = os.environ["SLACK_BOT_TOKEN"]\n')
    test = suite / "slack" / "test_slack.py"
    test.write_text(
        textwrap.dedent(
            """
            import os
            REQUIRES_ENV = ["SLACK_CHANNEL", 'EXTRA_ONE']
            OPTIONAL = os.environ.get("NOT_REQUIRED")
            def test_x(): ...
            """
        )
    )
    return suite, test


def test_collects_hard_requirements_from_module_and_conftests(tmp_path: Path) -> None:
    suite, test = _tree(tmp_path)
    assert required_env(test, suite) == ["EXTRA_ONE", "ROOT_TOKEN", "SLACK_BOT_TOKEN", "SLACK_CHANNEL"]


def test_optional_environ_get_is_not_a_requirement(tmp_path: Path) -> None:
    suite, test = _tree(tmp_path)
    assert "NOT_REQUIRED" not in required_env(test, suite)


class _Item:
    def __init__(self, path: Path) -> None:
        self.fspath = path
        self.markers: list[pytest.MarkDecorator] = []

    def add_marker(self, marker: pytest.MarkDecorator) -> None:
        self.markers.append(marker)


def test_missing_variables_turn_into_a_skip_with_a_clear_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    suite, test = _tree(tmp_path)
    for name in ["EXTRA_ONE", "ROOT_TOKEN", "SLACK_BOT_TOKEN", "SLACK_CHANNEL"]:
        monkeypatch.delenv(name, raising=False)
    item = _Item(test)
    skip_unprovisioned([item], suite, "ACCOUNTS.md")  # type: ignore[list-item]
    assert len(item.markers) == 1
    reason = item.markers[0].kwargs["reason"]
    assert "SLACK_BOT_TOKEN" in reason and "ACCOUNTS.md" in reason


def test_provisioned_account_is_not_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    suite, test = _tree(tmp_path)
    for name in ["EXTRA_ONE", "ROOT_TOKEN", "SLACK_BOT_TOKEN", "SLACK_CHANNEL"]:
        monkeypatch.setenv(name, "x")
    item = _Item(test)
    skip_unprovisioned([item], suite, "ACCOUNTS.md")  # type: ignore[list-item]
    assert item.markers == []


def test_tests_outside_the_suite_root_are_untouched(tmp_path: Path) -> None:
    suite, _ = _tree(tmp_path)
    other = tmp_path / "elsewhere" / "test_y.py"
    other.parent.mkdir()
    other.write_text('import os\nos.environ["NEVER_SET"]\n')
    item = _Item(other)
    skip_unprovisioned([item], suite, "ACCOUNTS.md")  # type: ignore[list-item]
    assert item.markers == []


def test_any_of_group_is_satisfied_by_one_variable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "conftest.py").write_text('REQUIRES_ANY_ENV = ["TOKEN_A", "TOKEN_B"]\n')
    test = suite / "test_z.py"
    test.write_text("def test_z(): ...\n")
    monkeypatch.delenv("TOKEN_A", raising=False)
    monkeypatch.delenv("TOKEN_B", raising=False)
    item = _Item(test)
    skip_unprovisioned([item], suite, "ACCOUNTS.md")  # type: ignore[list-item]
    assert "TOKEN_A or TOKEN_B" in item.markers[0].kwargs["reason"]
    monkeypatch.setenv("TOKEN_B", "x")
    ok = _Item(test)
    skip_unprovisioned([ok], suite, "ACCOUNTS.md")  # type: ignore[list-item]
    assert ok.markers == []
