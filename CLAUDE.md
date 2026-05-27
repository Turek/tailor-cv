# CLAUDE.md — guidance for Claude Code working in this repo

## What this is

`tailorcv`: a single-user Python CLI that turns a job ad (pasted text or URL) into an ATS-tailored CV
PDF + cover letter PDF using Claude. No RAG, no DB, no web server — the whole knowledge base goes into
one prompt-cached Claude call. Runs entirely in Docker.

## DOCKER-FIRST — non-negotiable

Every dependency lives inside the Docker image. The host has **only** Docker and `make`.

- **Never** run `pip`, `pytest`, or `python` directly on the host.
- Run everything through `make` targets or `docker compose run --rm app …`.
- Tests: `make test` (or `docker compose run --rm app pytest -q`).
- If a new Python or apt package is needed, **add it to `pyproject.toml` / `Dockerfile` and
  `make build` again** — do not `pip install` on the host.
- Source and tests are bind-mounted, so code edits take effect without rebuilding; only rebuild when
  dependencies change.

## Privacy boundary — do not leak

The repo is meant to be shared, but the user's prompts are their R&D and personal data is private.

- **Real prompts** live in `prompts/*.md` and are **gitignored**. When tuning prompts, edit the
  `prompts/*.md` files — NOT the `prompts/*.md.example` files (those are the committed generic
  placeholders). Never paste real prompt text into committed files, commit messages, README, or this file.
- **`docs/` is gitignored** in full (design docs, the implementation plan, source PDFs, and the
  verbatim prompts they contain). Don't commit anything under `docs/`.
- `.env`, `profile.yaml`, `knowledge_base/*.md` content, and `output/` are gitignored. Only the
  `.example` siblings and `knowledge_base/00-summary.md` placeholder are committed.
- Before any commit, sanity-check `git status`/`git diff --cached` for prompt text or personal data.

## Architecture (one responsibility per module)

| Module | Responsibility |
|---|---|
| `tailorcv/config.py` | Load `.env` (`load_dotenv(override=True)`) + `profile.yaml`; typed `Config`/`Profile`; hard-fail on missing `ANTHROPIC_API_KEY`. |
| `tailorcv/knowledge_base.py` | Concatenate `knowledge_base/*.md` in filename order; `count_tokens` via Anthropic; `check_budget` warning. |
| `tailorcv/job_input.py` | Resolve job ad from `--text`/`--text-file`/`--url`; URL path uses Firecrawl v2. |
| `tailorcv/prompts.py` | **Loader** for `prompts/*.md` (anchored to package root); substitutes `{{JOB_DESCRIPTION}}`. Holds NO prompt prose. |
| `tailorcv/generator.py` | Build 2-block cached `system`, call Anthropic, return inner HTML. |
| `tailorcv/pdf.py` | Assemble header/body/footer HTML from `Profile` + `assets/cv-pdf.css`; render via WeasyPrint. |
| `tailorcv/cli.py` | click group: `generate`, `kb-tokens`. |

## Verified external APIs (don't trust outdated signatures)

- **Anthropic**: `client.messages.create(model=, max_tokens=, system=[{"type":"text","text":...},{"type":"text","text":kb,"cache_control":{"type":"ephemeral"}}], messages=[{"role":"user","content":...}])`; read `block.text` where `block.type=="text"`. `client.messages.count_tokens(model=, messages=[...]).input_tokens`.
- **Firecrawl v2** (`firecrawl-py>=2.0`): `from firecrawl import Firecrawl`; `Firecrawl(api_key=...).scrape(url, formats=["markdown"])` → Document with `.markdown` / `.metadata`. (NOT the old v1 `FirecrawlApp.scrape_url(params=...)`.)
- **WeasyPrint**: `HTML(string=full_html).write_pdf(path)`; `@page` CSS sets A4 margins.

## Conventions

- **Model**: default `claude-sonnet-4-6` (a deliberate, locked choice — do not swap to Opus without being asked).
- **TDD**: write the failing test, run red via `make test`, implement, run green, commit.
- **Fail loud**: missing secrets / empty KB / missing prompt files / thin scrapes raise `SystemExit`
  with an actionable message. Don't fabricate; warn (not fail) on token-budget overrun.
- **Commits**: conventional-commit subjects. Do **not** add `Co-Authored-By` or "Generated with
  Claude" trailers. Do **not** run `git push`/`git pull`. Commit per build phase.

## Common commands

```bash
make build        # build image (after dependency changes)
make test         # full test suite in the container
make tokens       # KB token count vs budget (needs ANTHROPIC_API_KEY)
make generate URL="…"        # or TEXT="…"
make shell        # bash inside the container
docker compose run --rm app pytest tests/test_pdf.py -q   # single test module
```
