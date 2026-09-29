import json
from pathlib import Path

_TEMPLATE = (
    Path(__file__).resolve().parents[3]
    / "controller"
    / "attribute"
    / "llm_response_tmpl.py"
)


def _load_llm_kwargs(model: str, stop_sequences: list, is_o_series: bool) -> dict:
    source = _TEMPLATE.read_text()
    replacements = {
        "@@STOP_SEQUENCE@@": json.dumps(stop_sequences),
        "@@TEMPERATURE@@": "0",
        "@@MAX_TOKENS@@": "1024",
        "@@TOP_P@@": "1",
        "@@FREQUENCY_PENALTY@@": "0",
        "@@PRESENCE_PENALTY@@": "0",
        "@@MODEL@@": model,
        '"@@IS_O_SERIES@@"': str(is_o_series),
    }
    for key, value in replacements.items():
        source = source.replace(key, value)
    namespace: dict = {}
    exec(source, namespace)
    return namespace["LLM_KWARGS_A2VYBG"]


def test_gpt_5_6_sol_omits_stop_even_when_sequences_are_set():
    kwargs = _load_llm_kwargs("gpt-5.6-sol", ["END"], is_o_series=False)
    assert "stop" not in kwargs


def test_o_series_omits_stop():
    kwargs = _load_llm_kwargs("custom-azure-deployment", ["END"], is_o_series=True)
    assert "stop" not in kwargs
    assert "temperature" not in kwargs
    assert kwargs["max_completion_tokens"] == 1024


def test_empty_stop_sequences_are_omitted():
    kwargs = _load_llm_kwargs("gpt-4o", [], is_o_series=False)
    assert "stop" not in kwargs


def test_gpt_4o_keeps_configured_stop_sequences():
    kwargs = _load_llm_kwargs("gpt-4o", ["END"], is_o_series=False)
    assert kwargs["stop"] == ["END"]


def test_gpt_5_chat_keeps_configured_stop_sequences():
    kwargs = _load_llm_kwargs("gpt-5-chat-latest", ["END"], is_o_series=False)
    assert kwargs["stop"] == ["END"]
