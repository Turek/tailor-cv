"""Prompt loading.

Real prompts live in gitignored files under ``prompts/`` (one ``<name>.md`` per
prompt). Committed ``prompts/<name>.md.example`` files demonstrate the format. The
two user-prompt templates contain a ``{{JOB_DESCRIPTION}}`` placeholder that is
substituted at call time.
"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
PLACEHOLDER = "{{JOB_DESCRIPTION}}"


def _load(name: str, prompts_dir: str | Path = PROMPTS_DIR) -> str:
    path = Path(prompts_dir) / f"{name}.md"
    if not path.exists():
        raise SystemExit(
            f"Prompt file {path} not found. Create your prompts from the examples, e.g.:\n"
            f"  cp prompts/{name}.md.example prompts/{name}.md\n"
            "then edit them. (Real prompts are gitignored.)"
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"Prompt file {path} is empty.")
    return text


def cv_system_prompt(prompts_dir: str | Path = PROMPTS_DIR) -> str:
    return _load("cv_system", prompts_dir)


def cover_letter_system_prompt(prompts_dir: str | Path = PROMPTS_DIR) -> str:
    return _load("cover_letter_system", prompts_dir)


def build_cv_user_prompt(job_description: str, prompts_dir: str | Path = PROMPTS_DIR) -> str:
    template = _load("cv_user", prompts_dir)
    if PLACEHOLDER not in template:
        raise SystemExit(
            f"prompts/cv_user.md is missing the {PLACEHOLDER!r} placeholder. "
            "Check it against prompts/cv_user.md.example."
        )
    return template.replace(PLACEHOLDER, job_description)


def build_letter_user_prompt(job_description: str, prompts_dir: str | Path = PROMPTS_DIR) -> str:
    template = _load("letter_user", prompts_dir)
    if PLACEHOLDER not in template:
        raise SystemExit(
            f"prompts/letter_user.md is missing the {PLACEHOLDER!r} placeholder. "
            "Check it against prompts/letter_user.md.example."
        )
    return template.replace(PLACEHOLDER, job_description)
