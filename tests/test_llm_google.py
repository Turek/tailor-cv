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
    def __init__(self, prompt=11, candidates=7, thoughts=0):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates
        self.thoughts_token_count = thoughts
        self.total_token_count = prompt + candidates + thoughts


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


def test_dev_errors_propagate_unwrapped(monkeypatch):
    """A NameError from our own code must NOT be disguised as 'Gemini request failed'."""

    class TyposquatAgent(_FakeAgent):
        async def chat(self, query):
            # Simulate a programmer error inside our wrapper, not an SDK failure.
            raise NameError("undefined_helper")

    _install_fake_sdk(monkeypatch, agent_cls=TyposquatAgent)
    from tailorcv.llm.google_client import GoogleClient

    with pytest.raises(NameError):
        GoogleClient(_cfg()).generate("S", "U", "KB")


def test_thinking_tokens_count_as_output(monkeypatch):
    """Gemini 2.5 Flash routes some output to thoughts_token_count — Google bills
    those as output, so the Usage record must include them in output_tokens."""

    class ThinkingAgent(_FakeAgent):
        def __init__(self, config):
            super().__init__(config)
            self.conversation = _FakeConversation(
                _FakeUsage(prompt=50, candidates=10, thoughts=200)
            )

    _install_fake_sdk(monkeypatch, agent_cls=ThinkingAgent)
    from tailorcv.llm.google_client import GoogleClient

    _, usage = GoogleClient(_cfg()).generate("S", "U", "KB")
    assert usage.input_tokens == 50
    assert usage.output_tokens == 210  # 10 candidates + 200 thoughts


def test_gemini_api_key_is_scoped_not_leaked(monkeypatch):
    """The SDK reads GEMINI_API_KEY from env; we must restore prior value on exit."""
    import os as _os

    monkeypatch.setenv("GEMINI_API_KEY", "previous-value")
    _install_fake_sdk(monkeypatch)
    from tailorcv.llm.google_client import GoogleClient

    GoogleClient(_cfg(gemini_key="call-scoped")).generate("S", "U", "KB")
    assert _os.environ["GEMINI_API_KEY"] == "previous-value"


def test_gemini_api_key_cleared_when_originally_unset(monkeypatch):
    """If GEMINI_API_KEY wasn't set before the call, it must be unset after."""
    import os as _os

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    _install_fake_sdk(monkeypatch)
    from tailorcv.llm.google_client import GoogleClient

    GoogleClient(_cfg(gemini_key="call-scoped")).generate("S", "U", "KB")
    assert "GEMINI_API_KEY" not in _os.environ


def test_client_exposes_model_attribute(monkeypatch):
    _install_fake_sdk(monkeypatch)
    from tailorcv.llm.google_client import GoogleClient

    assert GoogleClient(_cfg()).model == "gemini-2.5-flash"
