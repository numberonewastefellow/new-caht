from om.chat.llm_step import translate_history_to_llm_format
from om.chat.models import ChatMessageSimple
from om.configs.constants import MessageType
from om.llm.interfaces import LLM
from om.llm.models import ReasoningEffort
from om.llm.utils import llm_response_to_string
from om.prompts.chat_prompts import CHAT_NAMING_REMINDER
from om.prompts.chat_prompts import CHAT_NAMING_SYSTEM_PROMPT
from om.tracing.llm_utils import llm_generation_span
from om.tracing.llm_utils import record_llm_response
from om.utils.logger import setup_logger

logger = setup_logger()


def generate_chat_session_name(
    chat_history: list[ChatMessageSimple],
    llm: LLM,
) -> str:
    system_prompt = ChatMessageSimple(
        message=CHAT_NAMING_SYSTEM_PROMPT,
        token_count=100,
        message_type=MessageType.SYSTEM,
    )

    reminder_prompt = ChatMessageSimple(
        message=CHAT_NAMING_REMINDER,
        token_count=100,
        message_type=MessageType.USER_REMINDER,
    )

    complete_message_history = [system_prompt] + chat_history + [reminder_prompt]

    llm_facing_history = translate_history_to_llm_format(
        complete_message_history, llm.config
    )

    # Call LLM with Braintrust tracing
    with llm_generation_span(
        llm=llm, flow="chat_session_naming", input_messages=llm_facing_history
    ) as span_generation:
        response = llm.invoke(llm_facing_history, reasoning_effort=ReasoningEffort.OFF)
        record_llm_response(span_generation, response)
        new_name_raw = llm_response_to_string(response)

    return new_name_raw.strip().strip('"')
