"""Text cleaning: headers, footers, page numbers, blank pages, whitespace."""
import re
from collections import Counter

_PAGE_NUMBER = re.compile(r"^(page\s*)?\d+(\s*(of|/)\s*\d+)?$", re.IGNORECASE)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _edge_lines(page_text: str, n: int = 2) -> set[str]:
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    return set(lines[:n] + lines[-n:])


def strip_headers_footers(pages: list[str], min_pages: int = 3, ratio: float = 0.6) -> list[str]:
    """Remove lines repeated at the top/bottom of most pages, plus page numbers.

    Returns one cleaned string per page. Blank pages come back as "".
    """
    repeated: set[str] = set()
    if len(pages) >= min_pages:
        counts: Counter[str] = Counter()
        for page in pages:
            counts.update(_edge_lines(page))
        repeated = {line for line, c in counts.items() if c / len(pages) >= ratio}

    cleaned = []
    for page in pages:
        kept = [
            ln.strip()
            for ln in page.splitlines()
            if ln.strip() and ln.strip() not in repeated and not _PAGE_NUMBER.match(ln.strip())
        ]
        cleaned.append(normalize_whitespace("\n".join(kept)))
    return cleaned
