# `init` — first-time onboarding

## What this does
Takes the user from "empty tailor-cv checkout + a CV PDF" to:
- `.env` populated (or scaffolded with TODOs).
- `profile.yaml` populated from CV contact info.
- `knowledge_base/NN-*.md` skeletons drafted from CV body, one per role/section, using the templates in `../templates/`.

`expand <NN>` is the follow-up step that turns each skeleton into rich STAR prose via interview. Tell the user that at the end.

## Phase 1 — Locate the project

1. Ask the user: "Absolute path to your tailor-cv checkout? (Press Enter to use the current directory.)"
2. Verify the path exists and contains all of: `profile.example.yaml`, `.env.example`, `prompts/cv_system.md.example`, `knowledge_base/00-summary.md`. If any are missing, stop with: "That doesn't look like a tailor-cv project — `<missing-file>` is not there."
3. Save the path internally as `PROJECT`.

## Phase 2 — Secrets (`.env`)

1. If `PROJECT/.env` already exists, skip to Phase 3 (don't touch secrets the user already curated).
2. Otherwise: `cp $PROJECT/.env.example $PROJECT/.env`.
3. Ask the user, one at a time (use AskUserQuestion):
   - "Paste your `ANTHROPIC_API_KEY` (sk-ant-…). Required."
   - "Will you ever use `--provider google`? If yes, paste a `GEMINI_API_KEY` (AIza…); otherwise skip."
   - "Will you ever pass `--url` to scrape job ads? If yes, paste a `FIRECRAWL_API_KEY` (fc-…); otherwise skip."
4. For each provided key, use Edit to replace the corresponding placeholder line in `.env`. Never echo the key back in chat.
5. Leave `TAILORCV_PROVIDER`, `TAILORCV_TOKEN_BUDGET`, `TAILORCV_MAX_OUTPUT_TOKENS` at the defaults the example ships.

## Phase 3 — Read the CV PDF

1. Ask: "Absolute path to your CV PDF?"
2. Use Read with the path. For PDFs >10 pages, pass `pages: "1-10"` first, then read remaining ranges as needed.
3. If extraction yields <500 characters, stop and tell the user the PDF appears to be image-only — they need to OCR it first.

## Phase 4 — Generate `profile.yaml`

1. `cp $PROJECT/profile.example.yaml $PROJECT/profile.yaml` (only if it doesn't already exist; otherwise diff and confirm).
2. From the CV, extract: full name, professional title, location/timezone hint, email, phone(s), public URLs (LinkedIn, GitHub, personal site), nationalities if explicitly stated. Do NOT invent any field — leave the example's empty string / empty list if the CV doesn't say.
3. Show the proposed `profile.yaml` to the user as a single block and ask: "Apply this? (You can ask me to change any field.)" Iterate until they confirm.
4. Write the confirmed YAML with Write. Schema reference (do not invent fields outside this list):

```yaml
full_name: ""          # required
subtitle: ""
header_note: ""
email: ""
phone: ""
phone_secondary: ""
urls: [{title: "", uri: ""}]
nationalities: []
cv_footer: ""          # raw HTML; leave empty for now — populate via `expand` later
```

## Phase 5 — Draft KB chunks

1. Show the user the existing `knowledge_base/00-summary.md` and tell them: "This is the style guide the rest of your KB should match — rich prose, STAR structure, no pre-condensed bullets."
2. Plan the chunk list. From the CV identify:
   - One **overview** chunk (`01-overview.md`).
   - One **per-role** chunk per substantive role (`02-…`, `03-…`, …). Skip ≤6-month internships unless the user asks otherwise.
   - One **education/languages/interests** chunk near the end.
   - One **key-skills** chunk last.
3. Present the planned filename list to the user before writing anything. Let them rename, reorder (numeric prefix matters — files concatenate in filename order per `tailorcv/knowledge_base.py:13`), or drop entries. Resolve duplicates by re-numbering.
4. For each approved chunk:
   - Load the matching template from `../templates/` (`overview.md` for overview, `job-star.md` for roles, `skills.md` for key-skills, `education.md` for education).
   - Substitute the placeholders with what you can extract from the PDF. For STAR fields the CV almost never covers (Problem, Ownership, Measurable result), leave the `{{…_DRAFT}}` placeholder in place but add an inline `<!-- TODO: fill via /tailor-cv-knowledge-base expand NN -->` comment so `expand` knows where to interview.
   - Write to `$PROJECT/knowledge_base/NN-slugified-name.md`.
5. Do NOT overwrite an existing KB file without diffing and asking.

## Phase 6 — Verify

1. Run `make tokens` from `$PROJECT` via Bash. Surface the output.
2. If it fails (e.g., missing API key, empty KB), explain which Phase to revisit.
3. If it warns about budget overrun, tell the user that's expected for a first draft — they can trim during `expand`.
4. Tell the user the next steps: "Run `/tailor-cv-knowledge-base prompts` to customize the generation prompts, then `/tailor-cv-knowledge-base expand 02` (etc.) to turn each role skeleton into full STAR prose."
