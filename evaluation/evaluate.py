"""Evaluate the running API.

Edit evaluation/eval_questions.json so in-scope questions match YOUR documents,
then run:  python -m evaluation.evaluate --api http://localhost:8000 [--judge]

Metrics
- Retrieval relevance : an expected keyword appears in at least one retrieved chunk
- Answer hit rate     : an expected keyword appears in the answer
- Correct refusal     : out-of-scope questions get the "not enough information" reply
- Hallucination rate  : out-of-scope questions answered anyway (+ ungrounded answers with --judge)
- Latency             : mean and p95
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import requests

from app.prompts.prompt_builder import NO_ANSWER


def judge_grounded(question: str, answer: str, sources: list[dict]) -> bool:
    """LLM-as-judge: is every claim in the answer supported by the sources?"""
    from app.services.llm_service import LLMService

    context = "\n\n".join(s["text"] for s in sources)
    prompt = [
        ("system", "You are a strict fact checker. Reply with only YES or NO."),
        ("human", f"Context:\n{context}\n\nAnswer:\n{answer}\n\n"
                  "Is every factual claim in the Answer supported by the Context?"),
    ]
    return LLMService().generate(prompt).strip().upper().startswith("YES")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--questions", default="evaluation/eval_questions.json")
    parser.add_argument("--judge", action="store_true", help="use Groq to judge groundedness")
    args = parser.parse_args()

    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    rows, latencies = [], []
    retrieval_hits = answer_hits = refusals = hallucinations = 0
    in_scope_n = out_scope_n = 0

    for item in questions:
        started = time.perf_counter()
        resp = requests.post(f"{args.api}/ask", json={"question": item["question"]}, timeout=120)
        latencies.append((time.perf_counter() - started) * 1000)
        if not resp.ok:
            rows.append((item["question"], "ERROR", resp.text[:80], "-", "-"))
            continue
        data = resp.json()
        answer, sources = data["answer"], data["sources"]
        refused = NO_ANSWER.lower() in answer.lower()
        kws = [k.lower() for k in item.get("expected_keywords", [])]

        if item["in_scope"]:
            in_scope_n += 1
            r_hit = any(k in s["text"].lower() for s in sources for k in kws)
            a_hit = any(k in answer.lower() for k in kws)
            retrieval_hits += r_hit
            answer_hits += a_hit
            grounded = judge_grounded(item["question"], answer, sources) if args.judge and sources and not refused else None
            if grounded is False:
                hallucinations += 1
            rows.append((item["question"], "in-scope", f"retrieval={'PASS' if r_hit else 'FAIL'}",
                         f"answer={'PASS' if a_hit else 'FAIL'}", f"grounded={grounded}"))
        else:
            out_scope_n += 1
            if refused:
                refusals += 1
            else:
                hallucinations += 1
            rows.append((item["question"], "out-of-scope", f"refused={'PASS' if refused else 'FAIL'}", "-", "-"))

    total = max(in_scope_n + out_scope_n, 1)
    p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0
    lines = [
        "# Evaluation Report", "",
        f"- Questions: {total} ({in_scope_n} in-scope, {out_scope_n} out-of-scope)",
        f"- Retrieval relevance: {retrieval_hits}/{in_scope_n}",
        f"- Answer hit rate: {answer_hits}/{in_scope_n}",
        f"- Correct refusals: {refusals}/{out_scope_n}",
        f"- Hallucination rate: {hallucinations}/{total} ({100 * hallucinations / total:.0f}%)",
        f"- Latency: mean {statistics.mean(latencies) if latencies else 0:.0f} ms, p95 {p95:.0f} ms", "",
        "| Question | Type | Check 1 | Check 2 | Check 3 |", "|---|---|---|---|---|",
    ]
    lines += [f"| {' | '.join(r)} |" for r in rows]
    report = "\n".join(lines)
    Path("evaluation/report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
