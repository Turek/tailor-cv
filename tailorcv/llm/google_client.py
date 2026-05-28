"""Google Antigravity (Gemini) backend.

Async SDK bridged to a sync `LLMClient.generate` via `asyncio.run`. Streamed
tokens are collected into a single string before returning.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Iterator

from ..config import Config
from .base import Usage


_KB_PREFIX = (
    "## Candidate's Professional Knowledge Base\n\n"
    "The following is the candidate's complete professional knowledge base: "
    "rich narrative descriptions of their roles, projects, and achievements. "
    "Select and synthesise the most relevant evidence for the target role. "
    "Do not use information that is not present here.\n\n"
)


# Dev-time bugs we never want to disguise as "Gemini request failed".
# These ALL indicate our own broken code, not an SDK/network problem, so let
# them propagate with their real traceback.
_DEV_ERRORS = (NameError, AttributeError, ImportError, SyntaxError, IndentationError)


@contextlib.contextmanager
def _scoped_env(name: str, value: str) -> Iterator[None]:
    """Temporarily set an env var and restore the prior value on exit.

    The antigravity SDK reads ``GEMINI_API_KEY`` from the environment; writing
    it globally would leak across calls in any long-lived process (e.g. an MCP
    server) and pollute tests run in the same interpreter. Scoping it to the
    one call keeps process state clean.
    """
    prev = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = prev


class GoogleClient:
    """Sends prompts to Gemini via google-antigravity. `cache` is a no-op here."""

    MODEL = "gemini-2.5-flash"

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self.model = self.MODEL  # satisfies LLMClient.model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        kb: str,
        cache: bool = False,
    ) -> tuple[str, Usage]:
        if not self._cfg.gemini_api_key:
            raise SystemExit(
                "GEMINI_API_KEY is not set. Add it to .env (see .env.example)."
            )

        instructions = f"{_KB_PREFIX}{kb}\n\n{system_prompt}"
        try:
            with _scoped_env("GEMINI_API_KEY", self._cfg.gemini_api_key):
                return asyncio.run(self._run(instructions, user_prompt))
        except SystemExit:
            raise
        except _DEV_ERRORS:
            # Surface our own bugs with their real traceback.
            raise
        except Exception as e:  # noqa: BLE001 — wrap genuine SDK/network failures
            raise SystemExit(f"Gemini request failed: {e}") from e

    async def _run(self, instructions: str, user_prompt: str) -> tuple[str, Usage]:
        # Imported lazily so the Anthropic-only path doesn't require the SDK.
        from google.antigravity import Agent, LocalAgentConfig

        config = LocalAgentConfig(model=self.MODEL, system_instructions=instructions)
        async with Agent(config) as agent:
            response = await agent.chat(user_prompt)
            chunks: list[str] = []
            async for token in response:
                chunks.append(token)
            text = "".join(chunks).strip()
            u = agent.conversation.total_usage
            # Gemini 2.5 Flash defaults to thinking mode; the SDK splits output
            # between candidates_token_count and thoughts_token_count. Google
            # bills both as output tokens, so we sum them — otherwise a reasoning-
            # heavy answer reports as ~$0 in the cost summary.
            candidates = getattr(u, "candidates_token_count", 0) or 0
            thoughts = getattr(u, "thoughts_token_count", 0) or 0
            return text, Usage(
                input_tokens=getattr(u, "prompt_token_count", 0) or 0,
                output_tokens=candidates + thoughts,
                cache_read=None,
                cache_write=None,
            )
