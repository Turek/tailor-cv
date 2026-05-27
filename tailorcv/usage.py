"""Anthropic token-usage aggregation and cost estimation."""
from __future__ import annotations

# USD per 1,000,000 tokens: (input_rate, output_rate).
# Cache write = 1.25x input rate (5-minute TTL); cache read = 0.1x input rate.
PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def _field(u, name: str) -> int:
    return getattr(u, name, 0) or 0


def totals(usages: list) -> dict[str, int]:
    return {
        "input": sum(_field(u, "input_tokens") for u in usages),
        "output": sum(_field(u, "output_tokens") for u in usages),
        "cache_write": sum(_field(u, "cache_creation_input_tokens") for u in usages),
        "cache_read": sum(_field(u, "cache_read_input_tokens") for u in usages),
    }


def estimate_cost(t: dict[str, int], model: str) -> float | None:
    rates = PRICING.get(model)
    if rates is None:
        return None
    in_rate, out_rate = rates
    return (
        t["input"] / 1e6 * in_rate
        + t["output"] / 1e6 * out_rate
        + t["cache_write"] / 1e6 * (in_rate * 1.25)
        + t["cache_read"] / 1e6 * (in_rate * 0.10)
    )


def summarize(usages: list, model: str) -> str:
    t = totals(usages)
    n = len(usages)
    lines = [
        f"Token usage ({n} call{'s' if n != 1 else ''}): "
        f"input(uncached) {t['input']:,} | cache-write {t['cache_write']:,} | "
        f"cache-read {t['cache_read']:,} | output {t['output']:,}"
    ]
    cost = estimate_cost(t, model)
    if cost is None:
        lines.append(f"Estimated cost: n/a (no pricing table for {model})")
    else:
        lines.append(f"Estimated cost ({model}): ${cost:.4f}")
    return "\n".join(lines)
