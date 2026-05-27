from types import SimpleNamespace
from tailorcv import usage


def _u(inp, out, cw=0, cr=0):
    return SimpleNamespace(
        input_tokens=inp,
        output_tokens=out,
        cache_creation_input_tokens=cw,
        cache_read_input_tokens=cr,
    )


def test_totals_sum_across_calls():
    t = usage.totals([_u(100, 50, cw=1000, cr=0), _u(20, 80, cw=0, cr=1000)])
    assert t["input"] == 120
    assert t["output"] == 130
    assert t["cache_write"] == 1000
    assert t["cache_read"] == 1000


def test_none_cache_fields_treated_as_zero():
    t = usage.totals([_u(10, 10, cw=None, cr=None)])
    assert t["cache_write"] == 0 and t["cache_read"] == 0


def test_estimate_cost_known_model():
    # sonnet-4-6: $3/M input, $15/M output, cache write 1.25x input, cache read 0.1x input
    t = {"input": 1_000_000, "output": 1_000_000, "cache_write": 1_000_000, "cache_read": 1_000_000}
    cost = usage.estimate_cost(t, "claude-sonnet-4-6")
    # 3 + 15 + 3.75 + 0.30 = 22.05
    assert cost is not None
    assert abs(cost - 22.05) < 1e-6


def test_estimate_cost_unknown_model_returns_none():
    assert usage.estimate_cost({"input": 1, "output": 1, "cache_write": 0, "cache_read": 0}, "mystery-model") is None


def test_summarize_includes_tokens_and_cost():
    s = usage.summarize([_u(100, 50, cw=1000, cr=2000)], "claude-sonnet-4-6")
    assert "100" in s            # input tokens
    assert "1,000" in s or "1000" in s  # cache write
    assert "claude-sonnet-4-6" in s
    assert "$" in s


def test_summarize_unknown_model_notes_no_pricing():
    s = usage.summarize([_u(100, 50)], "mystery-model")
    assert "mystery-model" in s
    # cost unavailable wording — must NOT print a fake "$" amount for unknown model
    assert "n/a" in s.lower() or "unavailable" in s.lower()
