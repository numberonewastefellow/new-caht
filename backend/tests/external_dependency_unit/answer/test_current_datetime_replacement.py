import re
from datetime import datetime

from sqlalchemy.orm import Session

from om.chat.models import AnswerStreamPart
from om.chat.models import StreamingError
from om.chat.message_handler import stream_chat_message
from om.db.chat import create_chat_session
from om.db.models import User
from om.db.agent import get_agent_by_id
from om.server.query_and_chat.models import MessageResponseIDInfo
from om.server.query_and_chat.models import SendMessageRequest
from om.server.query_and_chat.streaming_models import AgentResponseDelta
from tests.external_dependency_unit.answer.conftest import ensure_default_llm_provider
from tests.external_dependency_unit.conftest import create_test_user


def test_stream_chat_current_date_response(
    db_session: Session,
    full_deployment_setup: None,  # noqa: ARG001
    mock_external_deps: None,  # noqa: ARG001
) -> None:
    """Smoke test that asking for current date yields a streamed response.

    This exercises the full chat path using the default agent, ensuring
    the system prompt makes it to the LLM and a response is returned.
    """
    # Ensure LLM provider exists
    ensure_default_llm_provider(db_session)

    # Create user, agent, session
    test_user: User = create_test_user(db_session, email_prefix="test_current_date")
    default_agent = get_agent_by_id(
        agent_id=0, user=test_user, db_session=db_session, is_for_edit=False
    )
    chat_session = create_chat_session(
        db_session=db_session,
        description="Test current date question",
        user_id=test_user.id if test_user else None,
        agent_id=default_agent.id,
    )

    chat_request = SendMessageRequest(
        message="Please respond only with the current date in the format 'Weekday Month DD, YYYY'.",
        chat_session_id=chat_session.id,
    )

    gen = stream_chat_message(
        new_msg_req=chat_request,
        user=test_user,
        db_session=db_session,
    )

    raw: list[AnswerStreamPart] = []
    content = ""
    had_error = False

    for pkt in gen:
        raw.append(pkt)
        if hasattr(pkt, "obj") and isinstance(pkt.obj, AgentResponseDelta):
            if pkt.obj.content:
                content += pkt.obj.content
        if hasattr(pkt, "obj") and isinstance(pkt.obj, StreamingError):
            had_error = True
            break

    assert not had_error, "Should not error when answering current date"
    assert any(
        isinstance(p, MessageResponseIDInfo) for p in raw
    ), "Should yield a message ID"
    assert len(content) > 0, "Should stream some assistant content"

    # Validate the response contains a properly formatted current date string
    match = re.search(r"[A-Za-z]+ [A-Za-z]+ \d{1,2}, \d{4}", content)
    assert match, f"Expected a date in content, got: {content[:200]}..."

    timestamp_str = match.group(0)
    timestamp_dt = datetime.strptime(timestamp_str, "%A %B %d, %Y")
    now = datetime.now()

    assert timestamp_dt.strftime("%A") == now.strftime(
        "%A"
    ), f"Expected weekday {now.strftime('%A')}, got {timestamp_dt.strftime('%A')}"
    assert timestamp_dt.strftime("%B") == now.strftime(
        "%B"
    ), f"Expected month {now.strftime('%B')}, got {timestamp_dt.strftime('%B')}"
    assert timestamp_dt.day == now.day and timestamp_dt.year == now.year, (
        f"Expected day {now.strftime('%d')} and year {now.strftime('%Y')}, "
        f"got {timestamp_dt.strftime('%d')} {timestamp_dt.strftime('%Y')}"
    )
