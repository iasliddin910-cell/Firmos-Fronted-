"""
OmniAgent X - Graph Rewrite Provenance
=====================================
Rewrite provenance ledger

Bu modul rewrite eventlarini log qiladi.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict


logger = logging.getLogger(__name__)


class ProvenanceEvent(str, Enum):
    """Provenance event turlari"""
    REWRITE_REQUESTED = "graph_rewrite_requested"
    REWRITE_LEGAL = "graph_rewrite_legal"
    REWRITE_REJECTED = "graph_rewrite_rejected"
    REWRITE_APPLIED = "graph_rewrite_applied"
    LINEAGE_UPDATED = "lineage_updated"
    SUBTREE_CANCELLED = "subtree_cancelled"
    NODE_SUPERSEDED = "node_superseded"
    EDGE_MIGRATED = "edge_migrated"
    BUDGET_MIGRATED = "budget_migrated"


@dataclass
class ProvenanceEntry:
    """Provenance entry"""
    event_id: str
    event_type: ProvenanceEvent
    
    # Graph state
    graph_id: str
    graph_hash: str
    
    # Rewrite info
    tx_id: Optional[str] = None
    op_id: Optional[str] = None
    rewrite_kind: Optional[str] = None
    
    # Node info
    target_nodes: List[str] = field(default_factory=list)
    replacement_nodes: List[str] = field(default_factory=list)
    cancelled_nodes: List[str] = field(default_factory=list)
    
    # Reason
    reason: str = ""
    triggered_by: Optional[str] = None
    
    # Result
    success: bool = True
    error: Optional[str] = None
    
    # Metadata
    timestamp: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class GraphRewriteProvenance:
    """
    Graph Rewrite Provenance - rewrite event ledger
    
    Bu klass:
    - Rewrite eventlarini log qiladi
    - Analytics uchun data to'playdi
    - Audit trail taqdim etadi
    """
    
    def __init__(self):
        self._entries: List[ProvenanceEntry] = []
        self._events_by_graph: Dict[str, List[str]] = defaultdict(list)
        self._events_by_type: Dict[ProvenanceEvent, List[str]] = defaultdict(list)
        
        # Stats
        self._stats: Dict[str, int] = defaultdict(int)
    
    def log_event(
        self,
        event_type: ProvenanceEvent,
        graph_id: str,
        graph_hash: str,
        tx_id: Optional[str] = None,
        op_id: Optional[str] = None,
        rewrite_kind: Optional[str] = None,
        target_nodes: Optional[List[str]] = None,
        replacement_nodes: Optional[List[str]] = None,
        cancelled_nodes: Optional[List[str]] = None,
        reason: str = "",
        triggered_by: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ProvenanceEntry:
        """Event log qilish"""
        import uuid
        
        entry = ProvenanceEntry(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            graph_id=graph_id,
            graph_hash=graph_hash,
            tx_id=tx_id,
            op_id=op_id,
            rewrite_kind=rewrite_kind,
            target_nodes=target_nodes or [],
            replacement_nodes=replacement_nodes or [],
            cancelled_nodes=cancelled_nodes or [],
            reason=reason,
            triggered_by=triggered_by,
            success=success,
            error=error,
            details=details or {},
        )
        
        self._entries.append(entry)
        self._events_by_graph[graph_id].append(entry.event_id)
        self._events_by_type[event_type].append(entry.event_id)
        
        # Update stats
        self._stats[f"total_{event_type.value}"] += 1
        if success:
            self._stats[f"success_{event_type.value}"] += 1
        else:
            self._stats[f"failed_{event_type.value}"] += 1
        
        logger.info(f"📋 Provenance: {event_type.value} - {graph_id[:8]}...")
        
        return entry
    
    def get_events(
        self,
        graph_id: Optional[str] = None,
        event_type: Optional[ProvenanceEvent] = None,
        limit: int = 100,
    ) -> List[ProvenanceEntry]:
        """Eventlarni olish"""
        events = self._entries
        
        if graph_id:
            event_ids = self._events_by_graph.get(graph_id, [])
            events = [e for e in events if e.event_id in event_ids]
        
        if event_type:
            event_ids = self._events_by_type.get(event_type, [])
            events = [e for e in events if e.event_id in event_ids]
        
        # Sort by timestamp descending
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        
        return events[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistikani olish"""
        return dict(self._stats)
    
    def get_rewrite_summary(self, graph_id: str) -> Dict[str, Any]:
        """Graph uchun rewrite xulosasi"""
        events = self.get_events(graph_id=graph_id)
        
        total = len(events)
        applied = len([e for e in events if e.event_type == ProvenanceEvent.REWRITE_APPLIED])
        rejected = len([e for e in events if e.event_type == ProvenanceEvent.REWRITE_REJECTED])
        
        # Most common rewrite kinds
        kinds = defaultdict(int)
        for e in events:
            if e.rewrite_kind:
                kinds[e.rewrite_kind] += 1
        
        return {
            "graph_id": graph_id,
            "total_events": total,
            "rewrites_applied": applied,
            "rewrites_rejected": rejected,
            "success_rate": applied / total if total > 0 else 0,
            "rewrite_kinds": dict(kinds),
        }
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """Xato analizi"""
        failed_events = [e for e in self._entries if not e.success]
        
        by_reason = defaultdict(int)
        by_kind = defaultdict(int)
        
        for e in failed_events:
            if e.error:
                by_reason[e.error[:50]] += 1
            if e.rewrite_kind:
                by_kind[e.rewrite_kind] += 1
        
        return {
            "total_failures": len(failed_events),
            "by_error": dict(by_reason),
            "by_rewrite_kind": dict(by_kind),
        }
    
    def export_ledger(self, filepath: str):
        """Ledger'ni faylga export qilish"""
        data = [
            asdict(e) for e in self._entries
        ]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"📋 Exported {len(data)} entries to {filepath}")


# Global provenance instance
_provenance: Optional[GraphRewriteProvenance] = None


def log_rewrite_event(
    event_type: ProvenanceEvent,
    graph_id: str,
    graph_hash: str,
    **kwargs
) -> ProvenanceEntry:
    """Helper function to log events"""
    global _provenance
    if _provenance is None:
        _provenance = GraphRewriteProvenance()
    return _provenance.log_event(event_type, graph_id, graph_hash, **kwargs)


def get_provenance() -> GraphRewriteProvenance:
    """Get or create global provenance"""
    global _provenance
    if _provenance is None:
        _provenance = GraphRewriteProvenance()
    return _provenance
