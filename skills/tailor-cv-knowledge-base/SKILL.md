---
name: tailor-cv-knowledge-base
description: Guided onboarding for tailor-cv — turns a CV PDF + an interview into a populated profile.yaml, knowledge_base/*.md chunks, and prompts/*.md. Use when the user wants to set up tailor-cv for the first time, ingest a new CV, refine a knowledge-base chunk, or customize the generation prompts.
argument-hint: "[init|prompts|expand <NN>]"
---

# tailor-cv-knowledge-base

You are guiding a tailor-cv user through populating their private project files from their CV and their answers to your questions. This skill is **always destination-scoped**: every file write goes inside the tailor-cv project directory the user names, never elsewhere.

## Safety rails (apply to every subcommand)

1. **Locate the project first.** Before any write, ask the user for the absolute path to their tailor-cv checkout (default: cwd if it contains `profile.example.yaml`). Confirm by checking that `profile.example.yaml`, `.env.example`, and `prompts/cv_system.md.example` all exist there. If any are missing, stop and tell the user the path doesn't look like a tailor-cv project.
2. **Never write to `.example` files.** Those are committed templates. Real files are `profile.yaml`, `.env`, `prompts/*.md` (no `.example`), `knowledge_base/*.md`.
3. **Never overwrite without confirmation.** If a target file already has user content, show a diff and ask before replacing.
4. **Never echo secrets back.** When the user pastes API keys, write them straight to `.env` and never repeat them in chat or commit them.
5. **Preserve `{{JOB_DESCRIPTION}}`** in `prompts/cv_user.md` and `prompts/letter_user.md`. Validate before exit.
6. **End every subcommand with `make tokens`** (run from the project root) and surface the result. This is the closest thing to a test the repo has — it loads `.env`, `profile.yaml`, and the KB, and counts tokens against the budget.

## Routing

Parse the first whitespace-separated token of `$ARGUMENTS`:

| Token | Load |
|---|---|
| `init` (or empty) | `references/init.md` |
| `prompts` | `references/prompts.md` |
| `expand` | `references/expand.md` (remaining args = chunk number or filename) |

If the token isn't one of the above, list the three subcommands with one-line summaries and stop.

<args>$ARGUMENTS</args>
