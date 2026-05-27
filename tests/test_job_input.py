import pytest
from tailorcv import job_input
from tailorcv.config import Config, Profile


def _cfg(firecrawl=""):
    return Config(
        profile=Profile(full_name="X"),
        anthropic_api_key="sk-ant-test",
        firecrawl_api_key=firecrawl,
    )


def test_two_inputs_raises():
    with pytest.raises(SystemExit):
        job_input.resolve(text="x" * 200, url="http://e.com", cfg=_cfg())


def test_no_input_raises():
    with pytest.raises(SystemExit):
        job_input.resolve(cfg=_cfg())


def test_short_text_raises():
    with pytest.raises(SystemExit):
        job_input.resolve(text="too short", cfg=_cfg())


def test_valid_text_passthrough():
    body = "A" * 250
    ji = job_input.resolve(text=body, cfg=_cfg())
    assert ji.description == body
    assert ji.title == ""


def test_text_file_read(tmp_path):
    f = tmp_path / "job.txt"
    f.write_text("B" * 250, encoding="utf-8")
    ji = job_input.resolve(text_file=str(f), cfg=_cfg())
    assert ji.description == "B" * 250


def test_url_without_key_raises():
    with pytest.raises(SystemExit):
        job_input.resolve(url="http://e.com", cfg=_cfg(firecrawl=""))


def test_url_rich_markdown(monkeypatch):
    class FakeDoc:
        markdown = "C" * 500
        metadata = {"title": "Senior Engineer", "ogSiteName": "ACME"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def scrape(self, url, formats=None):
            assert formats == ["markdown"]
            return FakeDoc()

    monkeypatch.setattr("firecrawl.Firecrawl", FakeClient)
    ji = job_input.resolve(url="http://e.com", cfg=_cfg(firecrawl="fc-key"))
    assert ji.description == "C" * 500
    assert ji.title == "Senior Engineer"
    assert ji.company == "ACME"


def test_url_metadata_as_object(monkeypatch):
    # metadata exposed as attributes rather than dict
    class Meta:
        title = "Lead Dev"
        ogSiteName = "Globex"

    class FakeDoc:
        markdown = "D" * 500
        metadata = Meta()

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def scrape(self, url, formats=None):
            return FakeDoc()

    monkeypatch.setattr("firecrawl.Firecrawl", FakeClient)
    ji = job_input.resolve(url="http://e.com", cfg=_cfg(firecrawl="fc-key"))
    assert ji.title == "Lead Dev"
    assert ji.company == "Globex"


def test_url_thin_markdown_raises(monkeypatch):
    class FakeDoc:
        markdown = "tiny"
        metadata = {}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def scrape(self, url, formats=None):
            return FakeDoc()

    monkeypatch.setattr("firecrawl.Firecrawl", FakeClient)
    with pytest.raises(SystemExit):
        job_input.resolve(url="http://e.com", cfg=_cfg(firecrawl="fc-key"))
