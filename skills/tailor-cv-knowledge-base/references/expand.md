# `expand <NN>` — interview to deepen one KB chunk

## What this does
Opens a single `knowledge_base/NN-*.md` chunk and runs a focused interview to replace its `{{…_DRAFT}}` placeholders / TODO markers with rich first-person prose. This is the step that makes the KB usable — the PDF rarely contains STAR depth.

## Phase 1 — Locate the project & chunk

1. Same project-location flow as `init` Phase 1. Save `PROJECT`.
2. Parse the chunk identifier from `$ARGUMENTS`. Accept either:
   - A two-digit number (`02`) → glob `knowledge_base/02-*.md` and pick the unique match.
   - A filename (`02-msd-animal-health.md`) → use verbatim.
3. If no match or multiple matches, list candidates and ask the user to pick.

## Phase 2 — Diagnose

Read the chunk. Identify which sections still need work — anything matching `{{.*_DRAFT}}` or `<!-- TODO:` is fair game. If the chunk has no placeholders, ask the user which section they want to deepen anyway.

Classify the chunk by which template it follows (overview, STAR job, skills, education) — section headings give it away.

## Phase 3 — Interview (template-specific)

**For STAR job chunks**, ask in this order, one question at a time:
1. "Setting the scene — what was the company doing when you joined? Stage, team size, your reporting line."
2. "What was broken or missing on day one that this role was created to address?"
3. "What did you specifically own? Where did your decisions stop and someone else's start?"
4. "Walk me through 2–4 concrete things you actually did. Don't summarize — narrate."
5. "Numbers, if any: latency, revenue, headcount, time-to-X, retention. If no numbers, what's the qualitative outcome you'd stake your reputation on?"
6. "Final tech list — what did you actually use day-to-day on this role?"

**For overview chunks**: ask about career arc, 3–4 core themes, claimable-as-primary tech surface, and positioning notes the generator should respect.

**For skills chunks**: for each theme already listed, ask "What's the substrate — which roles or projects let you claim this as a primary skill, not a tool you've touched?"

**For education chunks**: confirm completion status of each entry (the example explicitly warns against fabricated degrees), language levels, and interests worth surfacing.

## Phase 4 — Draft & confirm

Compose the new section bodies from the answers in the user's voice (mirror their phrasing, don't sanitize into corporate-speak). Replace placeholders with the drafts. Show the user the full updated chunk as a single diff. Iterate on their edits. Write on confirmation.

## Phase 5 — Verify

1. Run `make tokens` from `$PROJECT`. Surface the new token count.
2. If the KB now exceeds `TAILORCV_TOKEN_BUDGET`, suggest which chunks look longest and offer a trim pass.
3. Tell the user how to do the next one: `/tailor-cv-knowledge-base expand 03` (etc.).
