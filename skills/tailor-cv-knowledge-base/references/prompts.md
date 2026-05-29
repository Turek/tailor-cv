# `prompts` — customize generation prompts

## What this does
Walks the user through customizing the four `prompts/*.md` files from their `.example` siblings. The examples are sensible defaults; this subcommand lets the user bias tone, sections, edge-cases, and forbidden moves to their preference.

## Phase 1 — Locate the project

Same as `init` Phase 1. Save `PROJECT`.

## Phase 2 — Take inventory

For each of the four prompts, check whether the real file already exists:

| Real file | Example source |
|---|---|
| `prompts/cv_system.md` | `prompts/cv_system.md.example` |
| `prompts/cv_user.md` | `prompts/cv_user.md.example` |
| `prompts/cover_letter_system.md` | `prompts/cover_letter_system.md.example` |
| `prompts/letter_user.md` | `prompts/letter_user.md.example` |

For each missing real file, `cp` the `.example` over. For each already-present real file, ask the user whether to leave it untouched or re-baseline from the example (warn: re-baseline will discard their edits — diff first).

## Phase 3 — Interview

Ask the user, one question at a time, using AskUserQuestion. These map to the customizations the example prompts already invite:

1. **Tone** — "How formal should the CV/letter sound? (formal & corporate / neutral & confident / warm & direct / other)"
2. **Sections to surface** — "Default CV sections are Professional Summary, Work Experience, Skills, Education. Want to add/remove any? (e.g. add 'Selected Projects' or 'Speaking')"
3. **Boldness budget** — "Per bullet, how many bolded keyword spans feel right to you? (0 / 1 / 2 / let the model decide)"
4. **No-go zones** — "Anything the model should NEVER do for you? (Examples: never claim Java, never use the phrase 'passionate about', never include education)"
5. **Letter length** — "Cover letter — strict 1–2 short paragraphs, or allow up to 3?"
6. **Letter angle** — "What's the angle you want the letter to lead with? (recent shipped result / domain match / specific named hook from the ad / your call)"

Take notes; don't write yet.

## Phase 4 — Apply the answers

For each of the four prompts:
1. Read the current real file (or the freshly-copied example).
2. Edit it with concrete additions/deletions that encode the answers. Examples of mechanical edits:
   - Tone answer → adjust the "voice" sentence in `cv_system.md` and `cover_letter_system.md`.
   - Sections answer → update the "Use only these section headings" line in `cv_system.md`.
   - Boldness answer → update the "0–2 spans per bullet" line.
   - No-go zones → append a new "Never:" bullet list inside the system prompts.
   - Letter length / angle → update the corresponding lines in `cover_letter_system.md`.
3. **Do not** rewrite the user prompts (`cv_user.md`, `letter_user.md`) unless the user asks — they're already minimal. Just verify `{{JOB_DESCRIPTION}}` is present.

Show the user the proposed diff for each file. Apply on confirmation.

## Phase 5 — Validate placeholders

Re-read `prompts/cv_user.md` and `prompts/letter_user.md` after writing. Confirm both contain the literal string `{{JOB_DESCRIPTION}}`. If either is missing it, restore the placeholder before exit — `tailorcv/prompts.py` will SystemExit at generation time without it.

## Phase 6 — Verify

Skip `make tokens` here — it costs an Anthropic API round-trip and `prompts` didn't touch the KB, so the count won't change. Run the targeted checks that actually exercise what `prompts` changed:

1. Confirm the `{{JOB_DESCRIPTION}}` placeholder survived in both user prompts:
   ```bash
   grep -l '{{JOB_DESCRIPTION}}' "$PROJECT/prompts/cv_user.md" "$PROJECT/prompts/letter_user.md"
   ```
   Expected output: both filenames. If either is missing, you skipped Phase 5 — go back.

2. Confirm all four prompts load through `tailorcv/prompts.py` without raising (this catches empty files, missing placeholders, and missing files in one shot):
   ```bash
   docker compose run --rm app python -c \
     'from tailorcv.prompts import cv_system_prompt, cover_letter_system_prompt, build_cv_user_prompt, build_letter_user_prompt; cv_system_prompt(); cover_letter_system_prompt(); build_cv_user_prompt("x"); build_letter_user_prompt("x"); print("prompts: OK")'
   ```

Tell the user they can do a fuller dry run with `make generate TEXT="dummy job ad"` whenever they want to exercise the prompts end-to-end (that one DOES cost an API call).
