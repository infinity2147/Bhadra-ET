"""Agent 2 — Expert Knowledge Copilot (spec §5.2).

ask() is a generator of SSE-ready events:
  {"type":"trace", ...}    router / retriever / overlay steps as they happen
  {"type":"delta","text"}  answer tokens
  {"type":"final", ...}    canonical answer object (spec §6): citations,
                           confidence, overlays, modalities, trace

The answer model is constrained to the retrieved evidence and must cite every
factual sentence with [c#] markers. "Insufficient evidence" is a first-class,
correct outcome — never a failure.
"""
from __future__ import annotations

import json
import re
from typing import Iterator

from . import config, llm
from .retrieval import retrieve

ANSWER_SYSTEM = """You are SMRITI, the institutional memory of Refinery Unit 4
(Bharat Petrochem Ltd.). You answer operations, maintenance, engineering and
compliance questions for plant personnel.

HARD RULES:
- Use ONLY the evidence blocks provided. Never use outside knowledge for plant
  facts. General engineering reasoning is allowed only to connect cited facts.
- Cite every factual claim with the marker of the evidence block it came from,
  like [c1] or [c2][c5]. Place markers at the end of the sentence they support.
- If the evidence does not answer the question, say plainly that the knowledge
  base has insufficient evidence, state what IS known from the evidence (cited),
  and suggest what document type would answer it. Start that reply with the
  exact token INSUFFICIENT_EVIDENCE.
- Be concise and operational: a field technician on a phone reads this.
- Use short paragraphs. Bold key equipment tags and dates with **...**.
- When evidence items conflict, present both with their citations and dates."""


def _evidence_block(evidence: list[dict]) -> tuple[str, list[dict]]:
    lines, citations = [], []
    for i, e in enumerate(evidence, start=1):
        cid = f"c{i}"
        citations.append({
            "id": cid, "doc_id": e["doc_id"], "page": e.get("page", 1),
            "doc_type": e.get("doc_type", "text"),
            "snippet": e["text"][:280],
            "full_text": e["text"][:1200],  # what the answer model saw (eval judge input)
            "render": e.get("render"),
        })
        lines.append(f"[{cid}] ({e.get('doc_type','text')}, {e['doc_id']}"
                     f" p{e.get('page',1)}): {e['text'][:1200]}")
    return "\n\n".join(lines), citations


def _confidence(answer: str, citations: list[dict], evidence: list[dict]) -> float:
    if answer.startswith("INSUFFICIENT_EVIDENCE"):
        return 0.25
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer) if len(s) > 30]
    cited = sum(1 for s in sentences if re.search(r"\[c\d+\]", s))
    coverage = cited / max(len(sentences), 1)
    rerank_scores = [e.get("rerank_score", 0.0) for e in evidence[:4]]
    strength = min(max((sum(rerank_scores) / max(len(rerank_scores), 1)) / 8.0, 0), 1)
    return round(0.35 + 0.45 * coverage + 0.20 * strength, 2)


def ask(query: str, stream_tokens: bool = True) -> Iterator[dict]:
    trace: list[dict] = []
    yield {"type": "trace", "step": "start", "query": query}
    r = retrieve(query, trace=trace)
    for t in trace:
        yield {"type": "trace", **t}

    ev_text, citations = _evidence_block(r["evidence"])
    used_markers: set[str] = set()
    prompt = (f"EVIDENCE BLOCKS:\n{ev_text}\n\n"
              f"QUESTION from plant personnel: {query}\n\n"
              f"Answer per your rules, citing evidence markers.")

    parts: list[str] = []
    if stream_tokens:
        for tok in llm.stream(prompt, system=ANSWER_SYSTEM, model=config.MODEL_STRONG):
            parts.append(tok)
            yield {"type": "delta", "text": tok}
        answer = "".join(parts)
    else:
        answer = llm.complete(prompt, system=ANSWER_SYSTEM, model=config.MODEL_STRONG)

    used_markers = set(re.findall(r"\[(c\d+)\]", answer))
    used_citations = [c for c in citations if c["id"] in used_markers]
    insufficient = answer.startswith("INSUFFICIENT_EVIDENCE")
    clean_answer = answer.removeprefix("INSUFFICIENT_EVIDENCE").strip()

    yield {"type": "final",
           "answer": clean_answer,
           "citations": used_citations,
           "all_evidence": citations,
           "modalities_used": r["routing"]["modalities"],
           "tags": r["routing"]["tags"],
           "confidence": _confidence(answer, used_citations, r["evidence"]),
           "drawing_overlays": r["overlays"],
           "insufficient_evidence": insufficient,
           "reasoning_trace": trace}


def ask_sync(query: str) -> dict:
    """Non-streaming variant used by the eval harness."""
    final = None
    for ev in ask(query, stream_tokens=False):
        if ev["type"] == "final":
            final = ev
    return final
