"""Assemble HTML documents and render them to PDF with WeasyPrint."""
from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import urlparse

from weasyprint import HTML, default_url_fetcher

from .config import Profile

_CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "cv-pdf.css"


def _no_external_fetch(url: str):
    """Block external resource fetches during PDF rendering.

    The document inlines its own CSS and needs no external resources, so refusing
    every non-``data:`` URL neutralises anything an untrusted job ad could induce the
    model to emit (e.g. ``<img src="http://…">``, CSS ``@import`` / ``url()``,
    ``file://`` reads). Only ``data:`` URIs are allowed through.
    """
    if url.startswith("data:"):
        return default_url_fetcher(url)
    raise ValueError(f"Blocked external resource in CV rendering: {url}")


def _css() -> str:
    if not _CSS_PATH.exists():
        raise SystemExit(f"CSS asset not found: {_CSS_PATH}")
    return _CSS_PATH.read_text(encoding="utf-8")


def _cv_header(p: Profile) -> str:
    contact = []
    if p.email:
        contact.append(f'<a href="mailto:{escape(p.email)}">{escape(p.email)}</a>')
    if p.phone:
        contact.append(f'<a href="tel:{escape(p.phone)}">{escape(p.phone)}</a>')
    if p.phone_secondary:
        contact.append(f'<a href="tel:{escape(p.phone_secondary)}">{escape(p.phone_secondary)}</a>')

    urls = [f'<a href="{escape(u.uri)}">{escape(u.uri)}</a>' for u in p.urls if u.uri]
    nats = [escape(n) for n in p.nationalities if n]

    h = ['<div class="cv-header">', '<div class="cv-top-row">', '<div class="cv-top-left">']
    h.append(f'<h1 class="cv-name">{escape(p.full_name)}</h1>')
    if p.subtitle:
        h.append(f'<div class="cv-subtitle">{escape(p.subtitle)}</div>')
    if p.header_note:
        h.append(f'<div class="cv-header-note">{escape(p.header_note)}</div>')
    h.append("</div>")
    if urls:
        h.append('<div class="cv-top-right">' + "<br>".join(urls) + "</div>")
    h.append("</div>")
    h.append('<div class="cv-accent-bar"></div>')
    if contact:
        h.append('<div class="cv-contact-line">Contact: ' + " | ".join(contact) + "</div>")
    if nats:
        h.append('<div class="cv-nationalities">Nationality: ' + ", ".join(nats) + "</div>")
    h.append("</div>")
    return "".join(h)


def _letter_header(p: Profile) -> str:
    parts = []
    if p.email:
        parts.append(f'<a href="mailto:{escape(p.email)}">{escape(p.email)}</a>')
    if p.phone:
        parts.append(f'<a href="tel:{escape(p.phone)}">{escape(p.phone)}</a>')
    if p.phone_secondary:
        parts.append(f'<a href="tel:{escape(p.phone_secondary)}">{escape(p.phone_secondary)}</a>')
    if p.header_note:
        parts.append(escape(p.header_note))
    for u in p.urls:
        if u.uri:
            host = urlparse(u.uri).netloc or u.uri.split("//")[-1].split("/")[0]
            display = u.title or host.removeprefix("www.")
            parts.append(escape(display))
    h = [
        '<div class="letter-header">',
        f'<h1 class="cv-name">{escape(p.full_name)}</h1>',
        '<div class="cv-accent-bar"></div>',
    ]
    if parts:
        h.append('<div class="letter-contact">' + " | ".join(parts) + "</div>")
    h.append("</div>")
    return "".join(h)


def _footer(p: Profile) -> str:
    return f'<div class="cv-footer">{p.cv_footer}</div>' if p.cv_footer.strip() else ""


def build_cv_document(body_html: str, p: Profile) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>{_css()}</style></head>
<body class="cv-document">{_cv_header(p)}<div class="cv-body">{body_html}</div>{_footer(p)}</body></html>"""


def build_letter_document(body_html: str, p: Profile) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>{_css()}</style></head>
<body class="cover-letter-document">{_letter_header(p)}<div class="letter-body">{body_html}</div></body></html>"""


def render_cv(body_html: str, p: Profile, out_path) -> Path:
    out = Path(out_path)
    HTML(
        string=build_cv_document(body_html, p), url_fetcher=_no_external_fetch
    ).write_pdf(str(out))
    return out


def render_cover_letter(body_html: str, p: Profile, out_path) -> Path:
    out = Path(out_path)
    HTML(
        string=build_letter_document(body_html, p), url_fetcher=_no_external_fetch
    ).write_pdf(str(out))
    return out
