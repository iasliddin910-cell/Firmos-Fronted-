"""
SwarmBenchmarkSuite - Multi-Agent Benchmark Framework

Bu module multi-agent tizimlarni baholash uchun maxsus benchmark suite.

Task oilalari:
- parallel repo diagnosis
- split research + patch + verify
- multi-branch feature implementation
- merge conflict resolution
- failing worker replacement
- tool built by worker A, used by worker B
- critic/verifier disagreement resolution

Policy 1: Multi-agent claim evalsiz qabul qilinmaydi.
Policy 2: Parallel run single-agent baseline bilan solishtiriladi.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time
import json


class WorkerRole(Enum):
    """Multi-agent worker rollari"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    CRITIC = "critic"
    RESEARCHER = "researcher"
    TOOL_BUILDER = "tool_builder"
    COORDINATOR = "coordinator"
    MERGER = "merger"


class TaskType(Enum):
    """Multi-agent task turlari"""
    PARALLEL_REPO_DIAGNOSIS = "parallel_repo_diagnosis"
    SPLIT_RESEARCH_PATCH_VERIFY = "split_research_patch_verify"
    MULTI_BRANCH_FEATURE = "multi_branch_feature"
    MERGE_CONFLICT_RESOLUTION = "merge_conflict_resolution"
    FAILING_WORKER_REPLACEMENT = "failing_worker_replacement"
    TOOL_BUILD_AND_USE = "tool_build_and_use"
    CRITIC_VERIFIER_DISAGREEMENT = "critic_verifier_disagreement"
    PARALLEL_PATCH_DESIGN = "parallel_patch_design"


class EvaluationMetric(Enum):
    """Evaluation metrics"""
    DECOMPOSITION_QUALITY = "decomposition_quality"
    DEPENDENCY_GRAPH_QUALITY = "dependency_graph_quality"
    PARALLEL_SPEEDUP = "parallel_speedup"
    MERGE_CORRECTNESS = "merge_correctness"
    DUPLICATE_WORK_RATE = "duplicate_work_rate"
    PARTIAL_FAILURE_RECOVERY = "partial_failure_recovery"
    ROLE_ROUTING_QUALITY = "role_routing_quality"
    COMMUNICATION_DISCIPLINE = "communication_discipline"
    ARBITRATION_CORRECTNESS = "arbitration_correctness"
    NET_PARALLEL_GAIN = "net_parallel_gain"


@dataclass
class WorkNode:
    """DAG node for work decomposition"""
    node_id: str
    task: str
    owner_role: WorkerRole
    owner_id: Optional[str] = None
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    timeout: float = 60.0
    artifact_contract: Optional[Dict[str, Any]] = None
    fallback_path: Optional[str] = None
    status: str = "pending"


@dataclass
class WorkGraph:
    """Complete work decomposition graph"""
    graph_id: str
    task_id: str
    nodes: Dict[str, WorkNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class WorkerExecution:
    """Single worker execution trace"""
    worker_id: str
    role: WorkerRole
    node_id: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    messages_sent: int = 0
    messages_received: int = 0


@dataclass
class MultiAgentResult:
    """Result of multi-agent execution"""
    task_id: str
    success: bool
    duration: float
    workers_used: List[str]
    work_graph: Optional[WorkGraph]
    executions: List[WorkerExecution]
    merged_outputs: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class SwarmBenchmarkTask:
    """A benchmark task for multi-agent evaluation"""
    task_id: str
    task_type: TaskType
    description: str
    difficulty: float
    expected_roles: List[WorkerRole]
    parallel_branches_expected: int
    success_criteria: List[str]
    baseline_single_agent_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SwarmBenchmarkSuite:
    """
    Multi-agent benchmark suite for evaluating parallel/cooperative systems.
    """
    
    TASK_TEMPLATES = {
        TaskType.PARALLEL_REPO_DIAGNOSIS: {
            "description": "Parallel repo diagnosis with multiple workers",
            "roles": [WorkerRole.RESEARCHER, WorkerRole.EXECUTOR],
            "branches": 3,
            "difficulty": 0.5
        },
        TaskType.SPLIT_RESEARCH_PATCH_VERIFY: {
            "description": "Split research + patch + verify pipeline",
            "roles": [WorkerRole.RESEARCHER, WorkerRole.EXECUTOR, WorkerRole.VERIFIER],
            "branches": 3,
            "difficulty": 0.6
        },
        TaskType.MULTI_BRANCH_FEATURE: {
            "description": "Multi-branch feature implementation",
            "roles": [WorkerRole.PLANNER, WorkerRole.EXECUTOR, WorkerRole.VERIFIER, WorkerRole.MERGER],
            "branches": 4,
            "difficulty": 0.7
        },
        TaskType.MERGE_CONFLICT_RESOLUTION: {
            "description": "Merge conflict resolution",
            "roles": [WorkerRole.MERGER, WorkerRole.CRITIC, WorkerRole.VERIFIER],
            "branches": 2,
            "difficulty": 0.65
        },
        TaskType.FAILING_WORKER_REPLACEMENT: {
            "description": "Failing worker replacement scenario",
            "roles": [WorkerRole.COORDINATOR, WorkerRole.EXECUTOR, WorkerRole.VERIFIER],
            "branches": 2,
            "difficulty": 0.55
        },
        TaskType.TOOL_BUILD_AND_USE: {
            "description": "Tool built by worker A, used by worker B",
            "roles": [WorkerRole.TOOL_BUILDER, WorkerRole.EXECUTOR],
            "branches": 2,
            "difficulty": 0.5
        },
        TaskType.CRITIC_VERIFIER_DISAGREEMENT: {
            "description": "Critic/verifier disagreement resolution",
            "roles": [WorkerRole.CRITIC, WorkerRole.VERIFIER, WorkerRole.COORDINATOR],
            "branches": 2,
            "difficulty": 0.6
        },
        TaskType.PARALLEL_PATCH_DESIGN: {
            "description": "Parallel patch design with multiple approaches",
            "roles": [WorkerRole.PLANNER, WorkerRole.EXECUTOR, WorkerRole.CRITIC],
            "branches": 3,
            "difficulty": 0.7
        }
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.tasks: Dict[str, SwarmBenchmarkTask] = {}
        self.results: List[MultiAgentResult] = []
        self.baseline_results: Dict[str, float] = {}
        
    def register_task(self, task: SwarmBenchmarkTask) -> None:
        self.tasks[task.task_id] = task
    
    def create_task(
        self,
        task_type: TaskType,
        task_id: Optional[str] = None,
        difficulty: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SwarmBenchmarkTask:
        template = self.TASK_TEMPLATES[task_type]
        
        if task_id is None:
            task_id = f"swarm_{task_type.value}_{int(time.time())}"
        
        task = SwarmBenchmarkTask(
            task_id=task_id,
            task_type=task_type,
            description=template["description"],
            difficulty=difficulty or template["difficulty"],
            expected_roles=template["roles"],
            parallel_branches_expected=template["branches"],
            success_criteria=self._get_success_criteria(task_type),
            metadata=metadata or {}
        )
        
        self.register_task(task)
        return task
    
    def _get_success_criteria(self, task_type: TaskType) -> List[str]:
        criteria = {
            TaskType.PARALLEL_REPO_DIAGNOSIS: [
                "All diagnosis branches completed",
                "Results merged correctly",
                "No duplicate work"
            ],
            TaskType.SPLIT_RESEARCH_PATCH_VERIFY: [
                "Research completed before patch",
                "Patch completed before verify",
                "Final verification passed"
            ],
            TaskType.MERGE_CONFLICT_RESOLUTION: [
                "Conflicts identified",
                "Correct resolution",
                "No regression"
            ],
            TaskType.FAILING_WORKER_REPLACEMENT: [
                "Failure detected",
                "Worker replaced",
                "Task completed"
            ]
        }
        return criteria.get(task_type, ["Task completed successfully"])
    
    def set_baseline(self, task_id: str, single_agent_time: float) -> None:
        self.baseline_results[task_id] = single_agent_time
    
    def evaluate_result(
        self,
        result: MultiAgentResult,
        task: Optional[SwarmBenchmarkTask] = None
    ) -> Dict[str, float]:
        metrics = {}
        
        if task and result.work_graph:
            metrics[EvaluationMetric.DECOMPOSITION_QUALITY.value] = self._evaluate_decomposition(
                result.work_graph, task
            )
            metrics[EvaluationMetric.DEPENDENCY_GRAPH_QUALITY.value] = self._evaluate_dependency_graph(
                result.work_graph
            )
            
            if task.task_id in self.baseline_results:
                baseline = self.baseline_results[task.task_id]
                metrics[EvaluationMetric.PARALLEL_SPEEDUP.value] = self._calculate_speedup(
                    result.duration, baseline
                )
            
            metrics[EvaluationMetric.MERGE_CORRECTNESS.value] = self._evaluate_merge_correctness(result)
            metrics[EvaluationMetric.ROLE_ROUTING_QUALITY.value] = self._evaluate_role_routing(result, task)
        
        metrics[EvaluationMetric.DUPLICATE_WORK_RATE.value] = self._calculate_duplicate_rate(result)
        metrics[EvaluationMetric.PARTIAL_FAILURE_RECOVERY.value] = self._evaluate_recovery(result)
        metrics[EvaluationMetric.COMMUNICATION_DISCIPLINE.value] = self._evaluate_communication(result)
        metrics[EvaluationMetric.NET_PARALLEL_GAIN.value] = self._calculate_net_gain(result, task)
        
        return metrics
    
    def _evaluate_decomposition(self, graph: WorkGraph, task: SwarmBenchmarkTask) -> float:
        score = 0.0
        
        used_roles = set(node.owner_role for node in graph.nodes.values())
        expected_roles = set(task.expected_roles)
        
        role_coverage = len(used_roles & expected_roles) / len(expected_roles) if expected_roles else 0
        score += role_coverage * 0.4
        
        well_defined = sum(1 for node in graph.nodes.values() if node.inputs and node.outputs) / len(graph.nodes) if graph.nodes else 0
        score += well_defined * 0.3
        
        has_dependencies = sum(1 for node in graph.nodes.values() if node.dependencies)
        score += (has_dependencies / len(graph.nodes)) * 0.3 if graph.nodes else 0
        
        return min(score, 1.0)
    
    def _evaluate_dependency_graph(self, graph: WorkGraph) -> float:
        if not graph.nodes or not graph.edges:
            return 0.0
        
        score = 0.0
        
        if self._has_cycle(graph):
            return 0.0
        
        score += 0.5
        
        nodes_with_deps = sum(1 for n in graph.nodes.values() if n.dependencies)
        score += (nodes_with_deps / len(graph.nodes)) * 0.5
        
        return score
    
    def _has_cycle(self, graph: WorkGraph) -> bool:
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
    
    def _calculate_speedup(self, multi_agent_time: float, baseline_time: float) -> float:
        if baseline_time <= 0:
            return 0.0
        return baseline_time / multi_agent_time if multi_agent_time > 0 else 0.0
    
    def _evaluate_merge_correctness(self, result: MultiAgentResult) -> float:
        if not result.executions:
            return 0.0
        
        completed = sum(1 for e in result.executions if e.status == "completed")
        total = len(result.executions)
        
        return completed / total if total > 0 else 0.0
    
    def _evaluate_role_routing(self, result: MultiAgentResult, task: SwarmBenchmarkTask) -> float:
        if not result.executions:
            return 0.0
        
        role_map = {
            WorkerRole.RESEARCHER: ["research", "analyze", "investigate"],
            WorkerRole.EXECUTOR: ["execute", "implement", "run", "patch"],
            WorkerRole.VERIFIER: ["verify", "test", "check", "validate"],
            WorkerRole.CRITIC: ["critique", "review", "assess"],
            WorkerRole.TOOL_BUILDER: ["build", "create", "tool"]
        }
        
        score = 0.0
        for execution in result.executions:
            task_text = execution.node_id.lower()
            keywords = role_map.get(execution.role, [])
            if any(kw in task_text for kw in keywords):
                score += 1.0
        
        return score / len(result.executions) if result.executions else 0.0
    
    def _calculate_duplicate_rate(self, result: MultiAgentResult) -> float:
        if not result.executions:
            return 0.0
        
        artifacts = defaultdict(list)
        for execution in result.executions:
            for output_key in execution.outputs:
                artifacts[output_key].append(execution.worker_id)
        
        duplicates = sum(1 for workers in artifacts.values() if len(workers) > 1)
        total = len(artifacts)
        
        return duplicates / total if total > 0 else 0.0
    
    def _evaluate_recovery(self, result: MultiAgentResult) -> float:
        if not result.executions:
            return 0.0
        
        failed = [e for e in result.executions if e.status == "failed"]
        recovered = sum(1 for e in result.executions if e.status == "recovered")
        
        if not failed:
            return 1.0
        
        return recovered / len(failed) if failed else 0.0
    
    def _evaluate_communication(self, result: MultiAgentResult) -> float:
        if not result.executions:
            return 0.0
        
        total_sent = sum(e.messages_sent for e in result.executions)
        
        if total_sent == 0:
            return 0.0
        
        total_received = sum(e.messages_received for e in result.executions)
        balance = 1 - abs(total_sent - total_received) / (total_sent + total_received)
        
        return balance
    
    def _calculate_net_gain(self, result: MultiAgentResult, task: Optional[SwarmBenchmarkTask]) -> float:
        if not task or task.task_id not in self.baseline_results:
            return 0.0
        
        baseline = self.baseline_results[task.task_id]
        speedup = self._calculate_speedup(result.duration, baseline)
        
        quality_delta = 1.0 if result.success else -0.5
        
        net_gain = speedup * quality_delta
        
        failures = sum(1 for e in result.executions if e.status == "failed")
        if failures > 0 and result.executions:
            net_gain *= (1 - failures / len(result.executions))
        
        return net_gain
    
    def run_benchmark(self, task_id: str, executor_func: Any) -> MultiAgentResult:
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        start_time = time.time()
        
        result = executor_func(task)
        
        result.duration = time.time() - start_time
        result.task_id = task_id
        
        result.metrics = self.evaluate_result(result, task)
        
        self.results.append(result)
        return result
    
    def get_suite_report(self) -> Dict[str, Any]:
        if not self.results:
            return {"status": "no_results"}
        
        all_metrics = defaultdict(list)
        for result in self.results:
            for metric, value in result.metrics.items():
                all_metrics[metric].append(value)
        
        avg_metrics = {
            metric: sum(values) / len(values)
            for metric, values in all_metrics.items()
        }
        
        return {
            "total_tasks": len(self.tasks),
            "completed_runs": len(self.results),
            "success_rate": sum(1 for r in self.results if r.success) / len(self.results),
            "average_metrics": avg_metrics,
            "baseline_count": len(self.baseline_results)
        }


__all__ = [
    'SwarmBenchmarkSuite',
    'WorkerRole',
    'TaskType',
    'EvaluationMetric',
    'WorkNode',
    'WorkGraph',
    'WorkerExecution',
    'MultiAgentResult',
    'SwarmBenchmarkTask'
]
