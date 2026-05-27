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


def test_safe_strips_unsafe_chars():
    assert cli._safe("Senior Eng/ineer: <x>") == "Senior Engineer x"


def test_safe_collapses_dot_sequences():
    assert ".." not in cli._safe("Senior .. Engineer")
    assert ".." not in cli._safe("..")
    assert cli._safe("@@@") == "unknown"


def test_base_name_uses_title_company():
    ji = JobInput(description="d", title="Senior Eng", company="ACME")
    assert cli._base_name(ji) == "Senior Eng - ACME"


def test_base_name_timestamp_fallback():
    ji = JobInput(description="d")
    assert cli._base_name(ji).startswith("Job - ")


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
    assert any("T - C - CV.pdf" in w for w in written)
    assert any("T - C - Cover Letter.pdf" in w for w in written)


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
    assert "Cover Letter.pdf" in written[0]


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
