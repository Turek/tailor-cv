import pytest
from pathlib import Path
from tailorcv import prompts


def test_load_missing_raises(tmp_path):
    with pytest.raises(SystemExit):
        prompts.cv_system_prompt(prompts_dir=tmp_path)


def test_cv_system_loads_and_strips(tmp_path):
    (tmp_path / "cv_system.md").write_text("  SYSTEM PROMPT BODY  \n", encoding="utf-8")
    assert prompts.cv_system_prompt(prompts_dir=tmp_path) == "SYSTEM PROMPT BODY"


def test_cover_letter_system_loads(tmp_path):
    (tmp_path / "cover_letter_system.md").write_text("LETTER SYS", encoding="utf-8")
    assert prompts.cover_letter_system_prompt(prompts_dir=tmp_path) == "LETTER SYS"


def test_build_cv_user_substitutes_placeholder(tmp_path):
    (tmp_path / "cv_user.md").write_text("Job:\n{{JOB_DESCRIPTION}}\nEnd.", encoding="utf-8")
    out = prompts.build_cv_user_prompt("ACME ROLE", prompts_dir=tmp_path)
    assert "ACME ROLE" in out
    assert "{{JOB_DESCRIPTION}}" not in out


def test_build_letter_user_substitutes(tmp_path):
    (tmp_path / "letter_user.md").write_text("{{JOB_DESCRIPTION}}", encoding="utf-8")
    assert prompts.build_letter_user_prompt("XYZ", prompts_dir=tmp_path) == "XYZ"


def test_empty_prompt_raises(tmp_path):
    (tmp_path / "cover_letter_system.md").write_text("   \n  ", encoding="utf-8")
    with pytest.raises(SystemExit):
        prompts.cover_letter_system_prompt(prompts_dir=tmp_path)


def test_committed_example_user_prompts_contain_placeholder():
    # The committed .example files are bind-mounted at /app/prompts in the container.
    for name in ("cv_user", "letter_user"):
        txt = Path("prompts") / f"{name}.md.example"
        assert txt.exists(), f"{txt} missing"
        assert "{{JOB_DESCRIPTION}}" in txt.read_text(encoding="utf-8")
