from app.utils.text_cleaner import normalize_whitespace, strip_headers_footers
from app.utils.validators import safe_filename, sanitize_question


def test_normalize_whitespace():
    assert normalize_whitespace("a   b\t\tc\n\n\n\nd") == "a b c\n\nd"


def test_headers_footers_and_page_numbers_removed():
    pages = [f"Hospital Guide 2026\nBody text {i}\nPage {i}\nConfidential" for i in range(1, 5)]
    cleaned = strip_headers_footers(pages)
    for i, text in enumerate(cleaned, start=1):
        assert text == f"Body text {i}"


def test_blank_page_becomes_empty_string():
    assert strip_headers_footers(["Real content here", "   \n  ", "More content"])[1] == ""


def test_sanitize_question():
    assert sanitize_question("  What\x00 is   diabetes?\n") == "What is diabetes?"


def test_safe_filename_blocks_paths():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("C:\\docs\\report.pdf") == "report.pdf"
