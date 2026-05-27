import pytest
from tailorcv.config import load_config, Config


def _write_profile(tmp_path):
    p = tmp_path / "profile.yaml"
    p.write_text(
        'full_name: "Tomasz Turczynski"\n'
        'email: "tomasz.turczynski@gmail.com"\n'
        "urls:\n"
        '  - { title: "GitHub", uri: "https://github.com/x" }\n',
        encoding="utf-8",
    )
    return p


def _write_env(tmp_path, body):
    e = tmp_path / ".env"
    e.write_text(body, encoding="utf-8")
    return e


def test_missing_api_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile = _write_profile(tmp_path)
    env = _write_env(tmp_path, "ANTHROPIC_API_KEY=\n")
    with pytest.raises(SystemExit):
        load_config(profile_path=profile, env_path=env)


def test_valid_config_loads(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile = _write_profile(tmp_path)
    env = _write_env(tmp_path, "ANTHROPIC_API_KEY=sk-ant-test\n")
    cfg = load_config(profile_path=profile, env_path=env)
    assert isinstance(cfg, Config)
    assert cfg.profile.full_name == "Tomasz Turczynski"
    assert cfg.anthropic_api_key == "sk-ant-test"
    assert cfg.model == "claude-sonnet-4-6"
    assert cfg.token_budget == 70000
    assert cfg.profile.urls[0].title == "GitHub"


def test_bad_token_budget_raises_systemexit(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TAILORCV_TOKEN_BUDGET", raising=False)
    profile = _write_profile(tmp_path)
    env = _write_env(
        tmp_path,
        "ANTHROPIC_API_KEY=sk-ant-test\n"
        "TAILORCV_TOKEN_BUDGET=not-a-number\n",
    )
    with pytest.raises(SystemExit):
        load_config(profile_path=profile, env_path=env)


def test_env_overrides_apply(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TAILORCV_MODEL", raising=False)
    monkeypatch.delenv("TAILORCV_TOKEN_BUDGET", raising=False)
    profile = _write_profile(tmp_path)
    env = _write_env(
        tmp_path,
        "ANTHROPIC_API_KEY=sk-ant-test\n"
        "TAILORCV_MODEL=claude-opus-4-6\n"
        "TAILORCV_TOKEN_BUDGET=50000\n",
    )
    cfg = load_config(profile_path=profile, env_path=env)
    assert cfg.model == "claude-opus-4-6"
    assert cfg.token_budget == 50000
