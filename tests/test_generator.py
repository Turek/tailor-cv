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


def test_markdown_bold_to_html_converts_pairs():
    f = generator._markdown_bold_to_html
    assert f("Built a **scalable** system.") == "Built a <strong>scalable</strong> system."
    # Multiple pairs in one string.
    assert (
        f("**Sedno**, a **multilingual** app")
        == "<strong>Sedno</strong>, a <strong>multilingual</strong> app"
    )
    # Phrase with spaces and punctuation inside.
    assert f("**5–10 seconds**") == "<strong>5–10 seconds</strong>"


def test_markdown_bold_to_html_leaves_html_strong_alone():
    f = generator._markdown_bold_to_html
    assert f("Already <strong>bold</strong>.") == "Already <strong>bold</strong>."


def test_markdown_bold_to_html_ignores_unbalanced_markers():
    f = generator._markdown_bold_to_html
    # Single trailing `**` with no opening pair — leave unchanged.
    assert f("price: 5**") == "price: 5**"
    # Empty `**` pair — leave unchanged (don't emit empty <strong/>).
    assert f("a ** ** b") == "a ** ** b"


def test_markdown_bold_to_html_does_not_cross_newlines():
    f = generator._markdown_bold_to_html
    # A stray `**` should not greedily span paragraphs.
    src = "intro **foo\n\nlater paragraph** more"
    assert f(src) == src


def test_generate_converts_markdown_bold_in_model_output(monkeypatch):
    fake = _FakeClient("<p>Founded **Sedno**, a **scalable** system.</p>")
    monkeypatch.setattr(generator, "get_client", lambda cfg: fake)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: "U")
    html, _ = generator.generate_cv("JOB", "KB", _cfg())
    assert "**" not in html
    assert "<strong>Sedno</strong>" in html
    assert "<strong>scalable</strong>" in html


def test_generate_empty_content_raises(monkeypatch):
    fake = _FakeClient("")
    monkeypatch.setattr(generator, "get_client", lambda cfg: fake)
    monkeypatch.setattr(generator.prompts, "cv_system_prompt", lambda: "SYS")
    monkeypatch.setattr(generator.prompts, "build_cv_user_prompt", lambda jd: "U")
    with pytest.raises(SystemExit):
        generator.generate_cv("JOB", "KB", _cfg())
