import sys
import types
import pytest

from tailorcv.config import Config, Profile
from tailorcv.llm import Usage


def _cfg(gemini_key="g-key"):
    return Config(
        profile=Profile(full_name="X"),
        anthropic_api_key="sk-ant-test",
        gemini_api_key=gemini_key,
        provider="google",
    )


class _FakeUsage:
    def __init__(self, prompt=11, candidates=7):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates
        self.total_token_count = prompt + candidates


class _FakeConversation:
    def __init__(self, usage):
        self.total_usage = usage


class _FakeResponse:
    def __init__(self, tokens):
        self._tokens = tokens

    def __aiter__(self):
        async def gen():
            for t in self._tokens:
                yield t
        return gen()


class _FakeAgent:
    last_config = None
    last_query = None

    def __init__(self, config):
        _FakeAgent.last_config = config
        self.conversation = _FakeConversation(_FakeUsage())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def chat(self, query):
        _FakeAgent.last_query = query
        return _FakeResponse(["<h2>", "Hello", "</h2>"])


class _FakeLocalAgentConfig:
    def __init__(self, *, model, system_instructions):
        self.model = model
        self.system_instructions = system_instructions


def _install_fake_sdk(monkeypatch, agent_cls=_FakeAgent):
    google_mod = types.ModuleType("google")
    antigravity_mod = types.ModuleType("google.antigravity")
    antigravity_mod.Agent = agent_cls
    antigravity_mod.LocalAgentConfig = _FakeLocalAgentConfig
    google_mod.antigravity = antigravity_mod
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.antigravity", antigravity_mod)


def test_missing_gemini_key_raises_systemexit(monkeypatch):
    _install_fake_sdk(monkeypatch)
    from tailorcv.llm.google_client import GoogleClient

    with pytest.raises(SystemExit) as exc:
        GoogleClient(_cfg(gemini_key="")).generate("SYS", "USER", "KB")
    assert "GEMINI_API_KEY" in str(exc.value)


def test_generate_concatenates_kb_and_system_into_instructions(monkeypatch):
    _install_fake_sdk(monkeypatch)
    from tailorcv.llm.google_client import GoogleClient

    text, usage = GoogleClient(_cfg()).generate("ROLE-SYS", "USER-Q", "KB-BODY")

    assert text == "<h2>Hello</h2>"
    assert isinstance(usage, Usage)
    assert usage.input_tokens == 11
    assert usage.output_tokens == 7
    assert usage.cache_read is None
    assert usage.cache_write is None
    # KB prefix and role prompt both present in system_instructions, in order.
    instr = _FakeAgent.last_config.system_instructions
    assert "KB-BODY" in instr
    assert "ROLE-SYS" in instr
    assert instr.index("KB-BODY") < instr.index("ROLE-SYS")
    assert _FakeAgent.last_config.model == "gemini-2.5-flash"
    assert _FakeAgent.last_query == "USER-Q"


def test_generate_cache_flag_is_ignored(monkeypatch):
    """Google has no equivalent of Anthropic prompt caching — cache=True is a no-op."""
    _install_fake_sdk(monkeypatch)
    from tailorcv.llm.google_client import GoogleClient

    text_a, _ = GoogleClient(_cfg()).generate("S", "U", "KB", cache=False)
    text_b, _ = GoogleClient(_cfg()).generate("S", "U", "KB", cache=True)
    assert text_a == text_b == "<h2>Hello</h2>"


def test_sdk_exception_wrapped_as_systemexit(monkeypatch):
    class BoomAgent(_FakeAgent):
        async def chat(self, query):
            raise RuntimeError("network down")

    _install_fake_sdk(monkeypatch, agent_cls=BoomAgent)
    from tailorcv.llm.google_client import GoogleClient

    with pytest.raises(SystemExit) as exc:
        GoogleClient(_cfg()).generate("S", "U", "KB")
    assert "Gemini request failed" in str(exc.value)
