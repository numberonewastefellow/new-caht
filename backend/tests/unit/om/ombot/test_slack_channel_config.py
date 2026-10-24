from unittest.mock import MagicMock
from unittest.mock import patch

from om.db.slack_channel_config import create_slack_channel_agent


def test_create_slack_channel_agent_reuses_existing_agent() -> None:
    db_session = MagicMock()
    existing_agent = MagicMock()
    existing_agent.id = 42
    db_session.scalar.return_value = existing_agent

    fake_tool = MagicMock()
    fake_tool.id = 7

    with (
        patch(
            "om.db.slack_channel_config.get_builtin_tool",
            return_value=fake_tool,
        ),
        patch("om.db.slack_channel_config.upsert_agent") as mock_upsert,
    ):
        mock_upsert.return_value = MagicMock()

        create_slack_channel_agent(
            db_session=db_session,
            channel_name="general",
            document_set_ids=[1],
        )

    mock_upsert.assert_called_once()
    assert mock_upsert.call_args.kwargs["agent_id"] == existing_agent.id
