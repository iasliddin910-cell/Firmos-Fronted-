"""
OmniAgent X - Lineage Map
=========================
Track node lineage and replacements

Bu modul graph rewrite paytida node lineage'ni track qiladi.
"""

import logging
import uuid
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class LineageEventType(str, Enum):
    """Lineage event turlari"""
    REPLACE = "replace"
    SUPERSEDE = "supersede"
    CANCEL = "cancel"
    RECOVERY = "recovery"
    SPLIT = "split"
    MERGE = "merge"


@dataclass
class LineageEntry:
    """Lineage entry - bitta node o'rnini bosish"""
    entry_id: str
    original_node_id: str
    replacement_node_id: Optional[str]
    event_type: LineageEventType
    
    # Chain info
    root_original_id: str  # Original root node
    generation: int = 0    # Replacement generation
    
    # Metadata
    reason: str = ""
    triggered_by: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class LineageMap:
    """
    Lineage Map - node replacement history
    
    Bu klass:
    - eski node → qaysi yangi node bilan almashtirildi
    - replacement chain qanday
    - root goal relation saqlanyaptimi
    - descendants qayerga ko'chirildi
    """
    
    # Maps
    replaced_by: Dict[str, str] = field(default_factory=dict)       # node_id -> new_node_id
    replacement_of: Dict[str, str] = field(default_factory=dict)   # new_node_id -> original_node_id
    superseded_subtrees: Dict[str, List[str]] = field(default_factory=dict)
    
    # Root tracking
    root_origins: Dict[str, str] = field(default_factory=dict)     # current_node -> root_original
    
    # Chains
    replacement_chains: Dict[str, List[str]] = field(default_factory=dict)
    
    # Generation tracking
    generation_count: Dict[str, int] = field(default_factory=dict)
    
    def record_replacement(
        self,
        original_node_id: str,
        replacement_node_id: str,
        event_type: LineageEventType,
        reason: str = "",
        triggered_by: Optional[str] = None,
    ):
        """Replacement qayd qilish"""
        # Find root original
        root_id = self._find_root_original(original_node_id)
        
        # Update maps
        self.replaced_by[original_node_id] = replacement_node_id
        self.replacement_of[replacement_node_id] = original_node_id
        
        # Update root origin
        self.root_origins[replacement_node_id] = root_id
        
        # Update generation
        original_gen = self.generation_count.get(original_node_id, 0)
        self.generation_count[replacement_node_id] = original_gen + 1
        
        # Update chain
        if original_node_id in self.replacement_chains:
            # Extend existing chain
            old_chain = self.replacement_chains[original_node_id]
            self.replacement_chains[replacement_node_id] = old_chain + [replacement_node_id]
            del self.replacement_chains[original_node_id]
        else:
            # New chain
            self.replacement_chains[replacement_node_id] = [original_node_id, replacement_node_id]
        
        # Log
        entry = LineageEntry(
            entry_id="",
            original_node_id=original_node_id,
            replacement_node_id=replacement_node_id,
            event_type=event_type,
            root_original_id=root_id,
            generation=original_gen + 1,
            reason=reason,
            triggered_by=triggered_by,
        )
        
        logger.info(f"📜 Lineage: {original_node_id} → {replacement_node_id} ({event_type.value})")
    
    def record_cancellation(
        self,
        cancelled_node_id: str,
        subtree_nodes: List[str],
        reason: str = "",
        triggered_by: Optional[str] = None,
    ):
        """Node cancellation qayd qilish"""
        # Find root original
        root_id = self._find_root_original(cancelled_node_id)
        
        # Record as superseded
        self.superseded_subtrees[cancelled_node_id] = subtree_nodes
        
        # Mark in maps
        if cancelled_node_id not in self.replaced_by:
            self.replaced_by[cancelled_node_id] = "__cancelled__"
        
        logger.info(f"📜 Lineage: {cancelled_node_id} cancelled (subtree: {len(subtree_nodes)} nodes)")
    
    def get_replacement(self, node_id: str) -> Optional[str]:
        """Node'ning replacement'ini olish"""
        return self.replaced_by.get(node_id)
    
    def get_original(self, node_id: str) -> Optional[str]:
        """Node'ning original'ini olish"""
        return self.replacement_of.get(node_id)
    
    def get_chain(self, node_id: str) -> List[str]:
        """Replacement chain olish"""
        return self.replacement_chains.get(node_id, [node_id])
    
    def get_root_original(self, node_id: str) -> str:
        """Node'ning root original'ini olish"""
        return self._find_root_original(node_id)
    
    def is_superseded(self, node_id: str) -> bool:
        """Node superseded bo'lganmi?"""
        return node_id in self.replaced_by
    
    def is_cancelled(self, node_id: str) -> bool:
        """Node cancelled bo'lganmi?"""
        return self.replaced_by.get(node_id) == "__cancelled__"
    
    def get_all_superseded(self) -> Set[str]:
        """Barcha superseded nodlar"""
        result = set()
        for node_id, replacement in self.replaced_by.items():
            if replacement and replacement != "__cancelled__":
                result.add(node_id)
        return result
    
    def get_all_cancelled(self) -> Set[str]:
        """Barcha cancelled nodlar"""
        result = set()
        for node_id, replacement in self.replaced_by.items():
            if replacement == "__cancelled__":
                result.add(node_id)
        return result
    
    def get_active_lineage(self, node_id: str) -> List[str]:
        """Active lineage (cancelled bo'lmagan)"""
        chain = self.get_chain(node_id)
        # Filter out cancelled
        active = []
        for nid in chain:
            if not self.is_cancelled(nid):
                active.append(nid)
        return active
    
    def _find_root_original(self, node_id: str) -> str:
        """Root original'ni topish"""
        # First check if it's a replacement
        current = node_id
        visited = set()
        
        while current in self.replacement_of:
            if current in visited:
                break  # Cycle detected
            visited.add(current)
            original = self.replacement_of[current]
            if original == node_id:
                break  # Back to self
            current = original
        
        # Now traverse up the chain
        while current in self.replacement_chains:
            chain = self.replacement_chains[current]
            if not chain or chain[0] == current:
                break
            current = chain[0]
        
        return current
    
    def validate(self) -> tuple[bool, List[str]]:
        """Lineage'ni tekshirish"""
        errors = []
        
        # Check for cycles
        for node_id in self.replacement_of:
            visited = set()
            current = node_id
            while current in self.replacement_of:
                if current in visited:
                    errors.append(f"Cycle detected in lineage: {current}")
                    break
                visited.add(current)
                current = self.replacement_of[current]
        
        # Check for orphaned replacements
        for new_id, orig_id in self.replacement_of.items():
            if orig_id not in self.replaced_by:
                errors.append(f"Orphaned replacement: {new_id} -> {orig_id}")
        
        return len(errors) == 0, errors
    
    def get_summary(self) -> Dict:
        """Lineage xulosasi"""
        return {
            "total_replacements": len(self.replaced_by),
            "total_superseded": len(self.get_all_superseded()),
            "total_cancelled": len(self.get_all_cancelled()),
            "active_chains": len(self.replacement_chains),
        }


# Global lineage instance
_lineage_map: Optional[LineageMap] = None


def get_lineage_map() -> LineageMap:
    """Get or create global lineage map"""
    global _lineage_map
    if _lineage_map is None:
        _lineage_map = LineageMap()
    return _lineage_map


def reset_lineage_map():
    """Reset global lineage map"""
    global _lineage_map
    _lineage_map = None
