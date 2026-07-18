SLACK_BOT_AGENT_PREFIX = "__slack_bot_agent__"
DEFAULT_AGENT_SLACK_CHANNEL_NAME = "DEFAULT_SLACK_CHANNEL"

CONNECTOR_VALIDATION_ERROR_MESSAGE_PREFIX = "ConnectorValidationError:"


# Sentinel value to distinguish between "not provided" and "explicitly set to None"
class UnsetType:
    def __repr__(self) -> str:
        return "<UNSET>"


UNSET = UnsetType()
