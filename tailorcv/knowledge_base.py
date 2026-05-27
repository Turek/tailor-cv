"""Knowledge-base loading and token accounting."""
from __future__ import annotations

from pathlib import Path

import anthropic


def load_kb(kb_dir: str | Path = "knowledge_base") -> str:
    """Concatenate all .md files in filename order, each prefixed by its name."""
    kb_dir = Path(kb_dir)
    files = sorted(kb_dir.glob("*.md"))
    if not files:
        raise SystemExit(f"No .md files found in {kb_dir}/. Add your knowledge base.")
    parts = []
    for f in files:
        text = f.read_text(encoding="utf-8").strip()
        if text:
            parts.append(f"# [Source: {f.name}]\n\n{text}")
    result = "\n\n---\n\n".join(parts)
    if not result:
        raise SystemExit(
            f"All .md files in {kb_dir}/ are empty. Add content to your knowledge base."
        )
    return result


def count_tokens(text: str, model: str, api_key: str) -> int:
    """Count tokens using the Anthropic token-counting API."""
    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": text}],
        )
    except anthropic.APIError as e:
        raise SystemExit(f"Token counting failed: {e}") from e
    return resp.input_tokens


def check_budget(token_count: int, budget: int) -> str | None:
    """Return a warning string if over budget, else None."""
    if token_count > budget:
        return (
            f"⚠️  Knowledge base is {token_count:,} tokens, over the "
            f"{budget:,}-token budget. Output quality may degrade; consider trimming."
        )
    return None
