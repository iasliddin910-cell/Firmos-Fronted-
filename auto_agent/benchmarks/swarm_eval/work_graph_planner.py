"""
WorkGraphPlanner - DAG Task Decomposition

Bu modul taskni DAG-contract ko'rinishida bo'ladi.

Har node'da:
- owner worker
- input contract
- output artifact
- dependency list
- timeout
- verifier
- fallback path

Policy 4: Near-frontier zone benchmarkning eng qimmat qismi.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time


class ContractType(Enum):
    """Type of artifact contract"""
    CODE_PATCH = "code_patch"
    ANALYSIS_REPORT = "analysis_report"
    TEST_RESULT = "test_result"
    TOOL_DEFINITION = "tool_definition"
    PLAN_DOCUMENT = "plan_document"
    VERIFICATION_REPORT = "verification_report"


@dataclass
class ArtifactContract:
    """Contract for expected artifact"""
    contract_type: ContractType
    description: str
    schema: Optional[Dict[str, Any]] = None
    required_fields: List[str] = field(default_factory=list)


@dataclass
class NodeDependency:
    """Dependency specification for a node"""
    depends_on: str
    required_artifact: str
    usage: str  # How the artifact is used


class WorkGraphPlanner:
    """
    Plans tasks into DAG-structured work graphs.
    
    Har node uchun aniq:
    - Kim egalik qiladi
    - Nimani input qiladi
    - Nimani output qiladi
    - Qanday dependencylar bor
    - Timeout qancha
    - Verifier kim
    - Fallback yo'li qayerda
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.planning_templates: Dict[str, Any] = {}
        
    def plan_task(
        self,
        task_description: str,
        available_roles: List[str],
        constraints: Optional[Dict[str, Any]] = None
    ) -> WorkGraph:
        """
        Plan a task into DAG work graph.
        
        Args:
            task_description: Description of the task
            available_roles: Available worker roles
            constraints: Planning constraints
            
        Returns:
            WorkGraph with nodes and edges
        """
        constraints = constraints or {}
        
        graph_id = f"graph_{uuid.uuid4().hex[:8]}"
        
        # Analyze task type and create appropriate nodes
        nodes = {}
        edges = []
        
        # Detect task type and plan accordingly
        if "research" in task_description.lower() and "patch" in task_description.lower():
            nodes, edges = self._plan_research_patch_verify(task_description, available_roles)
        elif "parallel" in task_description.lower() or "branch" in task_description.lower():
            nodes, edges = self._plan_multi_branch(task_description, available_roles)
        elif "merge" in task_description.lower() or "conflict" in task_description.lower():
            nodes, edges = self._plan_merge_conflict(task_description, available_roles)
        elif "tool" in task_description.lower() and "build" in task_description.lower():
            nodes, edges = self._plan_tool_build_use(task_description, available_roles)
        else:
            # Default: simple pipeline
            nodes, edges = self._plan_simple_pipeline(task_description, available_roles)
        
        return WorkGraph(
            graph_id=graph_id,
            task_id=task_description[:50],
            nodes=nodes,
            edges=edges,
            created_at=time.time()
        )
    
    def _plan_research_patch_verify(
        self,
        task: str,
        roles: List[str]
    ) -> Tuple[Dict[str, WorkNode], List[Tuple[str, str]]]:
        """Plan research -> patch -> verify pipeline"""
        nodes = {}
        edges = []
        
        # Research node
        research_id = "node_research"
        nodes[research_id] = WorkNode(
            node_id=research_id,
            task="Research and analyze the problem",
            owner_role=WorkerRole.RESEARCHER,
            inputs=[],
            outputs=["analysis_report"],
            dependencies=[],
            timeout=120.0,
            artifact_contract=ArtifactContract(
                contract_type=ContractType.ANALYSIS_REPORT,
                description="Detailed analysis of the problem",
                required_fields=["root_cause", "affected_files", "severity"]
            ).__dict__
        )
        
        # Patch design node
        design_id = "node_patch_design"
        nodes[design_id] = WorkNode(
            node_id=design_id,
            task="Design patch approach",
            owner_role=WorkerRole.PLANNER,
            inputs=["analysis_report"],
            outputs=["patch_plan"],
            dependencies=[research_id],
            timeout=60.0,
            artifact_contract=ArtifactContract(
                contract_type=ContractType.PLAN_DOCUMENT,
                description="Patch design document",
                required_fields=["approach", "files_affected", "risks"]
            ).__dict__
        )
        
        # Patch implementation node
        patch_id = "node_patch"
        nodes[patch_id] = WorkNode(
            node_id=patch_id,
            task="Implement the patch",
            owner_role=WorkerRole.EXECUTOR,
            inputs=["patch_plan"],
            outputs=["code_patch"],
            dependencies=[design_id],
            timeout=300.0,
            artifact_contract=ArtifactContract(
                contract_type=ContractType.CODE_PATCH,
                description="Code changes to fix the issue",
                required_fields=["files", "diffs", "tests_added"]
            ).__dict__
        )
        
        # Verify node
        verify_id = "node_verify"
        nodes[verify_id] = WorkNode(
            node_id=verify_id,
            task="Verify the fix",
            owner_role=WorkerRole.VERIFIER,
            inputs=["code_patch"],
            outputs=["verification_report"],
            dependencies=[patch_id],
            timeout=120.0,
            artifact_contract=ArtifactContract(
                contract_type=ContractType.VERIFICATION_REPORT,
                description="Verification results",
                required_fields=["tests_passed", "coverage", "regression_check"]
            ).__dict__,
            fallback_path=patch_id
        )
        
        edges = [
            (research_id, design_id),
            (design_id, patch_id),
            (patch_id, verify_id)
        ]
        
        return nodes, edges
    
    def _plan_multi_branch(
        self,
        task: str,
        roles: List[str]
    ) -> Tuple[Dict[str, WorkNode], List[Tuple[str, str]]]:
        """Plan multi-branch parallel execution"""
        nodes = {}
        edges = []
        
        # Planner node
        plan_id = "node_plan"
        nodes[plan_id] = WorkNode(
            node_id=plan_id,
            task="Create execution plan with multiple branches",
            owner_role=WorkerRole.PLANNER,
            inputs=[],
            outputs=["execution_plan"],
            dependencies=[],
            timeout=60.0
        )
        
        # Create parallel branches
        branch_count = 3
        branch_ids = []
        
        for i in range(branch_count):
            branch_id = f"node_branch_{i}"
            branch_ids.append(branch_id)
            
            nodes[branch_id] = WorkNode(
                node_id=branch_id,
                task=f"Execute branch {i}",
                owner_role=WorkerRole.EXECUTOR,
                inputs=["execution_plan"],
                outputs=[f"branch_result_{i}"],
                dependencies=[plan_id],
                timeout=180.0
            )
            
            edges.append((plan_id, branch_id))
        
        # Merge node
        merge_id = "node_merge"
        nodes[merge_id] = WorkNode(
            node_id=merge_id,
            task="Merge branch results",
            owner_role=WorkerRole.MERGER,
            inputs=[f"branch_result_{i}" for i in range(branch_count)],
            outputs=["merged_result"],
            dependencies=branch_ids,
            timeout=60.0
        )
        
        for branch_id in branch_ids:
            edges.append((branch_id, merge_id))
        
        # Verify
        verify_id = "node_verify"
        nodes[verify_id] = WorkNode(
            node_id=verify_id,
            task="Verify merged result",
            owner_role=WorkerRole.VERIFIER,
            inputs=["merged_result"],
            outputs=["verification_report"],
            dependencies=[merge_id],
            timeout=120.0,
            fallback_path=merge_id
        )
        
        edges.append((merge_id, verify_id))
        
        return nodes, edges
    
    def _plan_merge_conflict(
        self,
        task: str,
        roles: List[str]
    ) -> Tuple[Dict[str, WorkNode], List[Tuple[str, str]]]:
        """Plan merge conflict resolution"""
        nodes = {}
        edges = []
        
        # Analyze conflicts
        analyze_id = "node_analyze"
        nodes[analyze_id] = WorkNode(
            node_id=analyze_id,
            task="Analyze merge conflicts",
            owner_role=WorkerRole.RESEARCHER,
            inputs=[],
            outputs=["conflict_analysis"],
            dependencies=[],
            timeout=60.0
        )
        
        # Resolve
        resolve_id = "node_resolve"
        nodes[resolve_id] = WorkNode(
            node_id=resolve_id,
            task="Resolve conflicts",
            owner_role=WorkerRole.MERGER,
            inputs=["conflict_analysis"],
            outputs=["resolved_code"],
            dependencies=[analyze_id],
            timeout=120.0
        )
        
        edges = [(analyze_id, resolve_id)]
        
        # Verify
        verify_id = "node_verify"
        nodes[verify_id] = WorkNode(
            node_id=verify_id,
            task="Verify resolution",
            owner_role=WorkerRole.VERIFIER,
            inputs=["resolved_code"],
            outputs=["verification_report"],
            dependencies=[resolve_id],
            timeout=60.0
        )
        
        edges.append((resolve_id, verify_id))
        
        return nodes, edges
    
    def _plan_tool_build_use(
        self,
        task: str,
        roles: List[str]
    ) -> Tuple[Dict[str, WorkNode], List[Tuple[str, str]]]:
        """Plan tool building and usage"""
        nodes = {}
        edges = []
        
        # Tool builder
        build_id = "node_build_tool"
        nodes[build_id] = WorkNode(
            node_id=build_id,
            task="Build required tool",
            owner_role=WorkerRole.TOOL_BUILDER,
            inputs=[],
            outputs=["tool_definition"],
            dependencies=[],
            timeout=180.0,
            artifact_contract=ArtifactContract(
                contract_type=ContractType.TOOL_DEFINITION,
                description="Tool implementation",
                required_fields=["name", "description", "implementation"]
            ).__dict__
        )
        
        # Use tool
        use_id = "node_use_tool"
        nodes[use_id] = WorkNode(
            node_id=use_id,
            task="Use tool to accomplish task",
            owner_role=WorkerRole.EXECUTOR,
            inputs=["tool_definition"],
            outputs=["tool_result"],
            dependencies=[build_id],
            timeout=120.0
        )
        
        edges = [(build_id, use_id)]
        
        return nodes, edges
    
    def _plan_simple_pipeline(
        self,
        task: str,
        roles: List[str]
    ) -> Tuple[Dict[str, WorkNode], List[Tuple[str, str]]]:
        """Plan simple single-worker pipeline"""
        nodes = {}
        edges = []
        
        # Execute
        exec_id = "node_execute"
        nodes[exec_id] = WorkNode(
            node_id=exec_id,
            task=task,
            owner_role=WorkerRole.EXECUTOR,
            inputs=[],
            outputs=["result"],
            dependencies=[],
            timeout=300.0
        )
        
        # Verify
        verify_id = "node_verify"
        nodes[verify_id] = WorkNode(
            node_id=verify_id,
            task="Verify result",
            owner_role=WorkerRole.VERIFIER,
            inputs=["result"],
            outputs=["verification_report"],
            dependencies=[exec_id],
            timeout=60.0
        )
        
        edges = [(exec_id, verify_id)]
        
        return nodes, edges
    
    def validate_graph(self, graph: WorkGraph) -> Tuple[bool, List[str]]:
        """
        Validate work graph for correctness.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Check for cycles
        if self._has_cycle(graph):
            errors.append("Graph contains cycles - must be DAG")
        
        # Check all dependencies exist
        for node_id, node in graph.nodes.items():
            for dep in node.dependencies:
                if dep not in graph.nodes:
                    errors.append(f"Node {node_id} depends on non-existent node {dep}")
        
        # Check all nodes have owners
        for node_id, node in graph.nodes.items():
            if not node.owner_role:
                errors.append(f"Node {node_id} has no owner role assigned")
        
        # Check for orphaned nodes (not reachable from anywhere)
        reachable = set()
        for edge in graph.edges:
            reachable.add(edge[0])
            reachable.add(edge[1])
        
        for node_id in graph.nodes:
            if node_id not in reachable and graph.nodes[node_id].dependencies:
                pass  # Has dependencies so is reachable
            elif node_id not in reachable:
                errors.append(f"Node {node_id} is orphaned")
        
        return len(errors) == 0, errors
    
    def _has_cycle(self, graph: WorkGraph) -> bool:
        """Check if graph has cycles"""
        visited = set()
        rec_stack = set()
        
        def visit(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for edge in graph.edges:
                if edge[0] == node_id:
                    if edge[1] not in visited:
                        if visit(edge[1]):
                            return True
                    elif edge[1] in rec_stack:
                        return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in graph.nodes:
            if node_id not in visited:
                if visit(node_id):
                    return True
        return False
    
    def estimate_parallelism(self, graph: WorkGraph) -> Dict[str, float]:
        """
        Estimate parallelism metrics for the graph.
        
        Returns:
            Dictionary with parallelism metrics
        """
        if not graph.nodes:
            return {"max_parallel": 0, "avg_parallel": 0, "critical_path_length": 0}
        
        # Calculate levels (like topological sort by distance)
        levels = {}
        
        for node_id in graph.nodes:
            deps = graph.nodes[node_id].dependencies
            if not deps:
                levels[node_id] = 0
            else:
                levels[node_id] = max(levels.get(d, 0) for d in deps) + 1
        
        # Count nodes at each level
        level_counts = {}
        for node_id, level in levels.items():
            level_counts[level] = level_counts.get(level, 0) + 1
        
        max_parallel = max(level_counts.values()) if level_counts else 0
        avg_parallel = sum(level_counts.values()) / len(level_counts) if level_counts else 0
        
        # Critical path length
        critical_path_length = max(levels.values()) if levels else 0
        
        return {
            "max_parallel": max_parallel,
            "avg_parallel": avg_parallel,
            "critical_path_length": critical_path_length,
            "total_nodes": len(graph.nodes)
        }


# Import WorkerRole from swarm_benchmark
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from swarm_benchmark import WorkerRole
except ImportError:
    # Fallback if not available
    from enum import Enum
    class WorkerRole(Enum):
        PLANNER = "planner"
        EXECUTOR = "executor"
        VERIFIER = "verifier"
        CRITIC = "critic"
        RESEARCHER = "researcher"
        TOOL_BUILDER = "tool_builder"
        COORDINATOR = "coordinator"
        MERGER = "merger"

__all__ = [
    'WorkGraphPlanner',
    'ContractType',
    'ArtifactContract',
    'NodeDependency'
]
