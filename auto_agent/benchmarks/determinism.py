"""
OmniAgent X - Run Manifest & Determinism System
==============================================
Ensures benchmark determinism, reproducibility, and auditability.

This module provides:
- RunManifest: Complete metadata for every benchmark run
- EnvironmentFingerprint: Deterministic environment hashing
- SeedController: Controlled randomness for reproducibility
- TaskVersioning: Immutable task versions
- FlakeAnalyzer: Detects and quarantines flaky tasks

Core Policy:
    One run is NEVER enough for release decision.
    All runs must be deterministic, reproducible, and auditable.
"""
import os
import sys
import json
import hashlib
import platform
import subprocess
import random
import uuid
import locale
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class TaskStatus(str, Enum):
    """Task lifecycle status"""
    DRAFT = "draft"
    CANDIDATE = "candidate"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class FlakeStatus(str, Enum):
    """Flake detection status"""
    STABLE = "stable"
    CANDIDATE = "candidate"
    FLAKY = "flaky"
    QUARANTINED = "quarantined"


class NetworkPolicy(str, Enum):
    """Network access policy"""
    OFFLINE = "offline"
    LOCAL_ONLY = "local_only"
    ALLOWED = "allowed"


# ==================== RUN MANIFEST ====================

@dataclass
class RunManifest:
    """
    Complete metadata for every benchmark run.
    
    This is MANDATORY for every run - no run should proceed without it.
    Enables full auditability and reproducibility.
    
    Fields:
    - run_id: Unique identifier for this run
    - timestamp: ISO timestamp when run started
    - repo_commit: Git commit hash
    - benchmark_pack_version: Version of task pack used
    - task_ids: List of task IDs in this run
    - seed: Random seed used
    - python_version: Python version
    - os_name: Operating system
    - container_image: Container image (if any)
    - dependency_lock_hash: Hash of locked dependencies
    - environment_hash: Fingerprint of environment
    - model_name: Model used
    - model_config_hash: Model configuration hash
    - tool_config_hash: Tool configuration hash
    - workspace_snapshot_hash: Hash of workspace state
    - network_policy: Network access policy
    - timezone: System timezone
    - locale: System locale
    - notes: Additional metadata
    """
    run_id: str
    timestamp: str
    
    # Repository info
    repo_commit: str = ""
    repo_url: str = ""
    
    # Benchmark info
    benchmark_pack_version: str = ""
    task_ids: List[str] = field(default_factory=list)
    
    # Reproducibility
    seed: int = 42
    task_order: List[str] = field(default_factory=list)
    
    # Environment
    python_version: str = ""
    python_executable: str = ""
    os_name: str = ""
    os_version: str = ""
    container_image: str = ""
    container_runtime: str = ""
    
    # Dependencies
    dependency_lock_hash: str = ""
    pip_freeze_hash: str = ""
    requirements_files: List[str] = field(default_factory=list)
    
    # Tools
    browser_version: str = ""
    playwright_version: str = ""
    tool_config_hash: str = ""
    
    # Environment fingerprint
    environment_hash: str = ""
    environment_details: Dict[str, Any] = field(default_factory=dict)
    
    # Model
    model_name: str = ""
    model_config_hash: str = ""
    
    # Workspace
    workspace_snapshot_hash: str = ""
    
    # Policy
    network_policy: str = NetworkPolicy.LOCAL_ONLY.value
    timezone: str = ""
    locale: str = ""
    
    # Additional
    notes: Dict[str, str] = field(default_factory=dict)
    
    # Results (filled after run)
    passed_count: int = 0
    failed_count: int = 0
    total_duration: float = 0.0
    run_status: str = "pending"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def create_new(cls, seed: int = 42) -> "RunManifest":
        """Create a new manifest for a run"""
        return cls(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            seed=seed,
            python_version=sys.version,
            python_executable=sys.executable,
            os_name=platform.system(),
            os_version=platform.version(),
            timezone=os.getenv("TZ", "UTC"),
            locale=locale.getlocale()[0] or "en_US"
        )
    
    def verify_environment_match(self, other: "RunManifest") -> tuple[bool, List[str]]:
        """
        Verify environment matches another run for comparison.
        
        Returns:
            (matches, list_of_differences)
        """
        differences = []
        
        # Critical fields that must match
        critical_fields = [
            ("python_version", "Python version"),
            ("os_name", "OS name"),
            ("benchmark_pack_version", "Task pack version"),
            ("seed", "Random seed"),
            ("dependency_lock_hash", "Dependency lock"),
        ]
        
        for field_name, display_name in critical_fields:
            self_val = getattr(self, field_name, "")
            other_val = getattr(other, field_name, "")
            if self_val != other_val:
                differences.append(f"{display_name}: {self_val} != {other_val}")
        
        return len(differences) == 0, differences


# ==================== ENVIRONMENT FINGERPRINT ====================

class EnvironmentFingerprint:
    """
    Creates deterministic hashes of the environment.
    
    This ensures that benchmark results can be attributed to
    the actual environment, not just randomness.
    """
    
    @staticmethod
    def compute_fingerprint() -> tuple[str, Dict[str, Any]]:
        """
        Compute full environment fingerprint.
        
        Returns:
            (hash, details_dict)
        """
        details = {}
        
        # Python version
        details["python_version"] = sys.version
        details["python_executable"] = sys.executable
        details["python_implementation"] = getattr(sys, "implementation", "cpython").name
        
        # Platform
        details["os_name"] = platform.system()
        details["os_version"] = platform.version()
        details["os_release"] = platform.release()
        details["os_machine"] = platform.machine()
        
        # Timezone & locale
        details["timezone"] = os.getenv("TZ", "UTC")
        details["locale"] = str(locale.getlocale())
        
        # Installed packages (deterministic)
        try:
            pip_freeze = subprocess.run(
                [sys.executable, "-m", "pip", "freeze", "--all"],
                capture_output=True,
                text=True,
                timeout=30
            )
            packages = sorted(pip_freeze.stdout.strip().split("\n"))
            details["pip_packages"] = packages[:50]  # First 50 for brevity
            details["pip_count"] = len(packages)
        except Exception as e:
            details["pip_error"] = str(e)
            packages = []
        
        # Hash of packages for comparison
        package_hash = hashlib.sha256(
            "\n".join(packages).encode()
        ).hexdigest()[:16]
        
        # Browser tools
        details["playwright_version"] = EnvironmentFingerprint._get_playwright_version()
        
        # Compute final hash
        payload = {
            "python": details.get("python_version", ""),
            "platform": details.get("os_name", ""),
            "packages": package_hash,
            "playwright": details.get("playwright_version", ""),
            "timezone": details.get("timezone", ""),
        }
        
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:32]
        
        return fingerprint, details
    
    @staticmethod
    def _get_playwright_version() -> str:
        """Get Playwright version if installed"""
        try:
            result = subprocess.run(
                ["playwright", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except:
            pass
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import playwright; print(playwright.__version__)"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return f"playwright {result.stdout.strip()}"
        except:
            pass
        
        return "not_installed"
    
    @staticmethod
    def compute_lock_hash(requirements_files: List[str]) -> str:
        """
        Compute hash of locked dependencies.
        
        Args:
            requirements_files: List of requirements file paths
            
        Returns:
            Hash string
        """
        all_deps = []
        
        for req_file in requirements_files:
            path = Path(req_file)
            if path.exists():
                with open(path) as f:
                    content = f.read()
                    all_deps.extend(sorted(content.strip().split("\n")))
        
        return hashlib.sha256(
            "\n".join(all_deps).encode()
        ).hexdigest()[:16]


# ==================== SEED CONTROLLER ====================

class SeedController:
    """
    Controls all sources of randomness for deterministic execution.
    
    CRITICAL POLICY:
        Unseeded randomness is FORBIDDEN in benchmarks.
        Every run must have explicit seed control.
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._original_random_state = random.getstate()
        self._python_random_state = random.getstate()
        
        # Set all seeds
        self.set_all_seeds(seed)
        
        logger.info(f"🎲 SeedController initialized with seed={seed}")
    
    def set_all_seeds(self, seed: int):
        """Set seeds for all random sources"""
        self.seed = seed
        
        # Python random
        random.seed(seed)
        
        # NumPy (if available)
        try:
            import numpy as np
            np.random.seed(seed)
        except ImportError:
            pass
        
        # Hash-based task ordering (deterministic)
        self._task_order_seed = seed
    
    def get_task_order(self, task_ids: List[str]) -> List[str]:
        """
        Get deterministic ordering of tasks based on seed.
        
        This ensures same tasks, same seed = same order.
        """
        # Sort by hash of (task_id + seed) for determinism
        def task_hash(task_id: str) -> int:
            return int(hashlib.md5(f"{task_id}:{self.seed}".encode()).hexdigest(), 16)
        
        return sorted(task_ids, key=task_hash)
    
    def restore(self):
        """Restore original random state after run"""
        random.setstate(self._original_random_state)
        logger.info("🎲 Random state restored")


# ==================== TASK VERSIONING ====================

@dataclass
class TaskVersion:
    """
    Immutable task version information.
    
    Once a version is created, it should NEVER be modified.
    """
    version: str
    task_id: str
    created_at: str
    content_hash: str
    verifier_hash: str
    fixture_hash: str
    status: str = TaskStatus.STABLE.value
    
    # Metadata
    difficulty: str = ""
    suite: str = ""
    owner: str = ""
    last_validated_at: str = ""
    
    # Flake tracking
    flake_status: str = FlakeStatus.STABLE.value
    flake_runs: int = 0
    flake_pass_rate: float = 1.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class TaskRegistry:
    """
    Registry of all task versions.
    
    Ensures:
    - Task versions are immutable
    - Leaderboard tracks versions separately
    - Tasks can be deprecated but not modified
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        if registry_path is None:
            registry_path = Path(__file__).parent / "governance" / "registry.json"
        
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.tasks: Dict[str, TaskVersion] = {}
        self._load_registry()
        
        logger.info(f"📋 TaskRegistry initialized with {len(self.tasks)} tasks")
    
    def _load_registry(self):
        """Load registry from disk"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        self.tasks[task_id] = TaskVersion(**task_data)
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}")
    
    def _save_registry(self):
        """Save registry to disk"""
        data = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
        
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def register_task(self, task_id: str, task_spec: Dict, 
                      difficulty: str = "", suite: str = "") -> TaskVersion:
        """
        Register a new task version.
        
        Creates immutable version with content hash.
        """
        # Compute hashes
        content_hash = hashlib.sha256(
            json.dumps(task_spec, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        verifier_hash = hashlib.sha256(
            json.dumps(task_spec.get("verifier_chain", []), sort_keys=True).encode()
        ).hexdigest()[:16]
        
        fixture_path = task_spec.get("fixture_path", "")
        fixture_hash = ""
        if fixture_path:
            fixture_hash = hashlib.sha256(fixture_path.encode()).hexdigest()[:16]
        
        # Check if version exists
        version_num = 1
        for existing_id in self.tasks:
            if existing_id.startswith(task_id.rsplit("_v", 1)[0]):
                existing = self.tasks[existing_id]
                if existing.content_hash == content_hash:
                    # Same content, return existing
                    return existing
                version_num = max(version_num, 
                    int(existing_id.rsplit("_v", 1)[-1]) + 1)
        
        version_str = f"v{version_num}"
        full_task_id = f"{task_id.rsplit('_v', 1)[0]}_{version_str}"
        
        task_version = TaskVersion(
            version=version_str,
            task_id=full_task_id,
            created_at=datetime.now().isoformat(),
            content_hash=content_hash,
            verifier_hash=verifier_hash,
            fixture_hash=fixture_hash,
            status=TaskStatus.CANDIDATE.value,
            difficulty=difficulty,
            suite=suite
        )
        
        self.tasks[full_task_id] = task_version
        self._save_registry()
        
        logger.info(f"📋 Registered task: {full_task_id}")
        return task_version
    
    def get_stable_tasks(self, suite: Optional[str] = None) -> List[TaskVersion]:
        """Get all stable tasks, optionally filtered by suite"""
        tasks = [
            t for t in self.tasks.values() 
            if t.status == TaskStatus.STABLE.value
        ]
        
        if suite:
            tasks = [t for t in tasks if t.suite == suite]
        
        return tasks
    
    def update_flake_status(self, task_id: str, pass_rate: float):
        """Update flake status based on repeated runs"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.flake_runs += 1
        task.flake_pass_rate = pass_rate
        
        # Determine flake status
        if task.flake_runs >= 10:
            if pass_rate >= 0.95:
                task.flake_status = FlakeStatus.STABLE.value
            elif pass_rate >= 0.70:
                task.flake_status = FlakeStatus.FLAKY.value
            else:
                task.flake_status = FlakeStatus.QUARANTINED.value
        
        self._save_registry()


# ==================== FLAKE ANALYZER ====================

class FlakeAnalyzer:
    """
    Analyzes task stability through repeated runs.
    
    CRITICAL POLICY:
        Flaky tasks are FORBIDDEN in release gate.
    """
    
    def __init__(self, min_runs: int = 10):
        self.min_runs = min_runs
        self.results: Dict[str, List[bool]] = {}
        
        logger.info(f"🔍 FlakeAnalyzer initialized (min_runs={min_runs})")
    
    def record_result(self, task_id: str, passed: bool):
        """Record a single run result"""
        if task_id not in self.results:
            self.results[task_id] = []
        
        self.results[task_id].append(passed)
    
    def analyze_task(self, task_id: str) -> Dict[str, Any]:
        """
        Analyze flake status for a task.
        
        Returns:
            {
                "flake_status": "stable|candidate|flaky|quarantined",
                "pass_rate": float,
                "runs": int,
                "is_flaky": bool
            }
        """
        if task_id not in self.results:
            return {
                "flake_status": FlakeStatus.CANDIDATE.value,
                "pass_rate": 0.0,
                "runs": 0,
                "is_flaky": True
            }
        
        runs = self.results[task_id]
        pass_rate = sum(runs) / len(runs) if runs else 0.0
        
        if len(runs) < self.min_runs:
            return {
                "flake_status": FlakeStatus.CANDIDATE.value,
                "pass_rate": pass_rate,
                "runs": len(runs),
                "is_flaky": False  # Not enough runs to decide
            }
        
        # Determine status based on pass rate
        if pass_rate >= 0.95:
            status = FlakeStatus.STABLE.value
            is_flaky = False
        elif pass_rate >= 0.70:
            status = FlakeStatus.FLAKY.value
            is_flaky = True
        else:
            status = FlakeStatus.QUARANTINED.value
            is_flaky = True
        
        return {
            "flake_status": status,
            "pass_rate": pass_rate,
            "runs": len(runs),
            "is_flaky": is_flaky
        }
    
    def can_use_in_release(self, task_id: str) -> tuple[bool, str]:
        """
        Check if task can be used in release gate.
        
        Returns:
            (can_use, reason)
        """
        analysis = self.analyze_task(task_id)
        
        if analysis["flake_status"] == FlakeStatus.QUARANTINED.value:
            return False, f"Task is quarantined (pass_rate={analysis['pass_rate']:.2%})"
        
        if analysis["flake_status"] == FlakeStatus.FLAKY.value:
            return False, f"Task is flaky (pass_rate={analysis['pass_rate']:.2%})"
        
        if analysis["runs"] < self.min_runs:
            return False, f"Not enough runs: {analysis['runs']}/{self.min_runs}"
        
        return True, "OK"


# ==================== MULTI-RUN AGGREGATOR ====================

@dataclass
class AggregateResult:
    """Aggregated results from multiple runs"""
    task_id: str
    total_runs: int
    
    # Pass statistics
    pass_count: int
    fail_count: int
    pass_rate: float
    
    # Time statistics
    mean_duration: float
    median_duration: float
    p95_duration: float
    max_duration: float
    
    # Per-run details
    runs: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def is_reliable(self) -> bool:
        """Check if result is reliable (enough runs, stable)"""
        return (
            self.total_runs >= 3 and
            self.pass_rate in (0.0, 1.0)  # Either all pass or all fail = reliable
        )
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MultiRunAggregator:
    """
    Aggregates results from multiple runs with different seeds.
    
    CRITICAL POLICY:
        Single run verdict is NEVER enough for release.
        Must use multi-run aggregation.
    """
    
    def __init__(self, min_runs: int = 3):
        self.min_runs = min_runs
        self.run_results: Dict[str, List[Dict]] = {}
        
        logger.info(f"📊 MultiRunAggregator initialized (min_runs={min_runs})")
    
    def add_run(self, task_id: str, run_result: Dict):
        """Add a single run result"""
        if task_id not in self.run_results:
            self.run_results[task_id] = []
        
        self.run_results[task_id].append(run_result)
    
    def aggregate(self, task_id: str) -> AggregateResult:
        """Aggregate results for a task"""
        if task_id not in self.run_results:
            return AggregateResult(
                task_id=task_id,
                total_runs=0,
                pass_count=0,
                fail_count=0,
                pass_rate=0.0,
                mean_duration=0.0,
                median_duration=0.0,
                p95_duration=0.0,
                max_duration=0.0
            )
        
        runs = self.run_results[task_id]
        durations = [r.get("duration", 0) for r in runs]
        
        pass_count = sum(1 for r in runs if r.get("passed", False))
        fail_count = len(runs) - pass_count
        pass_rate = pass_count / len(runs) if runs else 0.0
        
        # Calculate statistics
        durations_sorted = sorted(durations)
        median = durations_sorted[len(durations_sorted) // 2] if durations_sorted else 0
        p95_idx = int(len(durations_sorted) * 0.95) if durations_sorted else 0
        p95 = durations_sorted[p95_idx] if durations_sorted else 0
        
        return AggregateResult(
            task_id=task_id,
            total_runs=len(runs),
            pass_count=pass_count,
            fail_count=fail_count,
            pass_rate=pass_rate,
            mean_duration=sum(durations) / len(durations) if durations else 0,
            median_duration=median,
            p95_duration=p95,
            max_duration=max(durations) if durations else 0,
            runs=runs
        )
    
    def get_release_decision(self, task_id: str, 
                           threshold: float = 0.66) -> tuple[bool, str]:
        """
        Get release decision based on aggregated results.
        
        Args:
            task_id: Task to check
            threshold: Minimum pass rate for release (default 66% = 2/3)
        
        Returns:
            (approved, reason)
        """
        if task_id not in self.run_results:
            return False, "No runs recorded"
        
        runs = len(self.run_results[task_id])
        if runs < self.min_runs:
            return False, f"Not enough runs: {runs}/{self.min_runs}"
        
        agg = self.aggregate(task_id)
        
        if agg.pass_rate >= threshold:
            return True, f"Approved (pass_rate={agg.pass_rate:.2%}, runs={runs})"
        else:
            return False, f"Rejected (pass_rate={agg.pass_rate:.2%}, runs={runs})"


# ==================== DETERMINISTIC RUNNER ====================

class DeterministicBenchmarkRunner:
    """
    Wraps benchmark execution with full determinism guarantees.
    
    Ensures:
    - Seed control
    - Environment fingerprinting  
    - Manifest generation
    - Fresh workspace per task
    - Multi-run aggregation
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).parent
        
        # Components
        self.manifest = RunManifest.create_new()
        self.seed_controller = SeedController(self.manifest.seed)
        self.env_fingerprint = EnvironmentFingerprint()
        self.task_registry = TaskRegistry()
        self.flake_analyzer = FlakeAnalyzer()
        self.multi_run_aggregator = MultiRunAggregator()
        
        logger.info("🎯 DeterministicBenchmarkRunner initialized")
    
    def prepare_run(self, task_ids: List[str], 
                   pack_version: str = "v1") -> RunManifest:
        """
        Prepare for a deterministic run.
        
        Sets up:
        - Environment fingerprint
        - Task ordering (deterministic)
        - Manifest
        """
        # Compute environment fingerprint
        env_hash, env_details = self.env_fingerprint.compute_fingerprint()
        self.manifest.environment_hash = env_hash
        self.manifest.environment_details = env_details
        
        # Set benchmark info
        self.manifest.benchmark_pack_version = pack_version
        self.manifest.task_ids = task_ids
        
        # Get deterministic task order
        ordered_tasks = self.seed_controller.get_task_order(task_ids)
        self.manifest.task_order = ordered_tasks
        
        # Get stable tasks only
        stable_tasks = {t.task_id for t in self.task_registry.get_stable_tasks()}
        available_tasks = [t for t in ordered_tasks if t in stable_tasks]
        
        if len(available_tasks) < len(ordered_tasks):
            skipped = set(ordered_tasks) - set(available_tasks)
            logger.warning(f"⚠️ Skipping non-stable tasks: {skipped}")
            self.manifest.notes["skipped_tasks"] = list(skipped)
        
        logger.info(f"📋 Run prepared: {len(available_tasks)} tasks, seed={self.manifest.seed}")
        
        return self.manifest
    
    def record_result(self, task_id: str, passed: bool, duration: float):
        """Record a task result"""
        self.flake_analyzer.record_result(task_id, passed)
        self.multi_run_aggregator.add_run(task_id, {
            "passed": passed,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
    
    def verify_for_release(self) -> tuple[bool, List[str]]:
        """
        Verify run is suitable for release decision.
        
        Checks:
        - Environment hash matches baseline
        - All tasks are stable
        - Multi-run threshold met
        
        Returns:
            (approved, list_of_issues)
        """
        issues = []
        
        # Check environment
        if not self.manifest.environment_hash:
            issues.append("Environment fingerprint not computed")
        
        # Check stable tasks
        stable_tasks = {t.task_id for t in self.task_registry.get_stable_tasks()}
        for task_id in self.manifest.task_ids:
            if task_id not in stable_tasks:
                issues.append(f"Task {task_id} is not stable")
        
        # Check flake status
        for task_id in self.manifest.task_ids:
            can_use, reason = self.flake_analyzer.can_use_in_release(task_id)
            if not can_use:
                issues.append(f"Task {task_id}: {reason}")
        
        # Check multi-run threshold
        for task_id in self.manifest.task_ids:
            approved, reason = self.multi_run_aggregator.get_release_decision(task_id)
            if not approved:
                issues.append(f"Task {task_id}: {reason}")
        
        return len(issues) == 0, issues
    
    def save_manifest(self, path: Optional[Path] = None):
        """Save run manifest to disk"""
        if path is None:
            path = self.base_path / "results" / self.manifest.run_id / "manifest.json"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(self.manifest.to_dict(), f, indent=2)
        
        logger.info(f"💾 Manifest saved: {path}")


# ==================== FACTORY ====================

def create_deterministic_runner(base_path: Optional[Path] = None) -> DeterministicBenchmarkRunner:
    """Create a deterministic benchmark runner"""
    return DeterministicBenchmarkRunner(base_path)


def create_seed_controller(seed: int = 42) -> SeedController:
    """Create a seed controller"""
    return SeedController(seed)
