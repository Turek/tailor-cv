"""Anthropic Claude backend."""
from __future__ import annotations

import anthropic

from ..config import Config
from .base import Usage


class AnthropicClient:
    """Sends prompts to Claude. Honours the `cache` flag via ephemeral KB caching."""

    MODEL = "claude-sonnet-4-6"

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg

    @staticmethod
    def _system_blocks(system_prompt: str, kb: str, cache: bool) -> list[dict]:
        # The KB is block 0 (large shared prefix); the small per-document role
        # instruction is block 1. Caching only helps when the SAME KB is sent
        # twice within the 5-minute TTL — i.e. one run generating BOTH the CV
        # and the cover letter. For a single-document run cache=False and we
        # pay plain 1x.
        kb_block = {
            "type": "text",
            "text": (
                "## Candidate's Professional Knowledge Base\n\n"
                "The following is the candidate's complete professional knowledge "
                "base: rich narrative descriptions of their roles, projects, and "
                "achievements. Select and synthesise the most relevant evidence for "
                "the target role. Do not use information that is not present here.\n\n"
                f"{kb}"
            ),
        }
        if cache:
            kb_block["cache_control"] = {"type": "ephemeral"}
        return [kb_block, {"type": "text", "text": system_prompt}]

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        kb: str,
        cache: bool = False,
    ) -> tuple[str, Usage]:
        client = anthropic.Anthropic(api_key=self._cfg.anthropic_api_key)
        try:
            resp = client.messages.create(
                model=self.MODEL,
                max_tokens=self._cfg.max_output_tokens,
                system=self._system_blocks(system_prompt, kb, cache),
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as e:
            raise SystemExit(f"Claude request failed: {e}") from e
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        u = resp.usage
        return text, Usage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
            cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
        )
