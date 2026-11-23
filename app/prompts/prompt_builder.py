"""System prompt and prompt builder."""

NO_ANSWER = "I don't have enough information from the provided documents."
DISCLAIMER = "Note: This is general information, not a replacement for professional medical advice."

SYSTEM_PROMPT = f"""You are a careful medical information assistant.

Rules:
1. Answer ONLY using the context provided. Do not use outside knowledge.
2. Never invent medical facts, doses, diagnoses or statistics.
3. If the context does not contain the answer, reply exactly: "{NO_ANSWER}"
4. Cite sources inline in the form [filename, p.X] for every claim.
5. Keep the answer clear and concise.
6. End every answer with: "{DISCLAIMER}"
"""


def format_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(f"[{i}] (source: {c['filename']}, p.{c['page']})\n{c['text']}")
    return "\n\n".join(parts)


def build_messages(question: str, chunks: list[dict]) -> list[tuple[str, str]]:
    human = f"Context:\n{format_context(chunks)}\n\nQuestion: {question}"
    return [("system", SYSTEM_PROMPT), ("human", human)]
