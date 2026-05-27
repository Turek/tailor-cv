# Tailor CV (`tailorcv`)

A single-user command-line tool that turns a job advertisement (pasted text **or** a URL) into an
**ATS-tailored CV PDF** and a **cover letter PDF** using Claude. It feeds your entire narrative
professional history to the model in one prompt-cached call and lets the model select and synthesise
the evidence — no RAG, no database, no web server.

This is a from-scratch rewrite of an earlier over-engineered Drupal application; the Drupal stack is
**superseded** by this tool.

## Requirements

Only **Docker** and **make** on the host. Everything else (Python, WeasyPrint and its native
libraries, the Anthropic and Firecrawl SDKs, …) lives inside the Docker image — your host stays clean.

## First-run setup

```bash
# 1. Secrets
cp .env.example .env
#    edit .env → set ANTHROPIC_API_KEY (required)
#    and FIRECRAWL_API_KEY (only if you use --url)

# 2. Your contact/header/footer data
cp profile.example.yaml profile.yaml
#    edit profile.yaml

# 3. Your prompts (these are gitignored — they're yours to tune)
for f in prompts/*.md.example; do cp "$f" "${f%.example}"; done
#    edit prompts/cv_system.md, prompts/cover_letter_system.md,
#    prompts/cv_user.md, prompts/letter_user.md
#    (the two *_user.md files must keep the {{JOB_DESCRIPTION}} placeholder)

# 4. Your narrative history — one .md per role/project/theme, rich PROSE (not bullets)
#    in knowledge_base/ (see knowledge_base/00-summary.md for the expected style)

# 5. Build the image
make build

# 6. Check your knowledge base fits the token budget
make tokens

# 7. Generate
make generate URL="https://…a-job-ad…"
#    or
make generate TEXT="$(cat job.txt)"

# 8. PDFs land in output/
```

## Make targets

| Target | What it does |
|---|---|
| `make build` | Build the Docker image |
| `make generate URL="…"` | Generate CV + cover letter from a job-ad URL (needs `FIRECRAWL_API_KEY`) |
| `make generate TEXT="…"` | Generate CV + cover letter from pasted job-ad text |
| `make cv-only URL="…"` | CV only |
| `make letter-only URL="…"` | Cover letter only |
| `make tokens` | Print the knowledge-base token count vs. budget |
| `make shell` | Open a bash shell inside the container |
| `make test` | Run the test suite inside the container |

For job ads with shell-hostile characters, write the ad to a file and use the CLI directly:
`docker compose run --rm app python -m tailorcv generate --text-file job.txt`.

## CLI surface

```
python -m tailorcv generate (--url URL | --text TEXT | --text-file PATH)
                            [--cv-only] [--letter-only]
                            [--output-dir DIR] [--model MODEL]
python -m tailorcv kb-tokens
```

Exactly one of `--url` / `--text` / `--text-file` is required. By default both documents are
generated. Output filename: `<job title> - <company> - CV.pdf` (sanitised), falling back to a
timestamp when the title/company are unknown (e.g. pasted text).

## How it works

```
job text / URL ──► job_input.resolve() ──► job description (plain text)
                                              │
profile.yaml ─┐                               ▼
knowledge_base/*.md ─┐   generator.generate_*()  (Anthropic, prompt caching)
prompts/*.md ────────┘     system = your prompt + full KB  (KB block cached)
                           user   = job description + task
                                              │ inner HTML
assets/cv-pdf.css ─┐                          ▼
profile.yaml ──────┘   pdf.render_*()  (WeasyPrint) ──► output/*.pdf
```

The system prompt + full knowledge base are sent as a cached block, identical across the CV and
cover-letter calls, so the second call bills the knowledge base at the cache-read rate. Default model
is `claude-sonnet-4-6` (override per-run with `--model`, or globally via `TAILORCV_MODEL` in `.env`).

## Privacy / what is and isn't committed

This repo is shareable. Your private data and your prompt R&D never enter git:

| Gitignored (yours, local only) | Committed (shareable template) |
|---|---|
| `.env` (secrets) | `.env.example` |
| `profile.yaml` | `profile.example.yaml` |
| `prompts/*.md` (your real prompts) | `prompts/*.md.example` (generic placeholders) |
| `knowledge_base/*.md` content (your history) | `knowledge_base/00-summary.md` (placeholder) |
| `output/` (generated PDFs) | — |
| `docs/` (design docs, R&D) | — |

The four `prompts/*.md.example` files are simple, generic placeholders so a fresh clone can run; your
tuned prompts live in the gitignored `prompts/*.md` and stay local.

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required. Used for generation and `kb-tokens`. |
| `FIRECRAWL_API_KEY` | Required only for `--url`. |
| `TAILORCV_MODEL` | Model id (default `claude-sonnet-4-6`). |
| `TAILORCV_TOKEN_BUDGET` | KB soft limit; `make tokens`/`generate` warn (don't fail) when exceeded. |
| `TAILORCV_MAX_OUTPUT_TOKENS` | Output cap per document. |

## Project layout

```
tailorcv/            # the package: config, knowledge_base, job_input, prompts, generator, pdf, cli
assets/cv-pdf.css    # PDF stylesheet
prompts/             # *.md (gitignored) + *.md.example (committed)
knowledge_base/      # your narrative history (*.md)
tests/               # pytest suite (run via `make test`)
Dockerfile, docker-compose.yml, Makefile, pyproject.toml
```
