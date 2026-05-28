"""LLM client abstraction: Anthropic and Google backends behind one interface."""
from __future__ import annotations

from .base import LLMClient, Usage

__all__ = ["LLMClient", "Usage", "get_client"]


def get_client(cfg):
    """Return an LLMClient for cfg.provider. Imported lazily to avoid pulling in
    the Google SDK when the user only runs the Anthropic path, and vice versa."""
    if cfg.provider == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient(cfg)
    if cfg.provider == "google":
        from .google_client import GoogleClient
        return GoogleClient(cfg)
    raise SystemExit(f"Unknown provider: {cfg.provider!r}")
