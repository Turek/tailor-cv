import pytest
from types import SimpleNamespace

from tailorcv.config import Config, Profile
from tailorcv.llm import Usage
from tailorcv.llm.anthropic_client import AnthropicClient


def _cfg():
    return Config(profile=Profile(full_name="X"), anthropic_api_key="sk-ant-test")


def _fake_resp_usage():
    return SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=2,
        cache_read_input_tokens=1,
    )


class _Block:
    def __init__(self, type, text):
        self.type = type
        self.text = text


def test_system_blocks_kb_prefix_then_role_prompt():
    blocks = AnthropicClient(_cfg())._system_blocks("SYS", "KB-CONTENT", cache=False)
    assert "KB-CONTENT" in blocks[0]["text"]
    assert "Candidate's Professional Knowledge Base" in blocks[0]["text"]
    assert blocks[1]["text"] == "SYS"
    assert "cache_control" not in blocks[0]


def test_system_blocks_cache_flag_sets_ephemeral():
    blocks = AnthropicClient(_cfg())._system_blocks("SYS", "KB", cache=True)
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_generate_joins_text_blocks_and_returns_usage(monkeypatch):
    class FakeResp:
        content = [_Block("text", "<h2>S</h2>"), _Block("text", "<p>x</p>")]
        usage = _fake_resp_usage()

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-sonnet-4-6"
            assert kwargs["system"][1]["text"] == "SYS"
            assert kwargs["messages"][0]["content"] == "USER"
            return FakeResp()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)
    text, usage = AnthropicClient(_cfg()).generate("SYS", "USER", "KB")
    assert text == "<h2>S</h2><p>x</p>"
    assert isinstance(usage, Usage)
    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
    assert usage.cache_write == 2
    assert usage.cache_read == 1


def test_generate_wraps_api_errors_as_systemexit(monkeypatch):
    import httpx
    import anthropic

    class FakeMessages:
        def create(self, **kwargs):
            raise anthropic.APIConnectionError(request=httpx.Request("POST", "http://x"))

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)
    with pytest.raises(SystemExit):
        AnthropicClient(_cfg()).generate("SYS", "USER", "KB")
