"""LLM generation: build cached prompts, call Anthropic, return inner HTML."""
from __future__ import annotations

import anthropic

from .config import Config
from . import prompts


def _system_blocks(system_prompt: str, kb: str) -> list[dict]:
    # cache_control on the KB block (the last/largest block of the system prefix)
    # makes the KB billed at the cache-read rate on the cover-letter call after the CV call.
    return [
        {"type": "text", "text": system_prompt},
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
    ]


def _generate(system_prompt: str, user_prompt: str, kb: str, cfg: Config) -> str:
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    resp = client.messages.create(
        model=cfg.model,
        max_tokens=cfg.max_output_tokens,
        system=_system_blocks(system_prompt, kb),
        messages=[{"role": "user", "content": user_prompt}],
    )
    html = "".join(
        block.text for block in resp.content if block.type == "text"
    ).strip()
    if not html:
        raise SystemExit("Model returned empty content; no document generated.")
    return html


def generate_cv(job_description: str, kb: str, cfg: Config) -> str:
    return _generate(
        prompts.cv_system_prompt(),
        prompts.build_cv_user_prompt(job_description),
        kb,
        cfg,
    )


def generate_cover_letter(job_description: str, kb: str, cfg: Config) -> str:
    return _generate(
        prompts.cover_letter_system_prompt(),
        prompts.build_letter_user_prompt(job_description),
        kb,
        cfg,
    )
