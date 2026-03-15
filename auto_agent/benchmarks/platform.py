"""
OmniAgent X - Benchmark Platform
================================
Harness-based benchmark platform for world-class agent evaluation.

This module provides:
- Declarative task specification (YAML/JSON based)
- Fixture repositories with isolated workspaces
- Verifier pipeline (pytest, diff, DOM, screenshot, etc.)
- Runner classes for each benchmark type
- Manifest and evidence tracking
- Task versioning and reproducibility

Architecture:
    benchmark.py (entry point)
        └── BenchmarkPlatform (main orchestrator)
                ├── TaskLoader (loads task packs)
                ├── FixtureManager (manages fixtures)
                ├── Runner (executes tasks)
                ├── VerifierPipeline (validates results)
                └── EvidenceStore (stores artifacts)

Usage:
    platform = BenchmarkPlatform()
    result = platform.run_task("repair_flask_import_bug_v1")
    print(result.passed, result.evidence)
"""
import os
import json
import yaml
import logging
import shutil
import hashlib
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class TaskDifficulty(str, Enum):
    """Task difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    FRONTIER = "frontier"


class TaskSuite(str, Enum):
    """Benchmark suites"""
    CODING = "coding"
    REPAIR = "repair"
    BROWSER = "browser"
    DESKTOP = "desktop"
    LONG_HORIZON = "long_horizon"


class VerifierType(str, Enum):
    """Verifier types"""
    PYTEST = "pytest"
    FILE_EXISTS = "file_exists"
    FILE_DIFF = "file_diff"
    DOM_VERIFIER = "dom"
    SCREENSHOT = "screenshot"
    JSON_SCHEMA = "json_schema"
    LOG_VERIFIER = "log"
    STATE_TRANSITION = "state_transition"


class ResetPolicy(str, Enum):
    """Workspace reset policies"""
    SNAPSHOT = "snapshot"  # Restore from snapshot
    CLEAN = "clean"  # Delete and recreate
    CLONE = "clone"  # Clone fresh each time


# ==================== DATA CLASSES ====================

@dataclass
class TaskSpec:
    """
    Declarative task specification.
    
    This replaces the old dict-based tasks in benchmark.py.
    Each task is now a self-contained specification with:
    - Unique ID and version
    - Difficulty and suite
    - Prompt for the agent
    - Fixture path
    - Allowed tools
    - Timeout
    - Verifier chain
    - Expected artifacts
    - Reset policy
    - Seed for reproducibility
    """
    task_id: str
    suite: str  # coding, repair, browser, desktop, long_horizon
    version: str
    difficulty: str  # easy, medium, hard, frontier
    
    prompt: str
    fixture_path: str  # Relative to fixtures/
    allowed_tools: List[str]
    timeout_sec: int
    
    verifier_chain: List[str]  # List of verifier names
    expected_artifacts: List[str]  # Expected output files
    
    reset_policy: str = "clone"  # snapshot, clean, clone
    seed: int = 42
    tags: List[str] = field(default_factory=list)
    
    # Optional metadata
    initial_context: Dict = field(default_factory=dict)
    subtasks: List[Dict] = field(default_factory=list)
    failure_injection: Dict = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)
    
    # Environment
    environment_hash: str = ""
    
    def __post_init__(self):
        # Generate environment hash if not provided
        if not self.environment_hash:
            self.environment_hash = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate deterministic hash for this task version"""
        content = f"{self.task_id}:{self.version}:{self.suite}:{self.difficulty}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @classmethod
    def from_yaml(cls, path: Path) -> "TaskSpec":
        """Load task from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_json(cls, path: Path) -> "TaskSpec":
        """Load task from JSON file"""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "suite": self.suite,
            "version": self.version,
            "difficulty": self.difficulty,
            "prompt": self.prompt,
            "fixture_path": self.fixture_path,
            "allowed_tools": self.allowed_tools,
            "timeout_sec": self.timeout_sec,
            "verifier_chain": self.verifier_chain,
            "expected_artifacts": self.expected_artifacts,
            "reset_policy": self.reset_policy,
            "seed": self.seed,
            "tags": self.tags,
            "initial_context": self.initial_context,
            "subtasks": self.subtasks,
            "failure_injection": self.failure_injection,
            "checkpoints": self.checkpoints,
            "environment_hash": self.environment_hash
        }
    
    @property
    def capability_tags(self) -> List[str]:
        """Get capability tags from subtasks and tags"""
        caps = set(self.tags)
        for st in self.subtasks:
            if "capability" in st:
                caps.add(st["capability"])
        return list(caps)


@dataclass
class VerifierConfig:
    """Configuration for a verifier"""
    verifier_type: str
    config: Dict = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VerifierConfig":
        return cls(
            verifier_type=data.get("type", "pytest"),
            config=data.get("config", {})
        )


@dataclass
class TaskResult:
    """Result of a task execution"""
    task_id: str
    task_version: str
    passed: bool
    score: float
    
    # Evidence
    stdout: str = ""
    stderr: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    verifier_results: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    duration: float = 0.0
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    environment_hash: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_version": self.task_version,
            "passed": self.passed,
            "score": self.score,
            "stdout": self.stdout[:10000],  # Truncate for storage
            "stderr": self.stderr[:10000],
            "artifacts": self.artifacts,
            "verifier_results": self.verifier_results,
            "duration": self.duration,
            "error": self.error,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "environment_hash": self.environment_hash
        }


@dataclass
class BenchmarkManifest:
    """Manifest for a benchmark pack"""
    pack_version: str
    created_at: str
    tasks: List[Dict]
    total_tasks: int
    suite_distribution: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    environment_hash: str
    
    @classmethod
    def from_tasks(cls, tasks: List[TaskSpec], pack_version: str) -> "BenchmarkManifest":
        suite_dist = {}
        difficulty_dist = {}
        
        for task in tasks:
            suite_dist[task.suite] = suite_dist.get(task.suite, 0) + 1
            difficulty_dist[task.difficulty] = difficulty_dist.get(task.difficulty, 0) + 1
        
        content = json.dumps({
            "pack_version": pack_version,
            "tasks": [t.to_dict() for t in tasks]
        }, sort_keys=True)
        
        env_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        return cls(
            pack_version=pack_version,
            created_at=datetime.now().isoformat(),
            tasks=[t.to_dict() for t in tasks],
            total_tasks=len(tasks),
            suite_distribution=suite_dist,
            difficulty_distribution=difficulty_dist,
            environment_hash=env_hash
        )
    
    def to_dict(self) -> Dict:
        return {
            "pack_version": self.pack_version,
            "created_at": self.created_at,
            "total_tasks": self.total_tasks,
            "suite_distribution": self.suite_distribution,
            "difficulty_distribution": self.difficulty_distribution,
            "environment_hash": self.environment_hash
        }


# ==================== FIXTURE MANAGER ====================

class FixtureManager:
    """
    Manages fixture repositories for benchmarks.
    
    Responsibilities:
    - Clone/setup fixtures
    - Reset workspace between runs
    - Ensure reproducibility
    """
    
    def __init__(self, fixtures_root: Path):
        self.fixtures_root = fixtures_root
        self.workspace_root = Path(tempfile.mkdtemp(prefix="omniagent_bench_"))
        self.snapshots: Dict[str, Path] = {}
        
        logger.info(f"📁 FixtureManager initialized")
        logger.info(f"   Fixtures root: {fixtures_root}")
        logger.info(f"   Workspace root: {self.workspace_root}")
    
    def prepare_workspace(self, task: TaskSpec) -> Path:
        """
        Prepare isolated workspace for a task.
        
        Args:
            task: Task specification
            
        Returns:
            Path to prepared workspace
        """
        # Create task-specific workspace
        workspace = self.workspace_root / task.task_id
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Get fixture source
        fixture_source = self.fixtures_root / task.fixture_path
        
        if not fixture_source.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_source}")
        
        # Clone or copy fixture based on reset policy
        if task.reset_policy == "clone":
            if fixture_source.is_dir():
                shutil.copytree(fixture_source, workspace, dirs_exist_ok=True)
            else:
                shutil.copy2(fixture_source, workspace)
        elif task.reset_policy == "snapshot":
            # TODO: Implement snapshot-based reset
            if fixture_source.is_dir():
                shutil.copytree(fixture_source, workspace, dirs_exist_ok=True)
            else:
                shutil.copy2(fixture_source, workspace)
        else:
            # Clean and clone
            if workspace.exists():
                shutil.rmtree(workspace)
            if fixture_source.is_dir():
                shutil.copytree(fixture_source, workspace)
            else:
                shutil.copy2(fixture_source, workspace)
        
        logger.info(f"📂 Workspace prepared: {workspace}")
        return workspace
    
    def save_snapshot(self, task_id: str, workspace: Path):
        """Save workspace snapshot for later restoration"""
        snapshot_dir = self.workspace_root / ".snapshots" / task_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        if workspace.exists():
            shutil.copytree(workspace, snapshot_dir, dirs_exist_ok=True)
        
        self.snapshots[task_id] = snapshot_dir
        logger.info(f"📸 Snapshot saved for: {task_id}")
    
    def restore_snapshot(self, task_id: str, workspace: Path):
        """Restore workspace from snapshot"""
        snapshot_dir = self.snapshots.get(task_id)
        
        if not snapshot_dir or not snapshot_dir.exists():
            logger.warning(f"No snapshot found for: {task_id}")
            return
        
        # Clear current workspace
        if workspace.exists():
            shutil.rmtree(workspace)
        
        # Restore from snapshot
        shutil.copytree(snapshot_dir, workspace)
        logger.info(f"🔄 Snapshot restored for: {task_id}")
    
    def cleanup(self):
        """Clean up all workspaces"""
        if self.workspace_root.exists():
            shutil.rmtree(self.workspace_root)
        logger.info("🧹 Workspace cleaned up")


# ==================== VERIFIER PIPELINE ====================

class VerifierPipeline:
    """
    Pipeline of verifiers for task validation.
    
    Runs multiple verifiers in sequence and aggregates results.
    """
    
    def __init__(self, verifiers_root: Path):
        self.verifiers_root = verifiers_root
        self.verifier_registry: Dict[str, Callable] = {}
        
        # Register built-in verifiers
        self._register_builtin_verifiers()
        
        logger.info("✅ VerifierPipeline initialized")
    
    def _register_builtin_verifiers(self):
        """Register built-in verifier functions"""
        self.verifier_registry = {
            "pytest": self._verify_pytest,
            "file_exists": self._verify_file_exists,
            "file_diff": self._verify_file_diff,
            "screenshot": self._verify_screenshot,
            "json_schema": self._verify_json_schema,
            "log": self._verify_log,
        }
    
    def run_verifiers(self, task: TaskSpec, workspace: Path, 
                     artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run verifier chain for a task.
        
        Args:
            task: Task specification
            workspace: Task workspace path
            artifacts: Generated artifacts
            
        Returns:
            Dict of verifier results
        """
        results = {}
        
        for verifier_name in task.verifier_chain:
            verifier_func = self.verifier_registry.get(verifier_name)
            
            if not verifier_func:
                logger.warning(f"⚠️ Verifier not found: {verifier_name}")
                results[verifier_name] = {
                    "passed": False,
                    "error": f"Verifier not found: {verifier_name}"
                }
                continue
            
            try:
                result = verifier_func(task, workspace, artifacts)
                results[verifier_name] = result
                
                if not result.get("passed", False):
                    logger.warning(f"❌ Verifier failed: {verifier_name}")
                else:
                    logger.info(f"✅ Verifier passed: {verifier_name}")
                    
            except Exception as e:
                logger.error(f"❌ Verifier error ({verifier_name}): {e}")
                results[verifier_name] = {
                    "passed": False,
                    "error": str(e)
                }
        
        return results
    
    def _verify_pytest(self, task: TaskSpec, workspace: Path, 
                       artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Run pytest verifier"""
        try:
            # Run pytest
            result = subprocess.run(
                ["pytest", "-v", "--tb=short"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=task.timeout_sec
            )
            
            passed = result.returncode == 0
            
            return {
                "passed": passed,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_file": "pytest_report.json"
            }
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "error": "Pytest timed out"
            }
        except FileNotFoundError:
            return {
                "passed": False,
                "error": "pytest not found"
            }
        except Exception as e:
            return {
                "passed": False,
                "error": str(e)
            }
    
    def _verify_file_exists(self, task: TaskSpec, workspace: Path,
                           artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Verify expected files exist"""
        expected = task.expected_artifacts
        missing = []
        
        for file_path in expected:
            full_path = workspace / file_path
            if not full_path.exists():
                missing.append(file_path)
        
        return {
            "passed": len(missing) == 0,
            "expected": expected,
            "missing": missing
        }
    
    def _verify_file_diff(self, task: TaskSpec, workspace: Path,
                         artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Verify file changes are within acceptable bounds"""
        # This would check diff size, forbidden files, etc.
        # Placeholder for actual implementation
        return {
            "passed": True,
            "message": "Diff verification passed (placeholder)"
        }
    
    def _verify_screenshot(self, task: TaskSpec, workspace: Path,
                          artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Verify screenshot artifacts"""
        # This would verify screenshot quality, content, etc.
        return {
            "passed": True,
            "message": "Screenshot verification passed (placeholder)"
        }
    
    def _verify_json_schema(self, task: TaskSpec, workspace: Path,
                           artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Verify JSON artifacts match schema"""
        return {
            "passed": True,
            "message": "JSON schema verification passed (placeholder)"
        }
    
    def _verify_log(self, task: TaskSpec, workspace: Path,
                   artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """Verify log artifacts"""
        return {
            "passed": True,
            "message": "Log verification passed (placeholder)"
        }


# ==================== TASK RUNNER ====================

class TaskRunner:
    """
    Base class for task runners.
    
    Each benchmark type (coding, repair, browser, etc.) has its own runner.
    """
    
    def __init__(self, fixture_manager: FixtureManager, 
                 verifier_pipeline: VerifierPipeline):
        self.fixture_manager = fixture_manager
        self.verifier_pipeline = verifier_pipeline
        
        logger.info("🏃 TaskRunner initialized")
    
    def run_task(self, task: TaskSpec, agent=None) -> TaskResult:
        """
        Run a single task.
        
        Args:
            task: Task specification
            agent: Optional agent to execute the task
            
        Returns:
            TaskResult with evidence
        """
        start_time = time.time()
        
        try:
            # Prepare workspace
            workspace = self.fixture_manager.prepare_workspace(task)
            
            # Execute task
            artifacts = self._execute_task(task, workspace, agent)
            
            # Run verifiers
            verifier_results = self.verifier_pipeline.run_verifiers(
                task, workspace, artifacts
            )
            
            # Calculate score
            all_passed = all(
                v.get("passed", False) for v in verifier_results.values()
            )
            score = 1.0 if all_passed else 0.0
            
            duration = time.time() - start_time
            
            return TaskResult(
                task_id=task.task_id,
                task_version=task.version,
                passed=all_passed,
                score=score,
                artifacts=artifacts,
                verifier_results=verifier_results,
                duration=duration,
                environment_hash=task.environment_hash
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Task failed: {task.task_id} - {e}")
            
            return TaskResult(
                task_id=task.task_id,
                task_version=task.version,
                passed=False,
                score=0.0,
                duration=duration,
                error=str(e),
                environment_hash=task.environment_hash
            )
    
    def _execute_task(self, task: TaskSpec, workspace: Path, 
                     agent=None) -> Dict[str, Any]:
        """
        Execute the task. Override in subclasses.
        
        Args:
            task: Task specification
            workspace: Prepared workspace
            agent: Optional agent
            
        Returns:
            Dict of generated artifacts
        """
        raise NotImplementedError("Subclasses must implement _execute_task")


# ==================== BENCHMARK PLATFORM ====================

class BenchmarkPlatform:
    """
    Main benchmark platform orchestrator.
    
    This is the entry point for running benchmark tasks.
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize benchmark platform.
        
        Args:
            base_path: Base path for benchmarks (default: auto_agent/benchmarks)
        """
        if base_path is None:
            base_path = Path(__file__).parent / "benchmarks"
        
        self.base_path = base_path
        self.packs_path = base_path / "packs"
        self.fixtures_path = base_path / "fixtures"
        self.verifiers_path = base_path / "verifiers"
        self.results_path = base_path / "results"
        self.manifests_path = base_path / "manifests"
        
        # Initialize components
        self.fixture_manager = FixtureManager(self.fixtures_path)
        self.verifier_pipeline = VerifierPipeline(self.verifiers_path)
        self.task_runner = TaskRunner(self.fixture_manager, 
                                      self.verifier_pipeline)
        
        # Task registry
        self.tasks: Dict[str, TaskSpec] = {}
        
        logger.info("🎯 BenchmarkPlatform initialized")
        logger.info(f"   Base path: {self.base_path}")
    
    def load_tasks(self, suite: Optional[str] = None) -> Dict[str, TaskSpec]:
        """
        Load tasks from pack files.
        
        Args:
            suite: Optional suite to filter (coding, repair, etc.)
            
        Returns:
            Dict of task_id -> TaskSpec
        """
        tasks = {}
        
        # Determine which suites to load
        suites = [suite] if suite else ["coding", "repair", "browser", 
                                          "desktop", "long_horizon"]
        
        for suite_name in suites:
            suite_path = self.packs_path / suite_name
            
            if not suite_path.exists():
                logger.warning(f"Suite path not found: {suite_path}")
                continue
            
            # Load all YAML/JSON files in suite directory
            for task_file in suite_path.glob("*.yaml"):
                try:
                    task = TaskSpec.from_yaml(task_file)
                    tasks[task.task_id] = task
                except Exception as e:
                    logger.error(f"Error loading {task_file}: {e}")
            
            for task_file in suite_path.glob("*.json"):
                try:
                    task = TaskSpec.from_json(task_file)
                    tasks[task.task_id] = task
                except Exception as e:
                    logger.error(f"Error loading {task_file}: {e}")
        
        self.tasks = tasks
        logger.info(f"📋 Loaded {len(tasks)} tasks")
        
        return tasks
    
    def run_task(self, task_id: str, agent=None) -> TaskResult:
        """
        Run a single task by ID.
        
        Args:
            task_id: Task identifier
            agent: Optional agent
            
        Returns:
            TaskResult
        """
        if task_id not in self.tasks:
            # Try loading tasks first
            self.load_tasks()
        
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # Create runner for task suite
        runner = self._get_runner_for_suite(task.suite)
        
        # Run task
        result = runner.run_task(task, agent)
        
        # Save result
        self._save_result(result)
        
        return result
    
    def run_suite(self, suite: str, agent=None) -> List[TaskResult]:
        """
        Run all tasks in a suite.
        
        Args:
            suite: Suite name
            agent: Optional agent
            
        Returns:
            List of TaskResults
        """
        tasks = self.load_tasks(suite)
        results = []
        
        runner = self._get_runner_for_suite(suite)
        
        for task_id, task in tasks.items():
            logger.info(f"🎯 Running task: {task_id}")
            result = runner.run_task(task, agent)
            results.append(result)
            self._save_result(result)
        
        return results
    
    def _get_runner_for_suite(self, suite: str) -> TaskRunner:
        """Get runner for a specific suite"""
        # For now, return base runner
        # Subclasses can override for suite-specific behavior
        return self.task_runner
    
    def _save_result(self, result: TaskResult):
        """Save task result to disk"""
        result_file = self.results_path / f"{result.run_id}.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(result_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        
        logger.info(f"💾 Result saved: {result_file}")
    
    def create_manifest(self, pack_version: str) -> BenchmarkManifest:
        """Create manifest for current task pack"""
        tasks_list = list(self.tasks.values())
        manifest = BenchmarkManifest.from_tasks(tasks_list, pack_version)
        
        # Save manifest
        manifest_file = self.manifests_path / f"manifest_{pack_version}.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)
        
        logger.info(f"📦 Manifest created: {manifest_file}")
        
        return manifest
    
    def get_results_summary(self) -> Dict:
        """Get summary of all results"""
        results = []
        
        for result_file in self.results_path.glob("*.json"):
            try:
                with open(result_file) as f:
                    results.append(json.load(f))
            except:
                pass
        
        if not results:
            return {"total": 0, "passed": 0, "pass_rate": 0.0}
        
        passed = sum(1 for r in results if r.get("passed", False))
        
        return {
            "total": len(results),
            "passed": passed,
            "pass_rate": passed / len(results) if results else 0.0,
            "avg_duration": sum(r.get("duration", 0) for r in results) / len(results)
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.fixture_manager.cleanup()


# ==================== HELPER FUNCTIONS ====================

def create_task_file(task: TaskSpec, path: Path):
    """Save task to YAML file"""
    with open(path, "w") as f:
        yaml.dump(task.to_dict(), f, default_flow_style=False)


# ==================== FACTORY ====================

def create_benchmark_platform(base_path: Optional[Path] = None) -> BenchmarkPlatform:
    """Create benchmark platform instance"""
    return BenchmarkPlatform(base_path)
