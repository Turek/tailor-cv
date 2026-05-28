"""Configuration loading and validation."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


class ProfileUrl(BaseModel):
    title: str = ""
    uri: str


class Profile(BaseModel):
    full_name: str
    subtitle: str = ""
    header_note: str = ""
    email: str = ""
    phone: str = ""
    phone_secondary: str = ""
    urls: list[ProfileUrl] = []
    nationalities: list[str] = []
    cv_footer: str = ""


Provider = Literal["anthropic", "google"]


class Config(BaseModel):
    profile: Profile
    anthropic_api_key: str
    gemini_api_key: str = ""
    firecrawl_api_key: str = ""
    provider: Provider = "anthropic"
    # Retained for the Anthropic budget/tokenizer path; clients pin their own model.
    model: str = "claude-sonnet-4-6"
    token_budget: int = 70000
    max_output_tokens: int = 4096


def _int_env(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"{key} must be an integer, got: {raw!r}")


def _provider_env() -> Provider:
    raw = os.environ.get("TAILORCV_PROVIDER", "anthropic").strip().lower() or "anthropic"
    if raw not in ("anthropic", "google"):
        raise SystemExit(
            f"TAILORCV_PROVIDER must be 'anthropic' or 'google', got: {raw!r}"
        )
    return raw  # type: ignore[return-value]


def load_config(
    profile_path: str | Path = "profile.yaml",
    env_path: str | Path = ".env",
) -> Config:
    load_dotenv(env_path, override=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Add it to .env (see .env.example)."
        )
    try:
        with open(profile_path, "r", encoding="utf-8") as fh:
            profile_data = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        raise SystemExit(
            f"Profile file {profile_path!r} not found. Copy the example:\n"
            "  cp profile.example.yaml profile.yaml\nthen edit it."
        )
    return Config(
        profile=Profile(**profile_data),
        anthropic_api_key=api_key,
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        firecrawl_api_key=os.environ.get("FIRECRAWL_API_KEY", "").strip(),
        provider=_provider_env(),
        model=os.environ.get("TAILORCV_MODEL", "claude-sonnet-4-6").strip(),
        token_budget=_int_env("TAILORCV_TOKEN_BUDGET", 70000),
        max_output_tokens=_int_env("TAILORCV_MAX_OUTPUT_TOKENS", 4096),
    )
