"""
OmniAgent X - Graph Types
========================
Graph node, edge, and related types
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set, FrozenSet
from dataclasses import dataclass, field
from datetime import datetime


class NodeStatus(str, Enum):
    """Graph node holatlari"""
    PENDING = "pending"              # Kutilmoqda
    RUNNABLE = "runnable"           # Ishga tushirish mumkin
    RUNNING = "running"             # Ishlamoqda
    COMPLETED = "completed"         # Bajarildi
    FAILED = "failed"               # Xato
    SUPERSEDED = "superseded"       # Almashtirildi (graph-level)
    REPLACED = "replaced"           # Alohida ko'rsatish uchun
    CANCELLED = "cancelled"         # Bekor qilindi
    CANCELLED_SUBTREE = "cancelled_subtree"  # Subtree bekor
    VERIFIED = "verified"           # Tekshirildi
    COMMITTED = "committed"         # Tasdiqlandi


class EdgeType(str, Enum):
    """Graph edge turlari"""
    DEPENDENCY = "dependency"       # Boshqa node kutish
    FALLBACK = "fallback"          # Xatoda alternativa
    GOAL = "goal"                  # Maqsad bog'lanishi
    APPROVAL = "approval"          # Ruxsat bog'lanishi
    SATISFACTION = "satisfaction"  # Qanoat sharti
    RECOVERY = "recovery"          # Qayta tiklanish
    REWRITE = "rewrite"            # Rewrite bog'lanishi


class RewriteKind(str, Enum):
    """Graph rewrite operation turlari"""
    REPLACE_NODE = "replace_node"          # Bitta node almashtirildi
    REPLACE_SUBTREE = "replace_subtree"    # Butun subtree almashtirildi
    SPLIT_NODE = "split_node"             # Node bo'lindi
    MERGE_NODES = "merge_nodes"            # Nodlar birlashtirildi
    CANCEL_SUBTREE = "cancel_subtree"     # Subtree bekor qilindi
    INJECT_FALLBACK = "inject_fallback"    # Fallback qo'shildi
    SIMPLIFY = "simplify"                 # Soddalashtirish
    RECOVERY = "recovery"                  # Recovery branch


class NodeType(str, Enum):
    """Node turlari"""
    ACTION = "action"
    VERIFICATION = "verification"
    GOAL = "goal"
    RECOVERY = "recovery"
    APPROVAL = "approval"


@dataclass
class GraphNode:
    """Graph node - bitta execution unit"""
    node_id: str
    task_type: str                    # "action", "verification", "goal", "recovery"
    status: NodeStatus
    
    # Task ma'lumotlari
    action: Optional[str] = None       # Amal nomi
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict] = None
    
    # Goal relation
    goal_id: Optional[str] = None      # Qaysi goal uchun
    satisfaction_condition: Optional[str] = None  # Qanoat sharti
    
    # Execution
    retry_count: int = 0
    max_retries: int = 3
    budget_ms: int = 60000            # Time budget (ms)
    execution_time_ms: float = 0.0
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Node ID'lar
    dependents: List[str] = field(default_factory=list)   # Bog'liq nodlar
    
    # Lineage
    parent_node_id: Optional[str] = None   # Parent node
    replaced_by: Optional[str] = None       # Kim almashtirirdi
    replacement_of: Optional[str] = None   # Kimning o'rniga
    
    # Approval
    approval_required: bool = False
    approval_status: Optional[str] = None
    
    # Locking
    is_locked: bool = False
    lock_holder: Optional[str] = None
    
    # Checkpoint
    checkpoint_id: Optional[str] = None
    checkpoint_valid: bool = True
    
    # Metadata
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def is_terminal(self) -> bool:
        """Terminal node-mi (children yo'q)"""
        return len(self.dependents) == 0
    
    def is_root(self) -> bool:
        """Root node-mi (parent yo'q)"""
        return self.parent_node_id is None
    
    def can_be_superseded(self) -> bool:
        """Almashtirilishi mumkinmi?"""
        return self.status not in (
            NodeStatus.VERIFIED,
            NodeStatus.COMMITTED,
            NodeStatus.RUNNING,
        )


@dataclass
class GraphEdge:
    """Graph edge - node'lar o'rtasidagi bog'lanish"""
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType
    
    # Metadata
    label: Optional[str] = None
    is_valid: bool = True           # Rewrite paytida bekor bo'lishi mumkin
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class ExecutionGraph:
    """
    Execution Graph - to'liq task graph representation
    
    Bu klass:
    - Nodlar va edge'larni saqlaydi
    - Graph invariantlarini tekshiradi
    - Rewrite operations uchun asos
    """
    
    graph_id: str
    root_goal_id: str
    
    # Nodlar va edge'lar
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: Dict[str, GraphEdge] = field(default_factory=dict)
    
    # Indexes
    _nodes_by_goal: Dict[str, List[str]] = field(default_factory=dict)
    _nodes_by_status: Dict[NodeStatus, List[str]] = field(default_factory=dict)
    _dependency_graph: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Hash for integrity
    graph_hash: str = ""
    
    def __post_init__(self):
        if not self.graph_id:
            import uuid
            self.graph_id = str(uuid.uuid4())
        self._recompute_hash()
    
    def add_node(self, node: GraphNode) -> bool:
        """Node qo'shish"""
        if node.node_id in self.nodes:
            return False
        
        self.nodes[node.node_id] = node
        
        # Update indexes
        if node.goal_id:
            if node.goal_id not in self._nodes_by_goal:
                self._nodes_by_goal[node.goal_id] = []
            self._nodes_by_goal[node.goal_id].append(node.node_id)
        
        if node.status not in self._nodes_by_status:
            self._nodes_by_status[node.status] = []
        self._nodes_by_status[node.status].append(node.node_id)
        
        self._recompute_hash()
        return True
    
    def add_edge(self, edge: GraphEdge) -> bool:
        """Edge qo'shish"""
        if edge.edge_id in self.edges:
            return False
        
        # Validate nodes exist
        if edge.source_node_id not in self.nodes:
            return False
        if edge.target_node_id not in self.nodes:
            return False
        
        self.edges[edge.edge_id] = edge
        
        # Update dependency graph
        if edge.edge_type == EdgeType.DEPENDENCY:
            if edge.target_node_id not in self._dependency_graph:
                self._dependency_graph[edge.target_node_id] = set()
            self._dependency_graph[edge.target_node_id].add(edge.source_node_id)
        
        self._recompute_hash()
        return True
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Node olish"""
        return self.nodes.get(node_id)
    
    def get_edges_from(self, node_id: str) -> List[GraphEdge]:
        """Noddan chiqadigan edge'lar"""
        return [e for e in self.edges.values() if e.source_node_id == node_id]
    
    def get_edges_to(self, node_id: str) -> List[GraphEdge]:
        """Nodga kiradigan edge'lar"""
        return [e for e in self.edges.values() if e.target_node_id == node_id]
    
    def get_dependents(self, node_id: str) -> List[str]:
        """Nodga bog'liq nodlar"""
        return [e.source_node_id for e in self.edges.values() 
                if e.target_node_id == node_id and e.edge_type == EdgeType.DEPENDENCY]
    
    def get_dependencies(self, node_id: str) -> List[str]:
        """Nod qaysi nodlarga bog'liq"""
        return [e.target_node_id for e in self.edges.values() 
                if e.source_node_id == node_id and e.edge_type == EdgeType.DEPENDENCY]
    
    def get_subtree(self, root_node_id: str) -> Set[str]:
        """Nod va uning descendants (subtree)"""
        subtree = {root_node_id}
        to_visit = [root_node_id]
        
        while to_visit:
            current = to_visit.pop()
            for dependent in self.get_dependents(current):
                if dependent not in subtree:
                    subtree.add(dependent)
                    to_visit.append(dependent)
        
        return subtree
    
    def get_subtree_roots(self, node_ids: Set[str]) -> Set[str]:
        """Berilgan set ichidagi root nodlar"""
        roots = set(node_ids)
        for node_id in node_ids:
            deps = self.get_dependencies(node_id)
            for dep in deps:
                if dep in node_ids:
                    roots.discard(node_id)
                    break
        return roots
    
    def has_cycle(self) -> bool:
        """Graphda cycle bormi?"""
        visited = set()
        rec_stack = set()
        
        def visit(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for dep in self.get_dependencies(node_id):
                if dep not in visited:
                    if visit(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if visit(node_id):
                    return True
        return False
    
    def get_runnable_nodes(self) -> List[str]:
        """Hozir ishga tushirish mumkin bo'lgan nodlar"""
        runnable = []
        
        for node_id, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue
            
            # Check if all dependencies are met
            deps = self.get_dependencies(node_id)
            all_met = True
            for dep_id in deps:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status not in (NodeStatus.COMPLETED, NodeStatus.VERIFIED, NodeStatus.COMMITTED):
                    all_met = False
                    break
            
            if all_met:
                runnable.append(node_id)
        
        return runnable
    
    def get_nodes_by_goal(self, goal_id: str) -> List[GraphNode]:
        """Goal uchun barcha nodlar"""
        node_ids = self._nodes_by_goal.get(goal_id, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]
    
    def invalidate_subtree(self, root_node_id: str):
        """Subtree'ni invalid qilish"""
        subtree = self.get_subtree(root_node_id)
        for node_id in subtree:
            node = self.nodes.get(node_id)
            if node:
                node.checkpoint_valid = False
    
    def _recompute_hash(self):
        """Graph hash hisoblash"""
        import hashlib
        content = f"{self.graph_id}:{self.root_goal_id}:"
        for node_id in sorted(self.nodes.keys()):
            node = self.nodes[node_id]
            content += f"{node_id}:{node.status.value}:"
        self.graph_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_hash(self) -> str:
        """Graph hash olish"""
        return self.graph_hash
    
    def validate(self) -> tuple[bool, List[str]]:
        """Graphni tekshirish"""
        errors = []
        
        # Check root exists
        if self.root_goal_id not in self.nodes:
            errors.append(f"Root goal {self.root_goal_id} not in graph")
        
        # Check for cycles
        if self.has_cycle():
            errors.append("Graph contains cycles")
        
        # Check for orphan nodes
        for node_id in self.nodes:
            node = self.nodes[node_id]
            if node.parent_node_id and node.parent_node_id not in self.nodes:
                errors.append(f"Orphan node: {node_id} references non-existent parent")
        
        return len(errors) == 0, errors
