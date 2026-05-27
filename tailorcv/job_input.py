"""Resolve a job ad into clean text from pasted text or a URL (Firecrawl v2)."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from .config import Config

MIN_DESCRIPTION_CHARS = 100
MIN_SCRAPE_CHARS = 200


class JobInput(BaseModel):
    description: str
    title: str = ""
    company: str = ""


def resolve(
    *,
    text: str | None = None,
    url: str | None = None,
    text_file: str | None = None,
    cfg: Config,
) -> JobInput:
    provided = [x for x in (text, url, text_file) if x]
    if len(provided) != 1:
        raise SystemExit("Provide exactly one of --text, --text-file, or --url.")

    if text_file:
        text = Path(text_file).read_text(encoding="utf-8")

    if text is not None:
        cleaned = text.strip()
        if len(cleaned) < MIN_DESCRIPTION_CHARS:
            raise SystemExit("Job description looks too short. Paste the full ad.")
        return JobInput(description=cleaned)

    # URL branch.
    if not cfg.firecrawl_api_key:
        raise SystemExit(
            "FIRECRAWL_API_KEY is not set. Set it in .env, or use --text/--text-file."
        )
    return _scrape(url, cfg)


def _meta_get(meta, key: str) -> str:
    """Read a metadata field whether `meta` is a dict or an attribute object."""
    if meta is None:
        return ""
    if isinstance(meta, dict):
        return (meta.get(key) or "").strip()
    return (getattr(meta, key, "") or "").strip()


def _scrape(url: str, cfg: Config) -> JobInput:
    from firecrawl import Firecrawl  # firecrawl-py >= 2.0

    client = Firecrawl(api_key=cfg.firecrawl_api_key)
    doc = client.scrape(url, formats=["markdown"])
    markdown = (getattr(doc, "markdown", "") or "").strip()
    meta = getattr(doc, "metadata", None)
    if len(markdown) < MIN_SCRAPE_CHARS:
        raise SystemExit(
            f"Extracted too little text from {url}. The site may block scraping — "
            "copy the job ad and use --text or --text-file instead."
        )
    return JobInput(
        description=markdown,
        title=_meta_get(meta, "title"),
        company=_meta_get(meta, "ogSiteName"),
    )
