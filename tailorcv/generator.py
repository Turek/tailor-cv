"""LLM generation: build cached prompts, call Anthropic, return inner HTML."""
from __future__ import annotations

import anthropic

from .config import Config
from . import prompts


def _system_blocks(system_prompt: str, kb: str) -> list[dict]:
    # The KB is the large, shared, CACHED PREFIX (block 0): byte-identical across the CV and
    # cover-letter calls, so the second call reads it from cache (~0.1x) instead of paying
    # full rate again — re-runs within the cache TTL benefit too. The small per-document
    # role instruction follows it (block 1, uncached, varies per document).
    return [
        {
            "type": "text",
            "text": (
                "## Candidate's Professional Knowledge Base\n\n"
                "The following is the candidate's complete professional knowledge "
                "base: rich narrative descriptions of their roles, projects, and "
                "achievements. Select and synthesise the most relevant evidence for "
                "the target role. Do not use information that is not present here.\n\n"
                f"{kb}"
            ),
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": system_prompt},
    ]


def _generate(system_prompt: str, user_prompt: str, kb: str, cfg: Config) -> tuple:
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_output_tokens,
            system=_system_blocks(system_prompt, kb),
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        raise SystemExit(f"Claude request failed: {e}") from e
    html = "".join(
        block.text for block in resp.content if block.type == "text"
    ).strip()
    if not html:
        raise SystemExit("Model returned empty content; no document generated.")
    return html, resp.usage


def generate_cv(job_description: str, kb: str, cfg: Config) -> tuple:
    return _generate(
        prompts.cv_system_prompt(),
        prompts.build_cv_user_prompt(job_description),
        kb,
        cfg,
    )


def generate_cover_letter(job_description: str, kb: str, cfg: Config) -> tuple:
    return _generate(
        prompts.cover_letter_system_prompt(),
        prompts.build_letter_user_prompt(job_description),
        kb,
        cfg,
    )
