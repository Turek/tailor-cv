"""LLM dispatch: build prompts, call the configured backend, return inner HTML."""
from __future__ import annotations

from .config import Config
from .llm import LLMClient, Usage, get_client
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


def _generate(
    system_prompt: str,
    user_prompt: str,
    kb: str,
    cfg: Config,
    cache: bool,
) -> tuple[str, Usage]:
    client: LLMClient = get_client(cfg)
    text, usage = client.generate(system_prompt, user_prompt, kb, cache=cache)
    html = _strip_code_fence(text)
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
