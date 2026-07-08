"""Industrial Knowledge Graph store.

NetworkX MultiDiGraph with the typed ontology enforced at write time and
provenance on every node/edge. JSON-persisted. At hackathon scale (<10k nodes)
every traversal here is sub-millisecond; the data contracts are what matter
and they port unchanged to Neo4j/Memgraph (see docs/decisions.md).
"""
from __future__ import annotations

import json
import threading
from typing import Iterable, Optional

import networkx as nx

from . import config
from .ontology import Provenance, check_edge_type, check_node_type


class KnowledgeGraph:
    def __init__(self, path=None):
        self.path = path or config.GRAPH_PATH
        self.g = nx.MultiDiGraph()
        self._lock = threading.Lock()
        if self.path.exists():
            self.load()

    # -- write ---------------------------------------------------------------
    def add_node(self, node_id: str, node_type: str, provenance: Provenance,
                 **props) -> str:
        check_node_type(node_type)
        with self._lock:
            if node_id in self.g:
                existing = self.g.nodes[node_id]
                # merge: keep first-seen type, accumulate provenance + new props
                existing.setdefault("provenance", []).append(provenance.to_dict())
                for k, v in props.items():
                    existing.setdefault(k, v)
            else:
                self.g.add_node(node_id, type=node_type,
                                provenance=[provenance.to_dict()], **props)
        return node_id

    def add_edge(self, src: str, dst: str, edge_type: str, provenance: Provenance,
                 **props) -> None:
        check_edge_type(edge_type)
        with self._lock:
            # avoid exact duplicates of the same typed edge
            if self.g.has_edge(src, dst):
                for key, data in self.g[src][dst].items():
                    if data.get("type") == edge_type:
                        data.setdefault("provenance", []).append(provenance.to_dict())
                        return
            self.g.add_edge(src, dst, type=edge_type,
                            provenance=[provenance.to_dict()], **props)

    # -- read ----------------------------------------------------------------
    def node(self, node_id: str) -> Optional[dict]:
        if node_id in self.g:
            return {"id": node_id, **self.g.nodes[node_id]}
        return None

    def nodes_by_type(self, node_type: str) -> list[dict]:
        return [{"id": n, **d} for n, d in self.g.nodes(data=True)
                if d.get("type") == node_type]

    def edges_of(self, node_id: str, edge_type: Optional[str] = None,
                 direction: str = "both") -> list[dict]:
        out = []
        if node_id not in self.g:
            return out
        if direction in ("out", "both"):
            for _, dst, data in self.g.out_edges(node_id, data=True):
                if edge_type is None or data.get("type") == edge_type:
                    out.append({"src": node_id, "dst": dst, **data})
        if direction in ("in", "both"):
            for src, _, data in self.g.in_edges(node_id, data=True):
                if edge_type is None or data.get("type") == edge_type:
                    out.append({"src": src, "dst": node_id, **data})
        return out

    def neighborhood(self, node_id: str, depth: int = 1,
                     edge_types: Optional[Iterable[str]] = None) -> dict:
        """Full typed neighborhood: the payload behind get_equipment_context()."""
        if node_id not in self.g:
            return {"nodes": [], "edges": []}
        seen = {node_id}
        frontier = {node_id}
        edges = []
        allowed = set(edge_types) if edge_types else None
        for _ in range(depth):
            nxt = set()
            for n in frontier:
                for e in self.edges_of(n):
                    if allowed and e["type"] not in allowed:
                        continue
                    edges.append(e)
                    for other in (e["src"], e["dst"]):
                        if other not in seen:
                            seen.add(other)
                            nxt.add(other)
            frontier = nxt
        # dedupe edges
        uniq, keyset = [], set()
        for e in edges:
            k = (e["src"], e["dst"], e["type"])
            if k not in keyset:
                keyset.add(k)
                uniq.append(e)
        return {"nodes": [self.node(n) for n in seen], "edges": uniq}

    def trace(self, node_id: str, edge_type: str = "FEEDS_INTO",
              direction: str = "in", depth: int = 4) -> list[dict]:
        """Walk a typed edge chain (e.g. upstream FEEDS_INTO for 'what feeds X')."""
        chain, frontier, seen = [], {node_id}, {node_id}
        for _ in range(depth):
            nxt = set()
            for n in frontier:
                for e in self.edges_of(n, edge_type=edge_type, direction=direction):
                    other = e["src"] if direction == "in" else e["dst"]
                    chain.append(e)
                    if other not in seen:
                        seen.add(other)
                        nxt.add(other)
            frontier = nxt
        return chain

    def find_equipment(self, text: str) -> list[str]:
        """Resolve equipment tags mentioned in free text (exact tag match)."""
        import re
        tags = {n for n, d in self.g.nodes(data=True) if d.get("type") == "Equipment"}
        found = []
        for tag in tags:
            if re.search(rf"\b{re.escape(tag)}\b", text, re.IGNORECASE):
                found.append(tag)
        return found

    def stats(self) -> dict:
        by_type: dict[str, int] = {}
        for _, d in self.g.nodes(data=True):
            by_type[d.get("type", "?")] = by_type.get(d.get("type", "?"), 0) + 1
        edge_types: dict[str, int] = {}
        for _, _, d in self.g.edges(data=True):
            edge_types[d.get("type", "?")] = edge_types.get(d.get("type", "?"), 0) + 1
        return {"nodes": self.g.number_of_nodes(), "edges": self.g.number_of_edges(),
                "node_types": by_type, "edge_types": edge_types}

    # -- persistence ----------------------------------------------------------
    def save(self) -> None:
        with self._lock:
            data = nx.node_link_data(self.g, edges="links")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))

    def load(self) -> None:
        data = json.loads(self.path.read_text())
        self.g = nx.node_link_graph(data, multigraph=True, directed=True, edges="links")


_instance: Optional[KnowledgeGraph] = None


def get_graph() -> KnowledgeGraph:
    global _instance
    if _instance is None:
        _instance = KnowledgeGraph()
    return _instance
