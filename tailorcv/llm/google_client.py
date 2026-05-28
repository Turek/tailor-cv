"""Google Antigravity (Gemini) backend.

Async SDK bridged to a sync `LLMClient.generate` via `asyncio.run`. Streamed
tokens are collected into a single string before returning.
"""
from __future__ import annotations

import asyncio
import os

from ..config import Config
from .base import Usage


_KB_PREFIX = (
    "## Candidate's Professional Knowledge Base\n\n"
    "The following is the candidate's complete professional knowledge base: "
    "rich narrative descriptions of their roles, projects, and achievements. "
    "Select and synthesise the most relevant evidence for the target role. "
    "Do not use information that is not present here.\n\n"
)


class GoogleClient:
    """Sends prompts to Gemini via google-antigravity. `cache` is a no-op here."""

    MODEL = "gemini-2.5-flash"

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg

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
        # The SDK reads GEMINI_API_KEY from the environment; mirror our config
        # value so a user who set it only in .env still works.
        os.environ["GEMINI_API_KEY"] = self._cfg.gemini_api_key

        instructions = f"{_KB_PREFIX}{kb}\n\n{system_prompt}"
        try:
            return asyncio.run(self._run(instructions, user_prompt))
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001 — any SDK/network failure is a hard stop
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
            return text, Usage(
                input_tokens=getattr(u, "prompt_token_count", 0) or 0,
                output_tokens=getattr(u, "candidates_token_count", 0) or 0,
                cache_read=None,
                cache_write=None,
            )
