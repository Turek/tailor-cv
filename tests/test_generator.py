import pytest
from types import SimpleNamespace
from tailorcv import generator
from tailorcv.config import Config, Profile


def _cfg():
    return Config(profile=Profile(full_name="X"), anthropic_api_key="sk-ant-test")


def _fake_usage():
    return SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def test_system_blocks_kb_is_prefix_and_role_prompt_follows():
    # KB is block 0 (the shared prefix); the role system prompt follows as block 1.
    blocks = generator._system_blocks("SYS", "KB-CONTENT-HERE", cache=False)
    assert "KB-CONTENT-HERE" in blocks[0]["text"]
    assert "Candidate's Professional Knowledge Base" in blocks[0]["text"]
    assert blocks[1]["text"] == "SYS"
    assert "cache_control" not in blocks[1]


def test_system_blocks_cache_flag_controls_cache_control():
    # cache=True marks the KB block ephemeral; cache=False leaves it uncached so a
    # single-document run never pays the cache-write premium for an unread cache.
    assert generator._system_blocks("SYS", "KB", cache=True)[0]["cache_control"] == {
        "type": "ephemeral"
    }
    assert "cache_control" not in generator._system_blocks("SYS", "KB", cache=False)[0]


def test_generate_cv_joins_text_blocks(monkeypatch):
    class Block:
        def __init__(self, type, text):
            self.type = type
            self.text = text

    class FakeResp:
        content = [Block("text", "<h2>Professional Summary</h2>"), Block("text", "<p>ok</p>")]
        usage = _fake_usage()

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-sonnet-4-6"
            assert isinstance(kwargs["system"], list)
            assert "KB" in kwargs["system"][0]["text"]
            # default cache=False → no cache_control on a single-document call
            assert "cache_control" not in kwargs["system"][0]
            assert kwargs["system"][1]["text"] == "SYS"
            assert kwargs["messages"][0]["role"] == "user"
            assert kwargs["messages"][0]["content"] == "USER:JOB"
            return FakeResp()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: f"USER:{jd}")
    html, u = generator.generate_cv("JOB", "KB", _cfg())
    assert html == "<h2>Professional Summary</h2><p>ok</p>"
    assert u.input_tokens == 10


def test_generate_cover_letter_uses_letter_prompts(monkeypatch):
    class Block:
        def __init__(self, type, text):
            self.type = type
            self.text = text

    class FakeResp:
        content = [Block("text", "<p>letter</p>")]
        usage = _fake_usage()

    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured["role_prompt"] = kwargs["system"][1]["text"]
            captured["user"] = kwargs["messages"][0]["content"]
            return FakeResp()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)
    monkeypatch.setattr(generator.prompts, "cover_letter_system_prompt", lambda: "LSYS")
    monkeypatch.setattr(generator.prompts, "build_letter_user_prompt", lambda jd: f"LUSER:{jd}")
    out, u = generator.generate_cover_letter("JD", "KB", _cfg())
    assert out == "<p>letter</p>"
    assert captured["role_prompt"] == "LSYS"
    assert captured["user"] == "LUSER:JD"
    assert u.input_tokens == 10


def test_generate_empty_content_raises(monkeypatch):
    class FakeResp:
        content = []
        usage = _fake_usage()

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResp()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: "U")
    with pytest.raises(SystemExit):
        generator.generate_cv("JOB", "KB", _cfg())


def test_strip_code_fence_removes_markdown_wrapper():
    fenced = "```html\n<h2>Professional Summary</h2><p>ok</p>\n```"
    assert generator._strip_code_fence(fenced) == "<h2>Professional Summary</h2><p>ok</p>"
    # bare ``` opener, and no-closer (truncated) cases
    assert generator._strip_code_fence("```\n<p>x</p>\n```") == "<p>x</p>"
    assert generator._strip_code_fence("```html\n<p>x</p>") == "<p>x</p>"
    # unfenced content is returned unchanged
    assert generator._strip_code_fence("<p>x</p>") == "<p>x</p>"


def test_generate_strips_fence_from_model_output(monkeypatch):
    class Block:
        type = "text"
        text = "```html\n<h2>Professional Summary</h2><p>ok</p>\n```"

    class FakeResp:
        content = [Block()]
        usage = _fake_usage()

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResp()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: "U")
    html, _ = generator.generate_cv("JOB", "KB", _cfg())
    assert "```" not in html
    assert html == "<h2>Professional Summary</h2><p>ok</p>"


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
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: "U")
    with pytest.raises(SystemExit):
        generator.generate_cv("JOB", "KB", _cfg())
