"""SMRITI evaluation harness (spec §3.6) — the credibility layer.

Runs the golden Q&A set through:
  (a) SMRITI (tri-modal fabric + evidence-constrained answering), and
  (b) a deliberately vanilla baseline: single dense-vector retrieval, same
      corpus chunks, same answer model, no graph, no visual, no rerank.

Metrics (LLM-as-judge with the strong model; definitions in judge prompts):
  faithfulness          — fraction of factual claims supported by the retrieved evidence
  citation_correctness  — fraction of citations whose cited source actually supports
                          the sentence citing it (SMRITI only has real citations;
                          the baseline is judged on its claims vs its own evidence)
  answer_coverage       — fraction of the human-authored expected answer points present

Usage: python eval/harness.py [--limit N]   (run from smriti/ with backend on path)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from smriti import config, llm, stores          # noqa: E402
from smriti.copilot import ask_sync, ANSWER_SYSTEM  # noqa: E402

JUDGE_PROMPT = """You are a strict evaluation judge for an industrial RAG system.

QUESTION: {question}

EVIDENCE the system retrieved (its only allowed knowledge):
{evidence}

SYSTEM ANSWER:
{answer}

EXPECTED ANSWER POINTS (from a domain expert):
{expected}

Score three things:
1. faithfulness: extract each factual claim in the answer; what fraction is
   supported by the evidence shown? (Claims of absence like "no record found"
   are supported if the evidence indeed lacks it.)
2. citation_correctness: for sentences carrying [c#] citations, what fraction
   cite an evidence block that actually supports that sentence? If the answer
   has no citation markers at all, score 0.
3. answer_coverage: what fraction of the expected points does the answer contain
   (semantically, not verbatim)? If the expected point is that the system should
   admit insufficient evidence, score 1.0 only if it did.

Return ONLY JSON:
{{"faithfulness": 0.0-1.0, "citation_correctness": 0.0-1.0,
  "answer_coverage": 0.0-1.0, "notes": "<one sentence>"}}"""

BASELINE_SYSTEM = """You are a helpful assistant answering questions about Refinery
Unit 4 using the provided context. Cite sources with [c#] markers where possible.
If the context is insufficient, say so."""


def baseline_answer(question: str) -> dict:
    """Vanilla RAG: dense-only retrieval, no graph/visual/rerank/hybrid."""
    dq = list(stores.dense_model().embed([question]))[0]
    from qdrant_client import models as qm
    res = stores.client().query_points(
        config.TEXT_COLLECTION,
        query=dq.tolist(), using="dense", limit=5, with_payload=True)
    evidence = [{"doc_id": p.payload["doc_id"], "page": p.payload.get("page", 1),
                 "text": p.payload["text"]} for p in res.points]
    ev_text = "\n\n".join(f"[c{i}] ({e['doc_id']}): {e['text'][:1200]}"
                          for i, e in enumerate(evidence, 1))
    answer = llm.complete(
        f"CONTEXT:\n{ev_text}\n\nQUESTION: {question}\n\nAnswer concisely.",
        system=BASELINE_SYSTEM, model=config.MODEL_STRONG)
    return {"answer": answer, "evidence": evidence}


def judge(question: str, evidence_texts: list[str], answer: str,
          expected: list[str]) -> dict:
    ev = "\n\n".join(f"[c{i}] {t[:1000]}" for i, t in enumerate(evidence_texts, 1))
    try:
        return llm.complete_json(JUDGE_PROMPT.format(
            question=question, evidence=ev or "(none)", answer=answer,
            expected="\n".join(f"- {p}" for p in expected)),
            model=config.MODEL_STRONG)
    except Exception as exc:
        return {"faithfulness": 0, "citation_correctness": 0,
                "answer_coverage": 0, "notes": f"judge error: {exc}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    golden = json.loads((ROOT / "eval" / "golden_qa.json").read_text())
    if args.limit:
        golden = golden[:args.limit]

    per_question = []
    for i, qa in enumerate(golden, 1):
        print(f"[{i}/{len(golden)}] {qa['q'][:70]}…", flush=True)
        t0 = time.time()
        s_final = ask_sync(qa["q"])
        s_answer = s_final["answer"]
        s_evidence = [c.get("full_text", c["snippet"]) for c in s_final["all_evidence"]]
        s_time = time.time() - t0

        t0 = time.time()
        b = baseline_answer(qa["q"])
        b_time = time.time() - t0

        s_scores = judge(qa["q"], s_evidence, s_answer, qa["expect"])
        b_scores = judge(qa["q"], [e["text"] for e in b["evidence"]],
                         b["answer"], qa["expect"])
        per_question.append({
            "question": qa["q"], "category": qa["category"],
            "smriti": {**{k: float(s_scores.get(k, 0)) for k in
                          ("faithfulness", "citation_correctness", "answer_coverage")},
                       "latency_s": round(s_time, 1),
                       "modalities": s_final["modalities_used"],
                       "notes": s_scores.get("notes", "")},
            "baseline": {**{k: float(b_scores.get(k, 0)) for k in
                            ("faithfulness", "citation_correctness", "answer_coverage")},
                         "latency_s": round(b_time, 1),
                         "notes": b_scores.get("notes", "")},
        })
        # persist incrementally so a crash keeps partial results
        _write(per_question, len(golden))
    print("done ->", ROOT / "eval" / "results.json")


def _write(per_question: list, total: int):
    keys = ("faithfulness", "citation_correctness", "answer_coverage")

    def agg(side):
        return {k: round(sum(q[side][k] for q in per_question)
                         / max(len(per_question), 1), 3) for k in keys} | {
            "latency_s": round(sum(q[side]["latency_s"] for q in per_question)
                               / max(len(per_question), 1), 1)}
    (ROOT / "eval" / "results.json").write_text(json.dumps({
        "n_questions": len(per_question), "total_planned": total,
        "aggregate": {"smriti": agg("smriti"), "baseline": agg("baseline")},
        "per_question": per_question,
    }, indent=1))


if __name__ == "__main__":
    main()
