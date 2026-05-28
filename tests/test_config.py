import pytest
from tailorcv.config import load_config, Config


def _write_profile(tmp_path):
    p = tmp_path / "profile.yaml"
    p.write_text(
        'full_name: "Tomasz King"\n'
        'email: "tomasz@turczynski.com"\n'
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
    assert cfg.profile.full_name == "Tomasz King"
    assert cfg.anthropic_api_key == "sk-ant-test"
    assert cfg.model == "claude-sonnet-4-6"
    assert cfg.token_budget == 70000
    assert cfg.profile.urls[0].title == "GitHub"


def test_missing_profile_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env = _write_env(tmp_path, "ANTHROPIC_API_KEY=sk-ant-test\n")
    with pytest.raises(SystemExit):
        load_config(profile_path=tmp_path / "does-not-exist.yaml", env_path=env)


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


def test_provider_defaults_to_anthropic(tmp_path, monkeypatch):
    from tailorcv.config import load_config

    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=sk-ant-x\n", encoding="utf-8")
    profile = tmp_path / "profile.yaml"
    profile.write_text("full_name: A\n", encoding="utf-8")
    monkeypatch.delenv("TAILORCV_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    cfg = load_config(profile_path=profile, env_path=env)
    assert cfg.provider == "anthropic"
    assert cfg.gemini_api_key == ""


def test_provider_env_override_to_google(tmp_path):
    from tailorcv.config import load_config

    env = tmp_path / ".env"
    env.write_text(
        "ANTHROPIC_API_KEY=sk-ant-x\n"
        "GEMINI_API_KEY=g-key\n"
        "TAILORCV_PROVIDER=google\n",
        encoding="utf-8",
    )
    profile = tmp_path / "profile.yaml"
    profile.write_text("full_name: A\n", encoding="utf-8")

    cfg = load_config(profile_path=profile, env_path=env)
    assert cfg.provider == "google"
    assert cfg.gemini_api_key == "g-key"


def test_unknown_provider_value_rejected(tmp_path):
    from tailorcv.config import load_config

    env = tmp_path / ".env"
    env.write_text(
        "ANTHROPIC_API_KEY=sk-ant-x\n"
        "TAILORCV_PROVIDER=openai\n",
        encoding="utf-8",
    )
    profile = tmp_path / "profile.yaml"
    profile.write_text("full_name: A\n", encoding="utf-8")

    import pytest
    with pytest.raises(SystemExit):
        load_config(profile_path=profile, env_path=env)
