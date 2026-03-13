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


# ==================== FACTORY ====================

def create_self_improvement_engine(workspace_dir: str = None) -> SelfImprovementEngine:
    """Create self-improvement engine"""
    return SelfImprovementEngine(workspace_dir)
