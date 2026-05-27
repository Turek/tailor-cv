"""Command-line interface."""
from __future__ import annotations

import contextlib
import datetime as dt
import re
from pathlib import Path

import click

from .config import load_config
from .knowledge_base import load_kb, count_tokens, check_budget
from .job_input import resolve
from . import generator, pdf, usage


@contextlib.contextmanager
def _step(label: str):
    """Print ``label… `` then ``Done`` (green) or ``Failed`` (red) inline."""
    click.echo(f"{label}… ", nl=False)
    try:
        yield
    except BaseException:
        click.secho("Failed", fg="red", bold=True)
        raise
    click.secho("Done", fg="green", bold=True)


def _slug(name: str) -> str:
    """Lowercase, hyphen-separated, filesystem-safe slug (no spaces, no dots)."""
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)   # drop everything except word chars, space, hyphen
    name = re.sub(r"[\s_]+", "-", name)    # spaces/underscores → hyphen
    name = re.sub(r"-{2,}", "-", name)     # collapse repeated hyphens
    return name.strip("-") or "job"


def _base_name(job) -> str:
    bits = [b for b in (job.title, job.company) if b]
    if bits:
        return _slug(" - ".join(bits))
    return "job-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")


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
        raise click.UsageError("--cv-only and --letter-only are mutually exclusive.")
    cfg = load_config()
    if model:
        cfg = cfg.model_copy(update={"model": model})

    with _step("Loading knowledge base"):
        kb = load_kb()
        token_count = count_tokens(kb, cfg.model, cfg.anthropic_api_key)
    warn = check_budget(token_count, cfg.token_budget)
    if warn:
        click.secho(warn, fg="yellow", err=True)

    with _step("Resolving job description"):
        job = resolve(text=text, url=url, text_file=text_file, cfg=cfg)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = _base_name(job)

    usages = []
    saved = []
    # Cache the KB only when both documents are generated (2 calls share it within the TTL,
    # so call 2 reads the cache). For a single-document run the cache would only be written
    # and never read, so skip it and pay the plain input rate.
    cache_kb = not cv_only and not letter_only

    if not letter_only:
        with _step("Generating CV"):
            cv_html, u = generator.generate_cv(job.description, kb, cfg, cache=cache_kb)
            usages.append(u)
            saved.append(pdf.render_cv(cv_html, cfg.profile, out_dir / f"{base}-cv.pdf"))

    if not cv_only:
        with _step("Generating cover letter"):
            cl_html, u = generator.generate_cover_letter(job.description, kb, cfg, cache=cache_kb)
            usages.append(u)
            saved.append(
                pdf.render_cover_letter(cl_html, cfg.profile, out_dir / f"{base}-cover-letter.pdf")
            )

    if usages:
        for line in usage.summarize(usages, cfg.model).splitlines():
            click.secho(line, bold=True)
    for p in saved:
        click.secho(f"Saved: {p}", fg="cyan")
