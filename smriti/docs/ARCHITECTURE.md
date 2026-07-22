# SMRITI — System Architecture

A tri-modal knowledge fabric over a typed industrial graph, with five agents on top.
Runs fully local (no cloud dependency, no Docker required).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SOURCES          P&ID drawings · work orders (CMMS) · SOPs (rev chains) ·      │
│  the whole       inspections · incidents / near-miss · OEM manuals (scanned) · │
│  estate          permits to work · email · OISD / Factories Act / PESO clauses │
└──────────────────────────────────────────────────────────────────────────────┘
        │  Ingestion (Agent 1): per-type parsers · LLM entity/relation extraction
        │  · entity resolution.  Continuous intake: structured forms · bulk CMMS
        ▼  CSV/JSON · auto-classifying upload  (identical graph writes as batch)
┌──────────────────────────────────────────────────────────────────────────────┐
│ KNOWLEDGE STORE  Industrial Knowledge Graph — NetworkX, typed ontology,        │
│  typed +         provenance on every node/edge, SUPERSEDES version chains      │
│  provenanced     Qdrant (embedded): text (dense bge-small + sparse BM25)       │
│                  · visual (colSmol-256M multivector, MaxSim)                   │
│                  DrawingRegion index — pixels ⇄ graph nodes                    │
└──────────────────────────────────────────────────────────────────────────────┘
        │  Retrieval fabric: intent router → text ‖ graph ‖ visual fan-out →
        ▼  RRF fusion → cross-encoder rerank → provenance + drawing overlays
┌──────────────────────────────────────────────────────────────────────────────┐
│ AGENTS           2 Expert Copilot (streaming, multi-turn)                      │
│  evidence-       3 Diagnostics / RCA (graph-native)                            │
│  constrained,    4 Compliance (clause ⇄ record)                               │
│  all cited       5 Lessons & Proactive Warnings                                │
└──────────────────────────────────────────────────────────────────────────────┘
        │  Presentation: vanilla-JS PWA — streaming chat with [c#] citations ·
        ▼  Drawing Viewer w/ live overlays + feed-path trace · reasoning trace
┌──────────────────────────────────────────────────────────────────────────────┐
│ USER SURFACES    Ask · Assets · Diagnostics · Warnings · Compliance ·          │
│                  Evaluation · Add data (live intake)                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

## One query, end to end

```
user asks
  → router classifies intent & tags
  → tri-modal fan-out:   text (hybrid dense+BM25)  ‖  graph (typed traversal)  ‖  visual (MaxSim)
  → RRF merge → cross-encoder rerank
  → provenance attached (doc, page, bbox, graph nodes)
  → answer streams with inline [c#] citations
  → if a drawing is in evidence, the Drawing Viewer renders it with regions
    highlighted and the feed path traced
  → every step logged to the reasoning trace AND the evaluation harness
```

## Design principles

- **Trust as a feature** — every sentence cites; citations click through to the exact
  page/region; "insufficient evidence" is a first-class answer; retrieval quality is
  measured against a baseline.
- **Built to run continuously** — new records enter through typed forms, bulk CMMS
  export, or auto-classified upload and write the *same* typed `:rec` nodes as the batch
  build, stamped `manual_intake · confidence 1.0` for audit — so a new incident is
  instantly in the timeline and a new permit fires warnings live.
- **Local-first** — NetworkX + embedded Qdrant + CPU/MPS models; no cloud, no Docker.
  The graph layer ports to Neo4j behind the same typed-ontology/provenance contract.

See [OVERVIEW.md](OVERVIEW.md) for the full write-up and [decisions.md](decisions.md)
for the engineering rationale behind each component choice.
