from app.prompts.prompt_builder import NO_ANSWER, build_messages, format_context

CHUNKS = [
    {"text": "Diabetes causes increased thirst.", "filename": "guide.pdf", "page": 3, "score": 0.8},
    {"text": "Insulin lowers blood sugar.", "filename": "guide.pdf", "page": 5, "score": 0.7},
]


def test_format_context_numbers_and_cites_sources():
    ctx = format_context(CHUNKS)
    assert "[1] (source: guide.pdf, p.3)" in ctx
    assert "[2] (source: guide.pdf, p.5)" in ctx


def test_build_messages_structure_and_rules():
    system, human = build_messages("What causes thirst?", CHUNKS)
    assert system[0] == "system" and human[0] == "human"
    assert NO_ANSWER in system[1]
    assert "not a replacement for professional medical advice" in system[1]
    assert "What causes thirst?" in human[1]
    assert "Diabetes causes increased thirst." in human[1]
