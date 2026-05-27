from pathlib import Path

from tailorcv import pdf
from tailorcv.config import Profile, ProfileUrl


def _profile():
    return Profile(
        full_name="Tomasz King",
        subtitle="Senior Engineer",
        email="t@example.com",
        phone="+48 000",
        urls=[ProfileUrl(title="GitHub", uri="https://github.com/x")],
        nationalities=["Polish"],
        cv_footer="<h2>Skills</h2><p>Python</p>",
    )


def test_cv_document_contains_header_body_footer_and_css():
    doc = pdf.build_cv_document("<h2>Professional Summary</h2><p>Body</p>", _profile())
    assert "Tomasz King" in doc
    assert "<h2>Professional Summary</h2><p>Body</p>" in doc
    assert "<h2>Skills</h2><p>Python</p>" in doc
    assert "cv-accent-bar" in doc
    assert "@page" in doc
    assert 'href="mailto:t@example.com"' in doc
    assert "https://github.com/x" in doc
    assert "Nationality: Polish" in doc


def test_cv_header_escapes_scalars():
    p = _profile()
    p.full_name = "A & B <script>"
    doc = pdf.build_cv_document("<p>x</p>", p)
    assert "A &amp; B &lt;script&gt;" in doc


def test_empty_footer_omitted():
    p = _profile()
    p.cv_footer = ""
    doc = pdf.build_cv_document("<p>x</p>", p)
    assert 'class="cv-footer"' not in doc


def test_letter_document_uses_letter_classes():
    doc = pdf.build_letter_document("<p>Dear team</p>", _profile())
    assert "letter-header" in doc
    assert "letter-body" in doc
    assert "<p>Dear team</p>" in doc


def test_render_cv_writes_pdf(tmp_path):
    out = tmp_path / "cv.pdf"
    pdf.render_cv("<h2>Professional Summary</h2><p>x</p>", _profile(), out)
    data = Path(out).read_bytes()
    assert data[:4] == b"%PDF"


def test_render_cover_letter_writes_pdf(tmp_path):
    out = tmp_path / "cl.pdf"
    pdf.render_cover_letter("<p>Dear team</p>", _profile(), out)
    assert Path(out).read_bytes()[:4] == b"%PDF"
