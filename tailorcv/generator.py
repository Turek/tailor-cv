"""LLM generation: build cached prompts, call Anthropic, return inner HTML."""
from __future__ import annotations

import anthropic

from .config import Config
from . import prompts


def _strip_code_fence(text: str) -> str:
    """Remove a wrapping markdown code fence (```/```html … ```) if the model added one.

    The model is told to emit raw inner HTML, but occasionally wraps the whole response in
    a fenced code block, which would otherwise render as literal backticks in the PDF.
    """
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    lines = lines[1:]  # drop the opening ``` / ```html line
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]  # drop the closing fence if present
    return "\n".join(lines).strip()


def _system_blocks(system_prompt: str, kb: str, cache: bool) -> list[dict]:
    # The KB is block 0 (the large, shared prefix); the small per-document role instruction
    # follows it (block 1). Caching only helps when the SAME KB is sent twice within the TTL
    # — i.e. a single run generating BOTH the CV and the cover letter (call 1 writes ~1.25x,
    # call 2 reads ~0.1x → cheaper than 2x uncached). For a single-document run the cache
    # would only ever be written (1.25x) and never read, so `cache` is False there and we
    # pay the plain 1x rate — no wasted cache-write premium.
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


def _generate(
    system_prompt: str, user_prompt: str, kb: str, cfg: Config, cache: bool = False
) -> tuple:
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_output_tokens,
            system=_system_blocks(system_prompt, kb, cache),
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        raise SystemExit(f"Claude request failed: {e}") from e
    html = "".join(
        block.text for block in resp.content if block.type == "text"
    ).strip()
    html = _strip_code_fence(html)
    if not html:
        raise SystemExit("Model returned empty content; no document generated.")
    return html, resp.usage


def generate_cv(job_description: str, kb: str, cfg: Config, cache: bool = False) -> tuple:
    return _generate(
        prompts.cv_system_prompt(),
        prompts.build_cv_user_prompt(job_description),
        kb,
        cfg,
        cache,
    )


def generate_cover_letter(
    job_description: str, kb: str, cfg: Config, cache: bool = False
) -> tuple:
    return _generate(
        prompts.cover_letter_system_prompt(),
        prompts.build_letter_user_prompt(job_description),
        kb,
        cfg,
        cache,
    )
