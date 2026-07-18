"""Integration tests for the unified assistant."""

from tests.integration.common_utils.managers.agent import AgentManager
from tests.integration.common_utils.test_models import DATestUser


def test_unified_assistant(reset: None, admin_user: DATestUser) -> None:  # noqa: ARG001
    """Combined test verifying unified assistant existence, tools, and starter messages."""
    # Fetch all agents
    agents = AgentManager.get_all(admin_user)

    # Find the unified assistant (ID 0)
    unified_assistant = None
    for agent in agents:
        if agent.id == 0:
            unified_assistant = agent
            break

    # Assert that there are no other assistants (agents) besides the unified assistant
    # (ID 0)
    assert (
        len(agents) == 1
    ), f"Expected only the unified assistant, found {len(agents)} agents"

    # Verify the unified assistant exists
    assert unified_assistant is not None, "Unified assistant (ID 0) not found"

    # Verify basic properties
    assert unified_assistant.name == "Assistant"
    assert (
        "search, web browsing, and image generation"
        in unified_assistant.description.lower()
    )
    assert unified_assistant.is_default_agent is True
    assert unified_assistant.is_visible is True
    assert unified_assistant.num_chunks == 25

    # Verify tools
    tools = unified_assistant.tools
    tool_names = [tool.name for tool in tools]
    assert "internal_search" in tool_names, "SearchTool not found in unified assistant"
    assert (
        "generate_image" in tool_names
    ), "ImageGenerationTool not found in unified assistant"
    assert "web_search" in tool_names, "WebSearchTool not found in unified assistant"

    # Verify no starter messages
    starter_messages = unified_assistant.starter_messages or []
    assert len(starter_messages) == 0, "Starter messages found"
