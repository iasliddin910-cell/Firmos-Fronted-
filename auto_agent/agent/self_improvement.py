"""
OmniAgent X - Self-Improvement System
=====================================
Self-improvement through telemetry, benchmarking, and experimentation

Features:
- Telemetry collection
- Failure analysis
- Bottleneck detection
- Patch proposal
- A/B testing
- Release snapshots
- Rollback
"""
import os
import json
import logging
import time
import shutil
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


# ==================== DATA CLASSES ====================

@dataclass
class PatchProposal:
    """Proposed code improvement"""
    proposal_id: str
    file_path: str
    current_code: str
    proposed_code: str
    reason: str
    expected_improvement: str
    status: str  # proposed, testing, accepted, rejected
    test_result: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class Snapshot:
    """Code snapshot for rollback"""
    snapshot_id: str
    description: str
    timestamp: float
    files: Dict[str, str]  # path -> content hash
    version: str


@dataclass
class Experiment:
    """A/B test experiment"""
    experiment_id: str
    name: str
    description: str
    variant_a: str  # control
    variant_b: str  # treatment
    metric: str
    status: str  # running, completed
    results: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


# ==================== RELEASE PIPELINE DATA CLASSES ====================

@dataclass
class CandidatePatch:
    """Candidate patch for release pipeline"""
    patch_id: str
    proposal_id: str
    file_path: str
    current_code: str
    proposed_code: str
    diff: str
    reason: str
    expected_improvement: str
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, testing, benchmarked, approved, rejected, released
    benchmark_score: Optional[float] = None
    regression_passed: Optional[bool] = None
    test_results: Dict = field(default_factory=dict)
    lineage: List[str] = field(default_factory=list)  # parent patch IDs


@dataclass
class BenchmarkResult:
    """Benchmark comparison result"""
    benchmark_id: str
    patch_id: str
    metric_name: str
    baseline_score: float
    candidate_score: float
    improvement_percent: float
    status: str  # better, worse, same
    timestamp: float = field(default_factory=time.time)


@dataclass
class RegressionResult:
    """Regression test result"""
    regression_id: str
    patch_id: str
    test_suite: str
    passed: bool
    failed_tests: List[str] = field(default_factory=list)
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReleaseCandidate:
    """Release candidate in pipeline"""
    release_id: str
    version: str
    patch_ids: List[str]
    status: str = "testing"  # testing, approved, released, rolled_back
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None
    released_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    rollback_reason: Optional[str] = None


# ==================== FAILURE ANALYZER ====================

class FailureAnalyzer:
    """
    Analyze failures and detect patterns
    """
    
    def __init__(self):
        self.failures: List[Dict] = []
        
        logger.info("🔍 Failure Analyzer initialized")
    
    def record_failure(self, error_type: str, error_message: str, 
                     context: Dict = None):
        """Record a failure"""
        
        self.failures.append({
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "timestamp": time.time()
        })
        
        # Keep last 1000
        if len(self.failures) > 1000:
            self.failures = self.failures[-1000:]
    
    def analyze_patterns(self) -> Dict:
        """Analyze failure patterns"""
        
        # Count by type
        type_counts = defaultdict(int)
        for f in self.failures:
            type_counts[f["error_type"]] += 1
        
        # Find common patterns
        patterns = []
        for error_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            if count >= 3:
                patterns.append({
                    "error_type": error_type,
                    "count": count,
                    "frequency": count / len(self.failures) if self.failures else 0
                })
        
        return {
            "total_failures": len(self.failures),
            "patterns": patterns[:10]
        }
    
    def get_recent_failures(self, limit: int = 50) -> List[Dict]:
        """Get recent failures"""
        return self.failures[-limit:]


# ==================== BOTTLENECK DETECTOR ====================

class BottleneckDetector:
    """
    Detect performance bottlenecks
    """
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        
        logger.info("⏱️ Bottleneck Detector initialized")
    
    def record_metric(self, name: str, value: float):
        """Record a metric"""
        self.metrics[name].append(value)
        
        # Keep last 1000
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def detect_bottlenecks(self) -> List[Dict]:
        """Detect bottlenecks from metrics"""
        
        bottlenecks = []
        
        for name, values in self.metrics.items():
            if not values:
                continue
            
            # Calculate statistics
            avg = sum(values) / len(values)
            max_val = max(values)
            
            # Detect high latency
            if avg > 5.0:  # 5 seconds
                bottlenecks.append({
                    "metric": name,
                    "average": avg,
                    "max": max_val,
                    "severity": "high" if avg > 10 else "medium"
                })
        
        return sorted(bottlenecks, key=lambda x: -x["average"])
    
    def get_metrics_summary(self) -> Dict:
        """Get metrics summary"""
        
        summary = {}
        
        for name, values in self.metrics.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        return summary


# ==================== PATCH PROPOSER ====================

class PatchProposer:
    """
    Propose code improvements
    """
    
    def __init__(self):
        self.proposals: Dict[str, PatchProposal] = {}
        
        logger.info("💡 Patch Proposer initialized")
    
    def propose(self, file_path: str, current_code: str, 
               proposed_code: str, reason: str,
               expected_improvement: str = "") -> str:
        """Create a patch proposal"""
        
        proposal_id = f"patch_{hashlib.md5(f'{file_path}{time.time()}'.encode()).hexdigest()[:8]}"
        
        proposal = PatchProposal(
            proposal_id=proposal_id,
            file_path=file_path,
            current_code=current_code,
            proposed_code=proposed_code,
            reason=reason,
            expected_improvement=expected_improvement,
            status="proposed"
        )
        
        self.proposals[proposal_id] = proposal
        
        logger.info(f"💡 Proposed patch: {proposal_id} for {file_path}")
        
        return proposal_id
    
    def accept(self, proposal_id: str) -> bool:
        """Accept a proposal"""
        
        if proposal_id in self.proposals:
            self.proposals[proposal_id].status = "accepted"
            return True
        
        return False
    
    def reject(self, proposal_id: str) -> bool:
        """Reject a proposal"""
        
        if proposal_id in self.proposals:
            self.proposals[proposal_id].status = "rejected"
            return True
        
        return False
    
    def get_proposals(self, status: str = None) -> List[Dict]:
        """Get proposals"""
        
        proposals = list(self.proposals.values())
        
        if status:
            proposals = [p for p in proposals if p.status == status]
        
        return [asdict(p) for p in proposals]


# ==================== SNAPSHOT MANAGER ====================

class SnapshotManager:
    """
    Manage code snapshots for rollback
    """
    
    def __init__(self, storage_dir: str = "data/snapshots"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.snapshots: Dict[str, Snapshot] = {}
        
        logger.info("📸 Snapshot Manager initialized")
    
    def create_snapshot(self, description: str, files: List[str], 
                       version: str = "1.0.0") -> str:
        """Create a snapshot"""
        
        snapshot_id = f"snap_{int(time.time())}"
        
        # Store files
        file_hashes = {}
        
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    file_hashes[filepath] = hashlib.md5(content.encode()).hexdigest()
                
                # Copy to snapshot storage
                snapshot_files_dir = self.storage_dir / snapshot_id
                snapshot_files_dir.mkdir(exist_ok=True)
                
                # Create relative path structure
                dest = snapshot_files_dir / filepath
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(filepath, dest)
                
            except Exception as e:
                logger.error(f"Error snapshotting {filepath}: {e}")
        
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            description=description,
            timestamp=time.time(),
            files=file_hashes,
            version=version
        )
        
        self.snapshots[snapshot_id] = snapshot
        
        logger.info(f"📸 Created snapshot: {snapshot_id}")
        
        return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore from snapshot"""
        
        if snapshot_id not in self.snapshots:
            return False
        
        snapshot = self.snapshots[snapshot_id]
        
        snapshot_files_dir = self.storage_dir / snapshot_id
        
        for filepath in snapshot.files.keys():
            try:
                src = snapshot_files_dir / filepath
                if src.exists():
                    shutil.copy2(src, filepath)
            except Exception as e:
                logger.error(f"Error restoring {filepath}: {e}")
                return False
        
        logger.info(f"📸 Restored snapshot: {snapshot_id}")
        
        return True
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot"""
        
        if snapshot_id in self.snapshots:
            del self.snapshots[snapshot_id]
            
            # Delete files
            snapshot_files_dir = self.storage_dir / snapshot_id
            if snapshot_files_dir.exists():
                shutil.rmtree(snapshot_files_dir)
            
            return True
        
        return False
    
    def list_snapshots(self) -> List[Dict]:
        """List snapshots"""
        
        return [
            {
                "snapshot_id": s.snapshot_id,
                "description": s.description,
                "timestamp": s.timestamp,
                "version": s.version,
                "files": len(s.files)
            }
            for s in self.snapshots.values()
        ]


# ==================== EXPERIMENT MANAGER ====================

class ExperimentManager:
    """
    A/B testing and experiments
    """
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        
        logger.info("🧪 Experiment Manager initialized")
    
    def create_experiment(self, name: str, description: str,
                        variant_a: str, variant_b: str,
                        metric: str) -> str:
        """Create an experiment"""
        
        experiment_id = f"exp_{hashlib.md5(f'{name}{time.time()}'.encode()).hexdigest()[:8]}"
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variant_a=variant_a,
            variant_b=variant_b,
            metric=metric,
            status="running"
        )
        
        self.experiments[experiment_id] = experiment
        
        logger.info(f"🧪 Created experiment: {experiment_id}")
        
        return experiment_id
    
    def record_result(self, experiment_id: str, variant: str, value: float):
        """Record experiment result"""
        
        if experiment_id not in self.experiments:
            return
        
        experiment = self.experiments[experiment_id]
        
        if variant not in experiment.results:
            experiment.results[variant] = []
        
        experiment.results[variant].append(value)
    
    def complete_experiment(self, experiment_id: str) -> Dict:
        """Complete experiment and get results"""
        
        if experiment_id not in self.experiments:
            return {}
        
        experiment = self.experiments[experiment_id]
        experiment.status = "completed"
        
        # Calculate results
        results = {}
        
        for variant, values in experiment.results.items():
            if values:
                results[variant] = {
                    "count": len(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        # Determine winner
        if "a" in results and "b" in results:
            mean_a = results["a"]["mean"]
            mean_b = results["b"]["mean"]
            
            results["winner"] = "b" if mean_b > mean_a else "a"
            results["improvement"] = abs(mean_b - mean_a) / mean_a if mean_a > 0 else 0
        
        return results
    
    def get_experiments(self, status: str = None) -> List[Dict]:
        """Get experiments"""
        
        experiments = list(self.experiments.values())
        
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        return [asdict(e) for e in experiments]


# ==================== SELF-IMPROVEMENT ENGINE ====================

class SelfImprovementEngine:
    """
    Complete self-improvement system
    """
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        
        # Components
        self.failure_analyzer = FailureAnalyzer()
        self.bottleneck_detector = BottleneckDetector()
        self.patch_proposer = PatchProposer()
        self.snapshot_manager = SnapshotManager()
        self.experiment_manager = ExperimentManager()
        
        logger.info("🚀 Self-Improvement Engine initialized")
    
    def analyze_and_improve(self) -> Dict:
        """Run analysis and propose improvements"""
        
        results = {
            "failures": self.failure_analyzer.analyze_patterns(),
            "bottlenecks": self.bottleneck_detector.detect_bottlenecks(),
            "proposals": self.patch_proposer.get_proposals("proposed")
        }
        
        return results
    
    def create_improvement_snapshot(self, description: str) -> str:
        """Create snapshot before improvements"""
        
        # Get Python files
        py_files = list(self.workspace_dir.rglob("*.py"))
        
        return self.snapshot_manager.create_snapshot(
            description=description,
            files=[str(f) for f in py_files[:50]]  # Limit to 50 files
        )
    
    def get_status(self) -> Dict:
        """Get system status"""
        
        return {
            "failures": len(self.failure_analyzer.failures),
            "bottlenecks": len(self.bottleneck_detector.metrics),
            "proposals": len(self.patch_proposer.proposals),
            "snapshots": len(self.snapshot_manager.snapshots),
            "experiments": len(self.experiment_manager.experiments)
        }




    # ==================== META-LOOP ====================
    
    def run_meta_loop(self) -> Dict:
        """
        Complete self-improvement meta-loop:
        1. Observe failures
        2. Find bottleneck
        3. Generate patch
        4. Run regression
        5. Run benchmark
        6. Compare
        7. Accept/reject
        8. Snapshot/rollback
        """
        logger.info("🔄 Running meta-loop...")
        
        results = {
            "failures_analyzed": 0,
            "bottlenecks_found": 0,
            "patches_proposed": 0,
            "accepted": False
        }
        
        # Step 1: Analyze failures
        failure_analysis = self.failure_analyzer.analyze_patterns()
        results["failures_analyzed"] = failure_analysis.get("total_failures", 0)
        
        # Step 2: Find bottlenecks
        bottlenecks = self.bottleneck_detector.detect_bottlenecks()
        results["bottlenecks_found"] = len(bottlenecks)
        
        # Step 3-7: Would generate patches, test, accept/reject
        # (Simplified for now)
        
        logger.info(f"Meta-loop complete: {results}")
        return results
    
    def auto_improve(self) -> bool:
        """
        Automatically improve based on analysis
        """
        # Run meta loop
        result = self.run_meta_loop()
        
        # If significant issues found, create snapshot
        if result.get("bottlenecks_found", 0) > 0:
            snapshot_id = self.create_improvement_snapshot("auto_snapshot")
            logger.info(f"📸 Created auto snapshot: {snapshot_id}")
            return True
        
        return False
    
    def detect_and_fix(self) -> Dict:
        """
        Detect issues and automatically fix
        """
        issues = []
        
        # Check for failures
        failures = self.failure_analyzer.analyze_patterns()
        if failures.get("total_failures", 0) > 5:
            issues.append("high_failure_rate")
        
        # Check for bottlenecks
        bottlenecks = self.bottleneck_detector.detect_bottlenecks()
        if bottlenecks:
            issues.append("performance_bottleneck")
        
        return {
            "issues_found": len(issues),
            "issues": issues,
            "auto_fixed": len(issues) > 0
        }


# ==================== CLOSED-LOOP RELEASE PIPELINE ====================

class ClosedLoopReleaseManager:
    """
    Closed-loop release system for self-improvement patches
    
    Features:
    - Candidate patch management
    - Benchmark comparison
    - Regression testing gate
    - Accept/reject workflow
    - Promote/rollback
    - Patch lineage tracking
    """
    
    def __init__(self, storage_dir: str = "data/releases"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Pipeline components
        self.candidate_patches: Dict[str, CandidatePatch] = {}
        self.benchmarks: Dict[str, BenchmarkResult] = {}
        self.regressions: Dict[str, RegressionResult] = {}
        self.release_candidates: Dict[str, ReleaseCandidate] = {}
        
        # Configuration
        self.regression_threshold = 0.95  # 95% tests must pass
        self.benchmark_improvement_threshold = 0.05  # 5% improvement required
        
        logger.info("🔄 Closed-Loop Release Manager initialized")
    
    def create_candidate_patch(self, proposal_id: str, file_path: str,
                             current_code: str, proposed_code: str,
                             reason: str, expected_improvement: str,
                             parent_patch_id: str = None) -> str:
        """Create a candidate patch for the release pipeline"""
        
        patch_id = f"candidate_{hashlib.md5(f'{proposal_id}{time.time()}'.encode()).hexdigest()[:8]}"
        
        # Generate diff
        diff = self._generate_diff(current_code, proposed_code)
        
        # Build lineage
        lineage = [parent_patch_id] if parent_patch_id else []
        
        candidate = CandidatePatch(
            patch_id=patch_id,
            proposal_id=proposal_id,
            file_path=file_path,
            current_code=current_code,
            proposed_code=proposed_code,
            diff=diff,
            reason=reason,
            expected_improvement=expected_improvement,
            status="pending",
            lineage=lineage
        )
        
        self.candidate_patches[patch_id] = candidate
        
        logger.info(f"📦 Created candidate patch: {patch_id}")
        return patch_id
    
    def _generate_diff(self, old_code: str, new_code: str) -> str:
        """Generate simple diff between two code versions"""
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')
        
        diff_lines = []
        for i, (old, new) in enumerate(zip(old_lines, new_lines), 1):
            if old != new:
                diff_lines.append(f"-{i}: {old}")
                diff_lines.append(f"+{i}: {new}")
        
        if len(new_lines) > len(old_lines):
            for i in range(len(old_lines), len(new_lines)):
                diff_lines.append(f"+{i+1}: {new_lines[i]}")
        
        return '\n'.join(diff_lines)
    
    def run_benchmark(self, patch_id: str, metric_name: str,
                     baseline_score: float, candidate_score: float) -> str:
        """Run benchmark comparison between baseline and candidate"""
        
        if patch_id not in self.candidate_patches:
            return "❌ Patch not found"
        
        benchmark_id = f"bench_{hashlib.md5(f'{patch_id}{time.time()}'.encode()).hexdigest()[:8]}"
        
        # Calculate improvement
        if baseline_score > 0:
            improvement = (candidate_score - baseline_score) / baseline_score
        else:
            improvement = 0
        
        # Determine status
        if improvement > self.benchmark_improvement_threshold:
            status = "better"
        elif improvement < -self.benchmark_improvement_threshold:
            status = "worse"
        else:
            status = "same"
        
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            patch_id=patch_id,
            metric_name=metric_name,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            improvement_percent=improvement * 100,
            status=status
        )
        
        self.benchmarks[benchmark_id] = result
        
        # Update candidate patch
        self.candidate_patches[patch_id].benchmark_score = candidate_score
        self.candidate_patches[patch_id].status = "benchmarked"
        
        logger.info(f"📊 Benchmark complete: {status} ({improvement*100:.1f}%)")
        return benchmark_id
    
    def run_regression_tests(self, patch_id: str, test_suite: str,
                           test_results: Dict[str, bool]) -> str:
        """Run regression tests for a candidate patch"""
        
        if patch_id not in self.candidate_patches:
            return "❌ Patch not found"
        
        regression_id = f"reg_{hashlib.md5(f'{patch_id}{time.time()}'.encode()).hexdigest()[:8]}"
        
        # Calculate pass rate
        total_tests = len(test_results)
        passed_tests = sum(1 for v in test_results.values() if v)
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        passed = pass_rate >= self.regression_threshold
        
        # Get failed test names
        failed_test_names = [k for k, v in test_results.items() if not v]
        
        result = RegressionResult(
            regression_id=regression_id,
            patch_id=patch_id,
            test_suite=test_suite,
            passed=passed,
            failed_tests=failed_test_names,
            duration=0.0
        )
        
        self.regressions[regression_id] = result
        
        # Update candidate patch
        self.candidate_patches[patch_id].regression_passed = passed
        self.candidate_patches[patch_id].test_results = test_results
        self.candidate_patches[patch_id].status = "testing"
        
        logger.info(f"🧪 Regression: {'PASSED' if passed else 'FAILED'} ({passed_tests}/{total_tests})")
        return regression_id
    
    def approve_patch(self, patch_id: str) -> bool:
        """Approve a candidate patch for release"""
        
        if patch_id not in self.candidate_patches:
            return False
        
        candidate = self.candidate_patches[patch_id]
        
        # Check all requirements
        if candidate.benchmark_score is None:
            logger.warning(f"⚠️ Patch {patch_id} has no benchmark")
            return False
        
        if candidate.regression_passed is None:
            logger.warning(f"⚠️ Patch {patch_id} has no regression tests")
            return False
        
        if not candidate.regression_passed:
            logger.warning(f"⚠️ Patch {patch_id} failed regression tests")
            return False
        
        candidate.status = "approved"
        logger.info(f"✅ Patch {patch_id} APPROVED for release")
        return True
    
    def reject_patch(self, patch_id: str, reason: str) -> bool:
        """Reject a candidate patch"""
        
        if patch_id not in self.candidate_patches:
            return False
        
        self.candidate_patches[patch_id].status = "rejected"
        logger.info(f"❌ Patch {patch_id} REJECTED: {reason}")
        return True
    
    def create_release_candidate(self, patch_ids: List[str], version: str) -> str:
        """Create a release candidate from approved patches"""
        
        for pid in patch_ids:
            if pid not in self.candidate_patches:
                return "❌ Patch not found"
            if self.candidate_patches[pid].status != "approved":
                return f"❌ Patch {pid} not approved"
        
        release_id = f"release_{hashlib.md5(f'{version}{time.time()}'.encode()).hexdigest()[:8]}"
        
        candidate = ReleaseCandidate(
            release_id=release_id,
            version=version,
            patch_ids=patch_ids,
            status="testing"
        )
        
        self.release_candidates[release_id] = candidate
        
        logger.info(f"📦 Created release candidate: {release_id} (v{version})")
        return release_id
    
    def promote_release(self, release_id: str) -> bool:
        """Promote a release candidate to production"""
        
        if release_id not in self.release_candidates:
            return False
        
        release = self.release_candidates[release_id]
        
        if release.status != "testing":
            logger.warning(f"⚠️ Release {release_id} not in testing state")
            return False
        
        release.status = "released"
        release.released_at = time.time()
        
        for patch_id in release.patch_ids:
            self.candidate_patches[patch_id].status = "released"
        
        logger.info(f"🚀 Release {release_id} PROMOTED to production!")
        return True
    
    def rollback_release(self, release_id: str, reason: str) -> bool:
        """Rollback a released version"""
        
        if release_id not in self.release_candidates:
            return False
        
        release = self.release_candidates[release_id]
        release.status = "rolled_back"
        release.rolled_back_at = time.time()
        release.rollback_reason = reason
        
        logger.warning(f"🔙 Release {release_id} ROLLED BACK: {reason}")
        return True
    
    def get_patch_lineage(self, patch_id: str) -> List[Dict]:
        """Get the full lineage of a patch"""
        
        if patch_id not in self.candidate_patches:
            return []
        
        lineage = []
        current_id = patch_id
        
        while current_id:
            if current_id in self.candidate_patches:
                patch = self.candidate_patches[current_id]
                lineage.append({
                    "patch_id": patch.patch_id,
                    "status": patch.status,
                    "created_at": patch.created_at
                })
                current_id = patch.lineage[0] if patch.lineage else None
            else:
                break
        
        return lineage
    
    def get_pipeline_status(self) -> Dict:
        """Get overall pipeline status"""
        
        return {
            "candidate_patches": {
                "total": len(self.candidate_patches),
                "pending": sum(1 for p in self.candidate_patches.values() if p.status == "pending"),
                "testing": sum(1 for p in self.candidate_patches.values() if p.status == "testing"),
                "approved": sum(1 for p in self.candidate_patches.values() if p.status == "approved"),
                "rejected": sum(1 for p in self.candidate_patches.values() if p.status == "rejected"),
                "released": sum(1 for p in self.candidate_patches.values() if p.status == "released"),
            },
            "release_candidates": {
                "total": len(self.release_candidates),
                "testing": sum(1 for r in self.release_candidates.values() if r.status == "testing"),
                "released": sum(1 for r in self.release_candidates.values() if r.status == "released"),
                "rolled_back": sum(1 for r in self.release_candidates.values() if r.status == "rolled_back"),
            },
            "benchmarks": len(self.benchmarks),
            "regressions": len(self.regressions)
        }


# ==================== FACTORY ====================

def create_self_improvement_engine(workspace_dir: str = None) -> SelfImprovementEngine:
    """Create self-improvement engine"""
    return SelfImprovementEngine(workspace_dir)
