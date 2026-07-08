"""Typed ontology for the Industrial Knowledge Graph (spec §3.1).

Every node/edge written to the graph must use these types and carry provenance.
Free-text entity types are rejected at write time and queued for review.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

NODE_TYPES = {
    "Equipment",        # tag, equipment_type, manufacturer, model, install_date, area, criticality
    "System",           # hierarchical Unit -> System -> Equipment
    "Area",
    "Document",         # doc_type: PID | WO | SOP | inspection | OEM_manual | incident | permit | regulatory | email
    "DrawingRegion",    # doc_id, page, bbox, symbol_class, equipment_tag
    "Procedure",        # SOP steps, hazards, permits
    "WorkOrder",        # wo_id, equipment, date, wo_type (PM/CM/breakdown), findings, downtime_h
    "Inspection",       # equipment, date, method, measurements, result
    "Incident",         # incident/near-miss: date, area, category, root_cause, precursors
    "FailureMode",      # canonical, ISO 14224-aligned where possible
    "RegulatoryClause", # standard_id, clause_id, requirement, applicability, source_url
    "Person",
    "Parameter",        # process parameter with units + normal range
}

EDGE_TYPES = {
    "FEEDS_INTO", "PART_OF", "LOCATED_IN",
    "DESCRIBED_BY",      # equipment -> document
    "MAINTAINED_BY",     # equipment -> work order
    "INSPECTED_BY",      # equipment -> inspection
    "GOVERNED_BY",       # equipment/procedure -> regulatory clause
    "HAS_FAILURE_MODE", "CAUSED_BY", "REMEDIED_BY",
    "SIMILAR_TO",        # incident <-> incident (learned)
    "AUTHORED_BY", "SUPERSEDES", "REFERENCED_IN", "CONFLICTS_WITH",
    "INVOLVES",          # incident/permit -> equipment/area
    "HAS_REGION",        # document -> drawing region
}


@dataclass
class Provenance:
    """Where a fact came from. Attached to every node and edge (spec §3.5)."""
    source_doc_id: str
    page: Optional[int] = None
    bbox: Optional[list] = None          # [x0, y0, x1, y1] in rendered-page pixels
    extractor: str = "unknown"           # generator | llm_extraction | digitizer | manual
    confidence: float = 1.0
    effective_date: Optional[str] = None  # ISO date

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class OntologyError(ValueError):
    pass


def check_node_type(node_type: str) -> None:
    if node_type not in NODE_TYPES:
        raise OntologyError(f"Unknown node type {node_type!r}; allowed: {sorted(NODE_TYPES)}")


def check_edge_type(edge_type: str) -> None:
    if edge_type not in EDGE_TYPES:
        raise OntologyError(f"Unknown edge type {edge_type!r}; allowed: {sorted(EDGE_TYPES)}")
