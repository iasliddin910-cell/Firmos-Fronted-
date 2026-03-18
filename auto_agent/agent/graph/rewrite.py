"""
OmniAgent X - Graph Rewrite Operations
=====================================
GraphRewriteOp, GraphRewriteTransaction, RewriteLegalityChecker
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime

from agent.graph.types import (
    NodeStatus,
    EdgeType,
    RewriteKind,
    GraphNode,
    GraphEdge,
    ExecutionGraph,
)


logger = logging.getLogger(__name__)


@dataclass
class GraphRewriteOp:
    """
    Graph Rewrite Operation - typed operation
    
    Rewrite erkin if/else emas, typed operation.
    Bu kernel'ga graph surgery qilish uchun formal obyekt beradi.
    """
    op_id: str
    kind: RewriteKind
    
    # Target nodes
    target_node_ids: List[str]
    replacement_node_ids: List[str] = field(default_factory=list)
    
    # Reason and trigger
    reason: str = ""
    triggered_by: Optional[str] = None  # failure_id / handoff_id / policy_id
    
    # Metadata
    created_at: str = ""
    created_by: str = "system"
    
    def __post_init__(self):
        if not self.op_id:
            self.op_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class EdgeMigration:
    """Edge migration record"""
    original_edge_id: str
    new_edge_id: Optional[str] = None
    source_changed: bool = False
    target_changed: bool = False
    is_cancelled: bool = False


@dataclass
class BudgetMigration:
    """Budget migration during rewrite"""
    original_node_id: str
    new_node_id: str
    budget_transferred_ms: int = 0
    retry_count_transferred: int = 0


@dataclass
class GraphRewriteTransaction:
    """
    Graph Rewrite Transaction - atomic rewrite
    
    Rewrite bitta atomic operatsiya bo'lishi kerak.
    Agar rewrite yarim yo'da qolsa, graph buzilmasligi kerak.
    """
    tx_id: str
    op: GraphRewriteOp
    
    # Graph state
    pre_graph_hash: str
    post_graph_hash: Optional[str] = None
    
    # Migration records
    migrated_edges: List[EdgeMigration] = field(default_factory=list)
    superseded_nodes: List[str] = field(default_factory=list)
    cancelled_nodes: List[str] = field(default_factory=list)
    lineage_updates: Dict[str, str] = field(default_factory=dict)  # old_id -> new_id
    
    # Budget migrations
    budget_migrations: List[BudgetMigration] = field(default_factory=list)
    
    # Status
    status: str = "pending"  # pending, applied, rolled_back, failed
    error: Optional[str] = None
    
    # Timestamps
    created_at: str = ""
    applied_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.tx_id:
            self.tx_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class RewriteLegalityResult:
    """Rewrite legality check result"""
    is_legal: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Migration hints
    can_migrate_budget: bool = True
    can_migrate_locks: bool = True
    can_migrate_checkpoints: bool = True
    approval_impact: str = "none"


class RewriteLegalityChecker:
    """
    Rewrite Legality Checker - pre-rewrite validation
    
    Har rewrite oldidan tekshiradi:
    - node committed emasmi
    - descendants bilan conflict yo'qmi
    - active locks bormi
    - approval lineage yo'qolmayaptimi
    - goal mapping buzilmayaptimi
    - dependency cycle paydo bo'lmayaptimi
    - budget accounting qonuni saqlanadimi
    """
    
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph
    
    def check_rewrite_legality(
        self,
        op: GraphRewriteOp,
    ) -> RewriteLegalityResult:
        """Rewrite qonuniy-yo'qligini tekshirish"""
        violations = []
        warnings = []
        
        # Check each target node
        for node_id in op.target_node_ids:
            node = self.graph.get_node(node_id)
            if not node:
                violations.append(f"Target node {node_id} not found")
                continue
            
            # 1. Check if node is committed/verified (cannot rewrite)
            if node.status in (NodeStatus.VERIFIED, NodeStatus.COMMITTED):
                violations.append(
                    f"Cannot rewrite {node_id}: status is {node.status.value}"
                )
            
            # 2. Check for active locks
            if node.is_locked:
                violations.append(
                    f"Cannot rewrite {node_id}: node is locked by {node.lock_holder}"
                )
            
            # 3. Check if approval is pending
            if node.approval_required and node.approval_status == "pending":
                warnings.append(
                    f"Rewriting {node_id} will invalidate pending approval"
                )
        
        # 4. Check for descendant conflicts
        if op.kind in (RewriteKind.REPLACE_SUBTREE, RewriteKind.CANCEL_SUBTREE):
            for node_id in op.target_node_ids:
                subtree = self.graph.get_subtree(node_id)
                for sub_id in subtree:
                    sub_node = self.graph.get_node(sub_id)
                    if sub_node and sub_node.status == NodeStatus.COMMITTED:
                        violations.append(
                            f"Cannot cancel subtree: descendant {sub_id} is committed"
                        )
        
        # 5. Check for dependency cycles after rewrite
        if op.replacement_node_ids:
            # Check if new nodes would create cycles
            for new_id in op.replacement_node_ids:
                for target_id in op.target_node_ids:
                    deps = self.graph.get_dependencies(target_id)
                    if new_id in deps:
                        warnings.append(
                            f"Replacement {new_id} depends on target - may cause cycle"
                        )
        
        # 6. Check goal mapping
        if op.kind in (RewriteKind.REPLACE_NODE, RewriteKind.REPLACE_SUBTREE):
            for node_id in op.target_node_ids:
                node = self.graph.get_node(node_id)
                if node and node.goal_id:
                    if not op.replacement_node_ids:
                        violations.append(
                            f"Replacing goal-related node {node_id} without replacement"
                        )
        
        # 7. Budget/Lock/Checkpoint migration checks
        can_migrate_budget = True
        can_migrate_locks = True
        can_migrate_checkpoints = True
        
        for node_id in op.target_node_ids:
            node = self.graph.get_node(node_id)
            if node:
                if node.is_locked:
                    can_migrate_locks = False
                if node.checkpoint_id:
                    can_migrate_checkpoints = False
        
        # Build result
        is_legal = len(violations) == 0
        
        return RewriteLegalityResult(
            is_legal=is_legal,
            violations=violations,
            warnings=warnings,
            can_migrate_budget=can_migrate_budget,
            can_migrate_locks=can_migrate_locks,
            can_migrate_checkpoints=can_migrate_checkpoints,
            approval_impact="warning" if warnings else "none",
        )
    
    def check_subtree_cancellation_legality(
        self,
        root_node_id: str,
    ) -> RewriteLegalityResult:
        """Subtree cancellation qonuniy-yo'qligini tekshirish"""
        violations = []
        warnings = []
        
        subtree = self.graph.get_subtree(root_node_id)
        
        for node_id in subtree:
            node = self.graph.get_node(node_id)
            if not node:
                continue
            
            # Check locked nodes
            if node.is_locked:
                violations.append(
                    f"Cannot cancel: descendant {node_id} is locked"
                )
            
            # Check committed nodes
            if node.status == NodeStatus.COMMITTED:
                violations.append(
                    f"Cannot cancel: descendant {node_id} is committed"
                )
            
            # Check verified nodes
            if node.status == NodeStatus.VERIFIED:
                violations.append(
                    f"Cannot cancel: descendant {node_id} is verified"
                )
            
            # Check pending approvals
            if node.approval_required and node.approval_status == "pending":
                warnings.append(
                    f"Cancelling {node_id} will invalidate pending approval"
                )
        
        return RewriteLegalityResult(
            is_legal=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )


def check_rewrite_legality(
    graph: ExecutionGraph,
    op: GraphRewriteOp,
) -> RewriteLegalityResult:
    """Helper function for legality check"""
    checker = RewriteLegalityChecker(graph)
    return checker.check_rewrite_legality(op)


@dataclass
class RewriteResult:
    """Rewrite operation natijasi"""
    success: bool
    transaction: Optional[GraphRewriteTransaction] = None
    error: Optional[str] = None
    
    # New graph state
    new_graph: Optional[ExecutionGraph] = None
    
    # Summary
    nodes_superseded: int = 0
    nodes_cancelled: int = 0
    edges_migrated: int = 0
    budget_transferred_ms: int = 0
