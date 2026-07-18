"""Tests for chat_utils.py, specifically get_custom_agent_prompt."""

from unittest.mock import MagicMock

from om.chat.chat_utils import get_custom_agent_prompt
from om.configs.constants import DEFAULT_PERSONA_ID


class TestGetCustomAgentPrompt:
    """Tests for the get_custom_agent_prompt function."""

    def _create_mock_persona(
        self,
        persona_id: int = 1,
        system_prompt: str | None = None,
        replace_base_system_prompt: bool = False,
    ) -> MagicMock:
        """Create a mock Persona with the specified attributes."""
        persona = MagicMock()
        persona.id = persona_id
        persona.system_prompt = system_prompt
        persona.replace_base_system_prompt = replace_base_system_prompt
        return persona

    def _create_mock_chat_session(
        self,
        workspace: MagicMock | None = None,
    ) -> MagicMock:
        """Create a mock ChatSession with the specified attributes."""
        chat_session = MagicMock()
        chat_session.workspace = workspace
        return chat_session

    def _create_mock_workspace(
        self,
        instructions: str = "",
    ) -> MagicMock:
        """Create a mock Workspace with the specified attributes."""
        workspace = MagicMock()
        workspace.instructions = instructions
        return workspace

    def test_default_persona_no_workspace(self) -> None:
        """Test that default persona without a workspace returns None."""
        persona = self._create_mock_persona(persona_id=DEFAULT_PERSONA_ID)
        chat_session = self._create_mock_chat_session(workspace=None)

        result = get_custom_agent_prompt(persona, chat_session)

        assert result is None

    def test_default_persona_with_workspace_instructions(self) -> None:
        """Test that default persona in a workspace returns workspace instructions."""
        persona = self._create_mock_persona(persona_id=DEFAULT_PERSONA_ID)
        workspace = self._create_mock_workspace(instructions="Do X and Y")
        chat_session = self._create_mock_chat_session(workspace=workspace)

        result = get_custom_agent_prompt(persona, chat_session)

        assert result == "Do X and Y"

    def test_default_persona_with_empty_workspace_instructions(self) -> None:
        """Test that default persona in a workspace with empty instructions returns None."""
        persona = self._create_mock_persona(persona_id=DEFAULT_PERSONA_ID)
        workspace = self._create_mock_workspace(instructions="")
        chat_session = self._create_mock_chat_session(workspace=workspace)

        result = get_custom_agent_prompt(persona, chat_session)

        assert result is None

    def test_custom_persona_replace_base_prompt_true(self) -> None:
        """Test that custom persona with replace_base_system_prompt=True returns None."""
        persona = self._create_mock_persona(
            persona_id=1,
            system_prompt="Custom system prompt",
            replace_base_system_prompt=True,
        )
        chat_session = self._create_mock_chat_session(workspace=None)

        result = get_custom_agent_prompt(persona, chat_session)

        assert result is None

    def test_custom_persona_with_system_prompt(self) -> None:
        """Test that custom persona with system_prompt returns the system_prompt."""
        persona = self._create_mock_persona(
            persona_id=1,
            system_prompt="Custom system prompt",
            replace_base_system_prompt=False,
        )
        chat_session = self._create_mock_chat_session(workspace=None)

        result = get_custom_agent_prompt(persona, chat_session)

        assert result == "Custom system prompt"

    def test_custom_persona_empty_string_system_prompt(self) -> None:
        """Test that custom persona with empty string system_prompt returns None."""
        persona = self._create_mock_persona(
            persona_id=1,
            system_prompt="",
            replace_base_system_prompt=False,
        )
        chat_session = self._create_mock_chat_session(workspace=None)

        result = get_custom_agent_prompt(persona, chat_session)

        assert result is None

    def test_custom_persona_none_system_prompt(self) -> None:
        """Test that custom persona with None system_prompt returns None."""
        persona = self._create_mock_persona(
            persona_id=1,
            system_prompt=None,
            replace_base_system_prompt=False,
        )
        chat_session = self._create_mock_chat_session(workspace=None)

        result = get_custom_agent_prompt(persona, chat_session)

        assert result is None

    def test_custom_persona_in_workspace_uses_persona_prompt(self) -> None:
        """Test that custom persona in a workspace uses persona's system_prompt, not workspace instructions."""
        persona = self._create_mock_persona(
            persona_id=1,
            system_prompt="Custom system prompt",
            replace_base_system_prompt=False,
        )
        workspace = self._create_mock_workspace(instructions="Workspace instructions")
        chat_session = self._create_mock_chat_session(workspace=workspace)

        result = get_custom_agent_prompt(persona, chat_session)

        # Should use persona's system_prompt, NOT workspace instructions
        assert result == "Custom system prompt"

    def test_custom_persona_replace_base_in_workspace(self) -> None:
        """Test that custom persona with replace_base_system_prompt=True in a workspace still returns None."""
        persona = self._create_mock_persona(
            persona_id=1,
            system_prompt="Custom system prompt",
            replace_base_system_prompt=True,
        )
        workspace = self._create_mock_workspace(instructions="Workspace instructions")
        chat_session = self._create_mock_chat_session(workspace=workspace)

        result = get_custom_agent_prompt(persona, chat_session)

        # Should return None because replace_base_system_prompt=True
        assert result is None
