"""Token-usage aggregation and cost estimation, provider-neutral."""
from __future__ import annotations

# USD per 1,000,000 tokens: (input_rate, output_rate).
# Cache write = 1.25x input rate (5-minute TTL); cache read = 0.1x input rate.
PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # Gemini Flash 2.5 paid tier (AI Studio free tier costs $0).
    "gemini-2.5-flash": (0.30, 2.50),
}


def _i(value) -> int:
    return int(value) if value else 0


def totals(usages: list) -> dict[str, int]:
    return {
        "input": sum(_i(getattr(u, "input_tokens", 0)) for u in usages),
        "output": sum(_i(getattr(u, "output_tokens", 0)) for u in usages),
        "cache_write": sum(_i(getattr(u, "cache_write", 0)) for u in usages),
        "cache_read": sum(_i(getattr(u, "cache_read", 0)) for u in usages),
    }


def _any_cache_data(usages: list) -> bool:
    for u in usages:
        if getattr(u, "cache_read", None) is not None:
            return True
        if getattr(u, "cache_write", None) is not None:
            return True
    return False


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
    parts = [f"input(uncached) {t['input']:,}"]
    if _any_cache_data(usages):
        parts.append(f"cache-write {t['cache_write']:,}")
        parts.append(f"cache-read {t['cache_read']:,}")
    parts.append(f"output {t['output']:,}")
    lines = [
        f"Token usage ({n} call{'s' if n != 1 else ''}): " + " | ".join(parts)
    ]
    cost = estimate_cost(t, model)
    if cost is None:
        lines.append(f"Estimated cost: n/a (no pricing table for {model})")
    else:
        lines.append(f"Estimated cost ({model}): ${cost:.4f}")
    return "\n".join(lines)
