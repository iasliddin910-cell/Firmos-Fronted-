"""
ExternalBenchmarkBridge - External Benchmark Adapter
=============================================

Tashqi benchmarklarni ichki formatga moslash.

Bu modul:
- SWE-bench style adapter
- Terminal task adapter
- Browser workflow adapter
- OS/computer-use style adapter
- Scorecard conversion

Definition of Done:
1. Tashqi benchmarklar ichki runner formatiga ulanadi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class ExternalBenchmarkType(str, Enum):
    """Tashqi benchmark turlari."""
    SWE_BENCH = "swe_bench"
    TERMINAL_BENCH = "terminal_bench"
    WEB_ARENA = "web_arena"
    OS_WORLD = "os_world"
    AGENT_WEB = "agent_web"
    GENERAL_AGENT = "general_agent"


@dataclass
class ExternalTask:
    """Tashqi benchmark task."""
    external_id: str
    benchmark_type: str
    
    # Task content
    repo: str = ""
    issue: str = ""
    patch: str = ""
    instructions: str = ""
    
    # Environment
    base_commit: str = ""
    test_patch: str = ""
    version: str = ""
    
    # Metadata
    difficulty: str = "medium"
    domain: str = ""


@dataclass
class ExternalResult:
    """Tashqi benchmark natijasi."""
    external_id: str
    resolved: bool = False
    resolution: str = ""
    
    # Metrics
    patch_apply_success: bool = False
    tests_passed: bool = False
    resolution_time_seconds: float = 0.0
    
    # Quality
    resolution_quality: float = 0.0


class ExternalBenchmarkBridge:
    """
    Tashqi benchmark adapter.
    
    Bu modul tashqi benchmarklarni ichki run/telemetry formatiga
    o'giradi.
    """
    
    def __init__(self):
        self.adapters = {
            ExternalBenchmarkType.SWE_BENCH: self._adapt_swe_bench,
            ExternalBenchmarkType.TERMINAL_BENCH: self._adapt_terminal,
            ExternalBenchmarkType.WEB_ARENA: self._adapt_web_arena,
            ExternalBenchmarkType.OS_WORLD: self._adapt_os_world,
        }
    
    def load_external_tasks(
        self,
        benchmark_type: ExternalBenchmarkType,
        task_source: Any,
    ) -> List[ExternalTask]:
        """Tashqi tasklarni yuklash."""
        adapter = self.adapters.get(benchmark_type)
        if not adapter:
            return []
        return adapter(task_source)
    
    def convert_to_internal_format(
        self,
        external_task: ExternalTask,
    ) -> Dict[str, Any]:
        """Ichki formatga o'girish."""
        return {
            "task_id": f"ext_{external_task.external_id}",
            "suite": self._get_suite_mapping(external_task.benchmark_type),
            "difficulty": external_task.difficulty,
            "capabilities": self._get_capability_mapping(external_task.benchmark_type),
            "prompt": external_task.instructions,
            "repo": external_task.repo,
            "base_commit": external_task.base_commit,
            "expected_patch": external_task.patch,
            "test_patch": external_task.test_patch,
            "metadata": {
                "external_type": external_task.benchmark_type,
                "domain": external_task.domain,
            }
        }
    
    def convert_result(
        self,
        external_result: ExternalResult,
        internal_format: Dict,
    ) -> Dict[str, Any]:
        """Natijani ichki scorecard formatiga o'girish."""
        return {
            "task_id": internal_format["task_id"],
            "raw_capability_score": 1.0 if external_result.resolved else 0.0,
            "resolved": external_result.resolved,
            "resolution": external_result.resolution,
            "resolution_time": external_result.resolution_time_seconds,
            "tests_passed": external_result.tests_passed,
            "quality": external_result.resolution_quality,
        }
    
    def _adapt_swe_bench(self, source: Any) -> List[ExternalTask]:
        """SWE-bench adapter."""
        tasks = []
        # Simplified - would parse actual SWE-bench format
        return tasks
    
    def _adapt_terminal(self, source: Any) -> List[ExternalTask]:
        """Terminal bench adapter."""
        tasks = []
        return tasks
    
    def _adapt_web_arena(self, source: Any) -> List[ExternalTask]:
        """WebArena adapter."""
        tasks = []
        return tasks
    
    def _adapt_os_world(self, source: Any) -> List[ExternalTask]:
        """OSWorld adapter."""
        tasks = []
        return tasks
    
    def _get_suite_mapping(self, benchmark_type: str) -> str:
        """Suite mapping."""
        mappings = {
            "swe_bench": "repo_engineering",
            "terminal_bench": "terminal_operations",
            "web_arena": "browser_workflow",
            "os_world": "long_horizon_orchestration",
        }
        return mappings.get(benchmark_type, "general")
    
    def _get_capability_mapping(self, benchmark_type: str) -> List[str]:
        """Capability mapping."""
        mappings = {
            "swe_bench": ["repo_comprehension", "bug_localization", "multi_file_patching"],
            "terminal_bench": ["terminal_ops", "planning"],
            "web_arena": ["browser_automation", "recovery"],
            "os_world": ["long_horizon_orchestration", "planning", "recovery"],
        }
        return mappings.get(benchmark_type, ["general"])


def create_bridge(benchmark_type: ExternalBenchmarkType) -> ExternalBenchmarkBridge:
    """Bridge yaratish."""
    return ExternalBenchmarkBridge()
