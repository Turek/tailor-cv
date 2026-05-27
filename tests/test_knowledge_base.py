import pytest
from tailorcv.knowledge_base import load_kb, check_budget, count_tokens


def test_load_kb_concatenates_in_order_with_filename_headers(tmp_path):
    (tmp_path / "01-b.md").write_text("Second file body.", encoding="utf-8")
    (tmp_path / "00-a.md").write_text("First file body.", encoding="utf-8")
    out = load_kb(tmp_path)
    assert out.index("00-a.md") < out.index("01-b.md")
    assert "First file body." in out
    assert "Second file body." in out
    assert "[Source: 00-a.md]" in out


def test_load_kb_empty_dir_raises(tmp_path):
    with pytest.raises(SystemExit):
        load_kb(tmp_path)


def test_load_kb_whitespace_only_files_raises(tmp_path):
    (tmp_path / "empty.md").write_text("   \n\n  ", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_kb(tmp_path)


def test_check_budget_warns_only_when_over():
    assert check_budget(100, 70000) is None
    warn = check_budget(80000, 70000)
    assert warn is not None
    assert "80,000" in warn


def test_count_tokens_uses_client(monkeypatch):
    class FakeResp:
        input_tokens = 1234

    class FakeMessages:
        def count_tokens(self, **kwargs):
            assert kwargs["model"] == "claude-sonnet-4-6"
            assert kwargs["messages"][0]["content"] == "hello"
            return FakeResp()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)
    assert count_tokens("hello", "claude-sonnet-4-6", "sk-ant-test") == 1234
