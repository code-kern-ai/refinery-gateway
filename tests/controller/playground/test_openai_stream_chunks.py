from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import Choice as CompletionChoice
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from controller.playground.reformulation import __get_openai_value_from

_SAFE_FILTER_RESULTS = {
    "hate": {"filtered": False, "severity": "safe"},
    "self_harm": {"filtered": False, "severity": "safe"},
    "sexual": {"filtered": False, "severity": "safe"},
    "violence": {"filtered": False, "severity": "safe"},
}


def _annotation_chunk(content_filter_results: dict) -> ChatCompletionChunk:
    # openai rejects delta=None during validation; Azure still emits it.
    return ChatCompletionChunk.model_construct(
        id="",
        choices=[
            Choice.model_construct(
                delta=None,
                finish_reason=None,
                index=0,
                content_filter_offsets={
                    "check_offset": 721637,
                    "start_offset": 721564,
                    "end_offset": 721637,
                },
                content_filter_results=content_filter_results,
            )
        ],
        created=0,
        model="",
        object="",
    )


def test_annotation_chunk_with_null_delta_returns_empty_string():
    chunk = _annotation_chunk(_SAFE_FILTER_RESULTS)
    assert __get_openai_value_from(chunk) == ""


def test_filtered_annotation_chunk_returns_empty_string():
    results = {
        **_SAFE_FILTER_RESULTS,
        "hate": {"filtered": True, "severity": "high"},
    }
    assert __get_openai_value_from(_annotation_chunk(results)) == ""


def test_content_chunk_returns_text():
    chunk = ChatCompletionChunk(
        id="chatcmpl-1",
        choices=[
            Choice(
                delta=ChoiceDelta(content="hello"),
                finish_reason=None,
                index=0,
            )
        ],
        created=1,
        model="gpt-4o-mini",
        object="chat.completion.chunk",
    )
    assert __get_openai_value_from(chunk) == "hello"


def test_chunk_with_null_content_returns_empty_string():
    chunk = ChatCompletionChunk(
        id="chatcmpl-1",
        choices=[
            Choice(
                delta=ChoiceDelta(content=None),
                finish_reason=None,
                index=0,
            )
        ],
        created=1,
        model="gpt-4o-mini",
        object="chat.completion.chunk",
    )
    assert __get_openai_value_from(chunk) == ""


def test_chat_completion_returns_message_content():
    completion = ChatCompletion(
        id="chatcmpl-1",
        choices=[
            CompletionChoice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(role="assistant", content="reformulated"),
            )
        ],
        created=1,
        model="gpt-4o-mini",
        object="chat.completion",
    )
    assert __get_openai_value_from(completion) == "reformulated"
