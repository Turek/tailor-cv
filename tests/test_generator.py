import pytest

from tailorcv import generator
from tailorcv.config import Config, Profile
from tailorcv.llm import Usage


def _cfg(provider="anthropic"):
    return Config(
        profile=Profile(full_name="X"),
        anthropic_api_key="sk-ant-test",
        gemini_api_key="g-key",
        provider=provider,
    )


class _FakeClient:
    def __init__(self, text="<p>ok</p>"):
        self._text = text
        self.calls: list[dict] = []

    def generate(self, system_prompt, user_prompt, kb, cache=False):
        self.calls.append(
            {"system": system_prompt, "user": user_prompt, "kb": kb, "cache": cache}
        )
        return self._text, Usage(input_tokens=10, output_tokens=5)


def test_strip_code_fence_removes_markdown_wrapper():
    assert (
        generator._strip_code_fence("```html\n<p>x</p>\n```") == "<p>x</p>"
    )
    assert generator._strip_code_fence("```\n<p>x</p>\n```") == "<p>x</p>"
    assert generator._strip_code_fence("```html\n<p>x</p>") == "<p>x</p>"
    assert generator._strip_code_fence("<p>x</p>") == "<p>x</p>"


def test_generate_cv_routes_through_client(monkeypatch):
    fake = _FakeClient("<h2>S</h2>")
    monkeypatch.setattr(generator, "get_client", lambda cfg: fake)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: f"U:{jd}")

    html, usage = generator.generate_cv("JOB", "KB", _cfg())

    assert html == "<h2>S</h2>"
    assert fake.calls[0]["system"] == "SYS"
    assert fake.calls[0]["user"] == "U:JOB"
    assert fake.calls[0]["kb"] == "KB"
    assert fake.calls[0]["cache"] is False
    assert usage.input_tokens == 10


def test_generate_cover_letter_uses_letter_prompts(monkeypatch):
    fake = _FakeClient("<p>letter</p>")
    monkeypatch.setattr(generator, "get_client", lambda cfg: fake)
    monkeypatch.setattr(generator.prompts, "cover_letter_system_prompt", lambda: "LSYS")
    monkeypatch.setattr(
        generator.prompts, "build_letter_user_prompt", lambda jd: f"L:{jd}"
    )

    html, _ = generator.generate_cover_letter("JD", "KB", _cfg(), cache=True)
    assert html == "<p>letter</p>"
    assert fake.calls[0]["system"] == "LSYS"
    assert fake.calls[0]["user"] == "L:JD"
    assert fake.calls[0]["cache"] is True


def test_generate_strips_fence_from_model_output(monkeypatch):
    fake = _FakeClient("```html\n<p>x</p>\n```")
    monkeypatch.setattr(generator, "get_client", lambda cfg: fake)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: "U")
    html, _ = generator.generate_cv("JOB", "KB", _cfg())
    assert html == "<p>x</p>"


def test_generate_empty_content_raises(monkeypatch):
    fake = _FakeClient("")
    monkeypatch.setattr(generator, "get_client", lambda cfg: fake)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: "U")
    with pytest.raises(SystemExit):
        generator.generate_cv("JOB", "KB", _cfg())
