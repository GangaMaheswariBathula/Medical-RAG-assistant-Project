"""Input sanitising and validation helpers."""
import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_question(question: str) -> str:
    """Strip control characters and collapse whitespace."""
    question = _CONTROL_CHARS.sub("", question or "")
    return re.sub(r"\s+", " ", question).strip()


def safe_filename(name: str) -> str:
    """Return only the base name so paths like ../../etc/passwd can't sneak in."""
    return (name or "").replace("\\", "/").split("/")[-1].strip()
