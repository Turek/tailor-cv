"""LLM dispatch: build prompts, call the configured backend, return inner HTML."""
from __future__ import annotations

import re

from .config import Config
from .llm import LLMClient, Usage, get_client
from . import prompts


# Match a `**…**` pair on a single line with non-empty, non-asterisk content.
# Non-greedy, no newline inside, and the inner text must contain at least one
# non-whitespace char — so stray `**` or empty pairs are left alone.
_MD_BOLD = re.compile(r"\*\*(?=\S)([^*\n]+?)(?<=\S)\*\*")


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


def _markdown_bold_to_html(text: str) -> str:
    """Rewrite ``**text**`` markdown bold as ``<strong>text</strong>``.

    The model is told to emit raw HTML, but Gemini in particular sometimes
    slips into markdown for emphasis — leaving literal ``**foo**`` in the PDF.
    Converting after the model returns is bulletproof regardless of which
    backend misbehaves; HTML ``<strong>`` already in the output is untouched
    because the regex requires literal ``**`` markers.
    """
    return _MD_BOLD.sub(r"<strong>\1</strong>", text)


def _generate(
    system_prompt: str,
    user_prompt: str,
    kb: str,
    cfg: Config,
    cache: bool,
) -> tuple[str, Usage]:
    client: LLMClient = get_client(cfg)
    text, usage = client.generate(system_prompt, user_prompt, kb, cache=cache)
    html = _markdown_bold_to_html(_strip_code_fence(text))
    if not html:
        raise SystemExit("Model returned empty content; no document generated.")
    return html, usage


def generate_cv(
    job_description: str, kb: str, cfg: Config, cache: bool = False
) -> tuple[str, Usage]:
    return _generate(
        prompts.cv_system_prompt(),
        prompts.build_cv_user_prompt(job_description),
        kb,
        cfg,
        cache,
    )


def generate_cover_letter(
    job_description: str, kb: str, cfg: Config, cache: bool = False
) -> tuple[str, Usage]:
    return _generate(
        prompts.cover_letter_system_prompt(),
        prompts.build_letter_user_prompt(job_description),
        kb,
        cfg,
        cache,
    )
