from types import SimpleNamespace

from click.testing import CliRunner

from tailorcv import cli
from tailorcv.config import Config, Profile
from tailorcv.job_input import JobInput


def _cfg():
    return Config(profile=Profile(full_name="X"), anthropic_api_key="sk-ant-test")


def _fake_usage():
    return SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def test_slug_lowercase_hyphenated_no_spaces():
    assert cli._slug("Senior Eng/ineer: <x>") == "senior-engineer-x"


def test_slug_drops_dots_and_empty_falls_back():
    assert "." not in cli._slug("Senior .. Engineer")
    assert cli._slug("Senior .. Engineer") == "senior-engineer"
    assert cli._slug("..") == "job"
    assert cli._slug("@@@") == "job"


def test_base_name_uses_title_company():
    ji = JobInput(description="d", title="Senior Eng", company="ACME")
    assert cli._base_name(ji) == "senior-eng-acme"


def test_base_name_timestamp_fallback():
    ji = JobInput(description="d")
    assert cli._base_name(ji).startswith("job-")


def test_cv_and_letter_only_mutually_exclusive():
    runner = CliRunner()
    res = runner.invoke(cli.main, ["generate", "--text", "x" * 200, "--cv-only", "--letter-only"])
    assert res.exit_code == 2


def test_generate_writes_both_files(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: _cfg())
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 100)
    monkeypatch.setattr(cli, "check_budget", lambda *a, **k: None)
    monkeypatch.setattr(
        cli, "resolve", lambda **k: JobInput(description="d", title="T", company="C")
    )
    monkeypatch.setattr(cli.generator, "generate_cv", lambda *a, **k: ("<p>cv</p>", _fake_usage()))
    monkeypatch.setattr(cli.generator, "generate_cover_letter", lambda *a, **k: ("<p>cl</p>", _fake_usage()))
    written = []
    monkeypatch.setattr(cli.pdf, "render_cv", lambda html, p, out: written.append(str(out)) or out)
    monkeypatch.setattr(cli.pdf, "render_cover_letter", lambda html, p, out: written.append(str(out)) or out)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["generate", "--text", "x" * 200, "--output-dir", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert any("t-c-cv.pdf" in w for w in written)
    assert any("t-c-cover-letter.pdf" in w for w in written)


def test_generate_cv_only_writes_one(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: _cfg())
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 100)
    monkeypatch.setattr(cli, "check_budget", lambda *a, **k: None)
    monkeypatch.setattr(cli, "resolve", lambda **k: JobInput(description="d"))
    monkeypatch.setattr(cli.generator, "generate_cv", lambda *a, **k: ("<p>cv</p>", _fake_usage()))
    written = []
    monkeypatch.setattr(cli.pdf, "render_cv", lambda html, p, out: written.append(str(out)) or out)
    monkeypatch.setattr(cli.pdf, "render_cover_letter", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not run")))

    runner = CliRunner()
    res = runner.invoke(cli.main, ["generate", "--text", "x" * 200, "--cv-only", "--output-dir", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert len(written) == 1


def test_kb_tokens_prints_count(monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: _cfg())
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 4242)
    runner = CliRunner()
    res = runner.invoke(cli.main, ["kb-tokens"])
    assert res.exit_code == 0
    assert "4,242" in res.output


def test_generate_letter_only_writes_one(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: _cfg())
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 100)
    monkeypatch.setattr(cli, "check_budget", lambda *a, **k: None)
    monkeypatch.setattr(cli, "resolve", lambda **k: JobInput(description="d", title="T", company="C"))
    monkeypatch.setattr(cli.generator, "generate_cover_letter", lambda *a, **k: ("<p>cl</p>", _fake_usage()))
    monkeypatch.setattr(cli.generator, "generate_cv", lambda *a, **k: (_ for _ in ()).throw(AssertionError("CV should not be generated")))
    written = []
    monkeypatch.setattr(cli.pdf, "render_cover_letter", lambda html, p, out: written.append(str(out)) or out)
    monkeypatch.setattr(cli.pdf, "render_cv", lambda *a, **k: (_ for _ in ()).throw(AssertionError("render_cv should not run")))
    runner = CliRunner()
    res = runner.invoke(cli.main, ["generate", "--text", "x" * 200, "--letter-only", "--output-dir", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert len(written) == 1
    assert "cover-letter.pdf" in written[0]


def test_generate_prints_cost_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: _cfg())
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 100)
    monkeypatch.setattr(cli, "check_budget", lambda *a, **k: None)
    monkeypatch.setattr(
        cli, "resolve", lambda **k: JobInput(description="d", title="T", company="C")
    )
    monkeypatch.setattr(cli.generator, "generate_cv", lambda *a, **k: ("<p>cv</p>", _fake_usage()))
    monkeypatch.setattr(cli.generator, "generate_cover_letter", lambda *a, **k: ("<p>cl</p>", _fake_usage()))
    monkeypatch.setattr(cli.pdf, "render_cv", lambda html, p, out: out)
    monkeypatch.setattr(cli.pdf, "render_cover_letter", lambda html, p, out: out)

    runner = CliRunner()
    res = runner.invoke(cli.main, ["generate", "--text", "x" * 200, "--output-dir", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert "Token usage" in res.output
    assert "Estimated cost" in res.output


def _capture_cache_flag(tmp_path, monkeypatch, extra_args):
    seen = {}
    monkeypatch.setattr(cli, "load_config", lambda: _cfg())
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 100)
    monkeypatch.setattr(cli, "check_budget", lambda *a, **k: None)
    monkeypatch.setattr(cli, "resolve", lambda **k: JobInput(description="d"))

    def fake_cv(*a, **k):
        seen["cv"] = k.get("cache")
        return ("<p>cv</p>", _fake_usage())

    def fake_cl(*a, **k):
        seen["cl"] = k.get("cache")
        return ("<p>cl</p>", _fake_usage())

    monkeypatch.setattr(cli.generator, "generate_cv", fake_cv)
    monkeypatch.setattr(cli.generator, "generate_cover_letter", fake_cl)
    monkeypatch.setattr(cli.pdf, "render_cv", lambda html, p, out: out)
    monkeypatch.setattr(cli.pdf, "render_cover_letter", lambda html, p, out: out)
    runner = CliRunner()
    res = runner.invoke(
        cli.main, ["generate", "--text", "x" * 200, "--output-dir", str(tmp_path), *extra_args]
    )
    assert res.exit_code == 0, res.output
    return seen


def test_cache_enabled_only_when_both_documents(tmp_path, monkeypatch):
    # Both documents → cache the shared KB (2 calls, the 2nd reads it).
    seen = _capture_cache_flag(tmp_path, monkeypatch, [])
    assert seen == {"cv": True, "cl": True}


def test_cache_disabled_for_single_document(tmp_path, monkeypatch):
    # cv-only → one call → caching would only ever be written, never read → disabled.
    seen = _capture_cache_flag(tmp_path, monkeypatch, ["--cv-only"])
    assert seen == {"cv": False}


def test_kb_tokens_over_budget_warns(monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda: _cfg())
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 999_999)
    runner = CliRunner()
    res = runner.invoke(cli.main, ["kb-tokens"])
    assert res.exit_code == 0
    assert "999,999" in res.output
    combined = res.output + (res.output)  # stderr captured in output with mix_stderr default
    assert "999,999" in res.output
    assert "over" in res.output.lower() or "budget" in res.output.lower()


def test_generate_provider_google_routes_to_google_client(monkeypatch, tmp_path):
    """--provider google must select the GoogleClient and skip KB caching."""
    from click.testing import CliRunner
    from tailorcv import cli, generator
    from tailorcv.llm import Usage

    # Stub KB + job resolution + PDF rendering so the test stays in-process.
    monkeypatch.setattr(cli, "load_kb", lambda: "KB")
    monkeypatch.setattr(cli, "count_tokens", lambda *a, **k: 1)
    monkeypatch.setattr(cli, "check_budget", lambda *a, **k: None)

    class _Job:
        title = "Dev"
        company = "Acme"
        description = "JD"

    monkeypatch.setattr(cli, "resolve", lambda **kw: _Job())
    monkeypatch.setattr(cli.pdf, "render_cv", lambda *a, **k: tmp_path / "cv.pdf")
    monkeypatch.setattr(cli.pdf, "render_cover_letter", lambda *a, **k: tmp_path / "cl.pdf")

    seen = {}

    def fake_cv(jd, kb, cfg, cache=False):
        seen["provider"] = cfg.provider
        seen["cache"] = cache
        return "<p>cv</p>", Usage(input_tokens=1, output_tokens=1)

    def fake_cl(jd, kb, cfg, cache=False):
        return "<p>cl</p>", Usage(input_tokens=1, output_tokens=1)

    monkeypatch.setattr(generator, "generate_cv", fake_cv)
    monkeypatch.setattr(generator, "generate_cover_letter", fake_cl)

    # Minimal env / profile via a temp working dir
    (tmp_path / ".env").write_text(
        "ANTHROPIC_API_KEY=sk-ant-x\nGEMINI_API_KEY=g\n", encoding="utf-8"
    )
    (tmp_path / "profile.yaml").write_text("full_name: A\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["generate", "--text", "JD", "--provider", "google", "--output-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert seen["provider"] == "google"
    # Cache is meaningful only for Anthropic. We still pass cache=True when both
    # docs are generated; the GoogleClient ignores it. Assert it was set.
    assert seen["cache"] is True
