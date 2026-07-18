from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from om.db.agent import update_agents_display_priority


def _agent(agent_id: int, display_priority: int) -> SimpleNamespace:
    return SimpleNamespace(id=agent_id, display_priority=display_priority)


def test_update_display_priority_updates_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Precondition
    agent_a = _agent(1, 5)
    agent_b = _agent(2, 6)
    db_session = MagicMock()
    user = MagicMock()
    monkeypatch.setattr(
        "om.db.agent.get_raw_agents_for_user",
        lambda user, db_session, **kwargs: [agent_a, agent_b],  # noqa: ARG005
    )

    # Under test
    update_agents_display_priority(
        {agent_a.id: 0}, db_session, user, commit_db_txn=True
    )

    # Postcondition
    assert agent_a.display_priority == 0
    assert agent_b.display_priority == 6
    db_session.commit.assert_called_once_with()


def test_update_display_priority_invalid_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    # Precondition
    agent_a = _agent(1, 5)
    db_session = MagicMock()
    user = MagicMock()
    monkeypatch.setattr(
        "om.db.agent.get_raw_agents_for_user",
        lambda user, db_session, **kwargs: [agent_a],  # noqa: ARG005
    )

    # Under test
    with pytest.raises(ValueError):
        update_agents_display_priority(
            {agent_a.id: 0, 99: 1},
            db_session,
            user,
            commit_db_txn=True,
        )

    # Postcondition
    db_session.commit.assert_not_called()
