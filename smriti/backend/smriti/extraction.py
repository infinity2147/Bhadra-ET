"""LLM entity/relation extraction with a typed-schema prompt (spec §5.1 step 3).

Used for unstructured sources (emails, ad-hoc uploads). Structured CMMS-style
records map directly to typed nodes without an LLM (spec §3.4d).
Extractions that don't fit the ontology are rejected and queued for review.
"""
from __future__ import annotations

import json

from . import config, llm
from .ontology import EDGE_TYPES, NODE_TYPES

_SCHEMA_PROMPT = """You are an information extraction engine for an industrial plant
knowledge graph. Extract entities and relations from the document below.

Allowed node types: {node_types}
Allowed edge types: {edge_types}

Known equipment tags in this plant (canonical IDs — reuse them EXACTLY if mentioned,
including partial mentions like "the booster pump" when the tag appears nearby):
{known_tags}

Return ONLY JSON:
{{
 "entities": [{{"id": "<canonical id, e.g. P-101 or person name>", "type": "<node type>",
                "props": {{...optional properties...}}}}],
 "relations": [{{"src": "<entity id>", "dst": "<entity id>", "type": "<edge type>"}}],
 "summary": "<one sentence: what knowledge this document adds>"
}}

Rules:
- Only extract facts stated in the document. No inference beyond the text.
- Prefer existing canonical tags over inventing new ids.
- Dates in ISO format inside props where present.
- If nothing fits the ontology, return empty lists.

DOCUMENT ({doc_id}):
---
{text}
---"""


def extract(doc_id: str, text: str, known_tags: list[str]) -> dict:
    prompt = _SCHEMA_PROMPT.format(
        node_types=", ".join(sorted(NODE_TYPES)),
        edge_types=", ".join(sorted(EDGE_TYPES)),
        known_tags=", ".join(sorted(known_tags)) or "(none yet)",
        doc_id=doc_id, text=text[:6000])
    result = llm.complete_json(prompt, model=config.MODEL_STRONG)
    accepted = {"entities": [], "relations": [], "summary": result.get("summary", "")}
    rejected = []
    ids = set()
    for ent in result.get("entities", []):
        if ent.get("type") in NODE_TYPES and ent.get("id"):
            accepted["entities"].append(ent)
            ids.add(ent["id"])
        else:
            rejected.append({"kind": "entity", **ent})
    for rel in result.get("relations", []):
        if rel.get("type") in EDGE_TYPES and rel.get("src") and rel.get("dst"):
            accepted["relations"].append(rel)
        else:
            rejected.append({"kind": "relation", **rel})
    accepted["rejected"] = rejected  # human-review queue
    return accepted
