"""Command-line interface."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import click

from .config import load_config
from .knowledge_base import load_kb, count_tokens, check_budget
from .job_input import resolve
from . import generator, pdf


def _safe(name: str) -> str:
    name = re.sub(r"[^\w\s\-.]", "", name)
    return re.sub(r"\s+", " ", name).strip()


def _base_name(job) -> str:
    bits = [b for b in (job.title, job.company) if b]
    if bits:
        return _safe(" - ".join(bits))
    return "Job - " + dt.datetime.now().strftime("%Y%m%d-%H%M%S")


@click.group()
def main() -> None:
    """Tailor CV — generate ATS-tailored CVs and cover letters with Claude."""


@main.command("kb-tokens")
def kb_tokens() -> None:
    cfg = load_config()
    kb = load_kb()
    n = count_tokens(kb, cfg.model, cfg.anthropic_api_key)
    click.echo(f"Knowledge base: {n:,} tokens (budget {cfg.token_budget:,}).")
    warn = check_budget(n, cfg.token_budget)
    if warn:
        click.echo(warn, err=True)


@main.command("generate")
@click.option("--url")
@click.option("--text")
@click.option("--text-file", type=click.Path(exists=True))
@click.option("--cv-only", is_flag=True)
@click.option("--letter-only", is_flag=True)
@click.option("--output-dir", default="output")
@click.option("--model", default=None)
def generate(url, text, text_file, cv_only, letter_only, output_dir, model) -> None:
    if cv_only and letter_only:
        raise SystemExit("--cv-only and --letter-only are mutually exclusive.")
    cfg = load_config()
    if model:
        cfg.model = model

    click.echo("Loading knowledge base…")
    kb = load_kb()
    warn = check_budget(count_tokens(kb, cfg.model, cfg.anthropic_api_key), cfg.token_budget)
    if warn:
        click.echo(warn, err=True)

    click.echo("Resolving job description…")
    job = resolve(text=text, url=url, text_file=text_file, cfg=cfg)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = _base_name(job)

    if not letter_only:
        click.echo("Generating CV…")
        cv_html = generator.generate_cv(job.description, kb, cfg)
        p = pdf.render_cv(cv_html, cfg.profile, out_dir / f"{base} - CV.pdf")
        click.echo(f"  → {p}")

    if not cv_only:
        click.echo("Generating cover letter…")
        cl_html = generator.generate_cover_letter(job.description, kb, cfg)
        p = pdf.render_cover_letter(cl_html, cfg.profile, out_dir / f"{base} - Cover Letter.pdf")
        click.echo(f"  → {p}")

    click.echo("Done.")
