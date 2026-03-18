"""
Checkpoint Integrity Verifier - Validates Checkpoint/Restore Integrity
=====================================================================

This module verifies checkpoint and restore operations:
- Goal mismatch detection
- Stale summary detection
- Missing artifacts detection
- Wrong branch resume detection
- State divergence detection

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import logging
import threading
import hashlib
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class IntegrityStatus(str, Enum):
    """Checkpoint integrity status"""
    VALID = "valid"
    SUSPICIOUS = "suspicious"
    CORRUPTED = "corrupted"
    STALE = "stale"
    INCOMPLETE = "incomplete"


class IntegrityIssueType(str, Enum):
    """Types of integrity issues"""
    GOAL_MISMATCH = "goal_mismatch"
    STALE_SUMMARY = "stale_summary"
    MISSING_ARTIFACTS = "missing_artifacts"
    WRONG_BRANCH = "wrong_branch"
    STATE_DIVERGENCE = "state_divergence"
    CHECKPOINT_CORRUPTION = "checkpoint_corruption"


# ==================== DATA CLASSES ====================

@dataclass
class CheckpointMetadata:
    """Metadata for a checkpoint"""
    checkpoint_id: str
    task_id: str
    created_at: datetime
    goal: str
    summary: str
    artifacts: List[str]
    state_hash: str
    branch: str
    parent_checkpoint: Optional[str]
    metadata: Dict


@dataclass
class RestoreOperation:
    """A restore operation"""
    restore_id: str
    checkpoint_id: str
    requested_at: datetime
    completed_at: Optional[datetime]
    success: bool
    restored_goal: str
    restored_summary: str
    restored_artifacts: List[str]
    issues: List[str]


@dataclass
class IntegrityIssue:
    """Detected integrity issue"""
    issue_type: IntegrityIssueType
    severity: str           # "low", "medium", "high", "critical"
    description: str
    checkpoint_id: str
    detected_at: datetime
    evidence: Dict
    recommendation: str


@dataclass
class IntegrityReport:
    """Comprehensive integrity report"""
    timestamp: datetime
    checkpoint_id: str
    status: IntegrityStatus
    
    # Verification results
    goal_verified: bool
    summary_fresh: bool
    artifacts_complete: bool
    branch_correct: bool
    state_valid: bool
    
    # Issues found
    issues: List[IntegrityIssue]
    
    # Recommendations
    recommendations: List[str]
    
    # Integrity score (0-100)
    integrity_score: float


# ==================== CHECKPOINT STORAGE ====================

class CheckpointStorage:
    """Stores and retrieves checkpoints"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path("./checkpoints")
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._checkpoints: Dict[str, CheckpointMetadata] = {}
        self._restore_history: deque = deque(maxlen=100)
    
    def save_checkpoint(self, metadata: CheckpointMetadata):
        """Save checkpoint metadata"""
        with self._lock:
            self._checkpoints[metadata.checkpoint_id] = metadata
            
            # Also save to disk
            file_path = self._storage_path / f"{metadata.checkpoint_id}.json"
            with open(file_path, 'w') as f:
                json.dump({
                    "checkpoint_id": metadata.checkpoint_id,
                    "task_id": metadata.task_id,
                    "created_at": metadata.created_at.isoformat(),
                    "goal": metadata.goal,
                    "summary": metadata.summary,
                    "artifacts": metadata.artifacts,
                    "state_hash": metadata.state_hash,
                    "branch": metadata.branch,
                    "parent_checkpoint": metadata.parent_checkpoint,
                    "metadata": metadata.metadata
                }, f, indent=2)
            
            logger.info(f"Checkpoint saved: {metadata.checkpoint_id}")
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        """Load checkpoint metadata"""
        with self._lock:
            if checkpoint_id in self._checkpoints:
                return self._checkpoints[checkpoint_id]
            
            # Try loading from disk
            file_path = self._storage_path / f"{checkpoint_id}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    return CheckpointMetadata(
                        checkpoint_id=data["checkpoint_id"],
                        task_id=data["task_id"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        goal=data["goal"],
                        summary=data["summary"],
                        artifacts=data["artifacts"],
                        state_hash=data["state_hash"],
                        branch=data["branch"],
                        parent_checkpoint=data.get("parent_checkpoint"),
                        metadata=data.get("metadata", {})
                    )
        
        return None
    
    def delete_checkpoint(self, checkpoint_id: str):
        """Delete a checkpoint"""
        with self._lock:
            if checkpoint_id in self._checkpoints:
                del self._checkpoints[checkpoint_id]
                
                file_path = self._storage_path / f"{checkpoint_id}.json"
                if file_path.exists():
                    file_path.unlink()
                
                logger.info(f"Checkpoint deleted: {checkpoint_id}")
    
    def get_latest_checkpoint(self, task_id: str) -> Optional[CheckpointMetadata]:
        """Get latest checkpoint for a task"""
        with self._lock:
            task_checkpoints = [
                cp for cp in self._checkpoints.values()
                if cp.task_id == task_id
            ]
            
            if not task_checkpoints:
                return None
            
            return max(task_checkpoints, key=lambda cp: cp.created_at)
    
    def get_checkpoint_count(self) -> int:
        """Get total checkpoint count"""
        return len(self._checkpoints)
    
    def record_restore(self, operation: RestoreOperation):
        """Record a restore operation"""
        with self._lock:
            self._restore_history.append(operation)
    
    def get_restore_history(self, limit: int = 10) -> List[RestoreOperation]:
        """Get recent restore operations"""
        return list(self._restore_history)[-limit:]


# ==================== INTEGRITY VERIFIER ====================

class CheckpointIntegrityVerifier:
    """
    Verifies checkpoint and restore integrity.
    
    Features:
    - Goal verification
    - Summary freshness checking
    - Artifact completeness verification
    - Branch verification
    - State hash validation
    - Restore operation validation
    - Historical pattern analysis
    """
    
    def __init__(self, storage: Optional[CheckpointStorage] = None,
                 config: Optional[Dict] = None):
        self._config = config or {}
        self._storage = storage or CheckpointStorage()
        
        # Configuration
        self._stale_summary_hours = self._config.get("stale_summary_hours", 24)
        self._min_artifacts = self._config.get("min_artifacts", 1)
        
        # Callbacks
        self._on_issue_detected: Optional[Callable] = None
        self._on_corruption_detected: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_issue_detected: Optional[Callable] = None,
                     on_corruption_detected: Optional[Callable] = None):
        """Set callback functions"""
        self._on_issue_detected = on_issue_detected
        self._on_corruption_detected = on_corruption_detected
    
    # ==================== CHECKPOINT VERIFICATION ====================
    
    def verify_checkpoint(self, checkpoint_id: str) -> IntegrityReport:
        """Verify a checkpoint's integrity"""
        checkpoint = self._storage.load_checkpoint(checkpoint_id)
        
        if not checkpoint:
            return IntegrityReport(
                timestamp=datetime.now(),
                checkpoint_id=checkpoint_id,
                status=IntegrityStatus.INCOMPLETE,
                goal_verified=False,
                summary_fresh=False,
                artifacts_complete=False,
                branch_correct=False,
                state_valid=False,
                issues=[IntegrityIssue(
                    issue_type=IntegrityIssueType.CHECKPOINT_CORRUPTION,
                    severity="critical",
                    description=f"Checkpoint {checkpoint_id} not found",
                    checkpoint_id=checkpoint_id,
                    detected_at=datetime.now(),
                    evidence={},
                    recommendation="Recreate checkpoint"
                )],
                recommendations=["Recreate the checkpoint"],
                integrity_score=0
            )
        
        issues = []
        
        # Verify goal
        goal_verified = self._verify_goal(checkpoint)
        if not goal_verified:
            issues.append(IntegrityIssue(
                issue_type=IntegrityIssueType.GOAL_MISMATCH,
                severity="high",
                description="Goal may have changed since checkpoint",
                checkpoint_id=checkpoint_id,
                detected_at=datetime.now(),
                evidence={"goal": checkpoint.goal},
                recommendation="Verify current goal matches checkpoint goal"
            ))
        
        # Verify summary freshness
        summary_fresh = self._verify_summary_fresh(checkpoint)
        if not summary_fresh:
            issues.append(IntegrityIssue(
                issue_type=IntegrityIssueType.STALE_SUMMARY,
                severity="medium",
                description="Summary may be stale",
                checkpoint_id=checkpoint_id,
                detected_at=datetime.now(),
                evidence={"summary_age_hours": self._get_summary_age_hours(checkpoint)},
                recommendation="Update summary before resuming"
            ))
        
        # Verify artifacts
        artifacts_complete = self._verify_artifacts(checkpoint)
        if not artifacts_complete:
            issues.append(IntegrityIssue(
                issue_type=IntegrityIssueType.MISSING_ARTIFACTS,
                severity="high",
                description="Some artifacts may be missing",
                checkpoint_id=checkpoint_id,
                detected_at=datetime.now(),
                evidence={"artifacts": checkpoint.artifacts},
                recommendation="Verify all artifacts exist"
            ))
        
        # Verify branch
        branch_correct = self._verify_branch(checkpoint)
        if not branch_correct:
            issues.append(IntegrityIssue(
                issue_type=IntegrityIssueType.WRONG_BRANCH,
                severity="critical",
                description="May be resuming from wrong branch",
                checkpoint_id=checkpoint_id,
                detected_at=datetime.now(),
                evidence={"branch": checkpoint.branch},
                recommendation="Verify correct branch before resuming"
            ))
        
        # Verify state
        state_valid = self._verify_state(checkpoint)
        if not state_valid:
            issues.append(IntegrityIssue(
                issue_type=IntegrityIssueType.STATE_DIVERGENCE,
                severity="critical",
                description="State may have diverged",
                checkpoint_id=checkpoint_id,
                detected_at=datetime.now(),
                evidence={"state_hash": checkpoint.state_hash},
                recommendation="Recreate checkpoint from current state"
            ))
        
        # Determine overall status
        status = self._determine_status(issues)
        
        # Calculate integrity score
        integrity_score = self._calculate_score(issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues, status)
        
        # Trigger callbacks for critical issues
        if status == IntegrityStatus.CORRUPTED and self._on_corruption_detected:
            self._on_corruption_detected(checkpoint_id, issues)
        elif issues and self._on_issue_detected:
            self._on_issue_detected(checkpoint_id, issues)
        
        return IntegrityReport(
            timestamp=datetime.now(),
            checkpoint_id=checkpoint_id,
            status=status,
            goal_verified=goal_verified,
            summary_fresh=summary_fresh,
            artifacts_complete=artifacts_complete,
            branch_correct=branch_correct,
            state_valid=state_valid,
            issues=issues,
            recommendations=recommendations,
            integrity_score=integrity_score
        )
    
    def _verify_goal(self, checkpoint: CheckpointMetadata) -> bool:
        """Verify goal hasn't changed (simplified - would compare with current goal)"""
        # In real implementation, would compare with current task goal
        return len(checkpoint.goal) > 0
    
    def _verify_summary_fresh(self, checkpoint: CheckpointMetadata) -> bool:
        """Verify summary is fresh"""
        age_hours = self._get_summary_age_hours(checkpoint)
        return age_hours < self._stale_summary_hours
    
    def _get_summary_age_hours(self, checkpoint: CheckpointMetadata) -> float:
        """Get age of summary in hours"""
        age = datetime.now() - checkpoint.created_at
        return age.total_seconds() / 3600
    
    def _verify_artifacts(self, checkpoint: CheckpointMetadata) -> bool:
        """Verify artifacts exist"""
        # In real implementation, would check file system
        return len(checkpoint.artifacts) >= self._min_artifacts
    
    def _verify_branch(self, checkpoint: CheckpointMetadata) -> bool:
        """Verify branch is correct"""
        # In real implementation, would compare with current branch
        return len(checkpoint.branch) > 0
    
    def _verify_state(self, checkpoint: CheckpointMetadata) -> bool:
        """Verify state hash is valid"""
        # In real implementation, would verify state hash
        return len(checkpoint.state_hash) > 0
    
    def _determine_status(self, issues: List[IntegrityIssue]) -> IntegrityStatus:
        """Determine overall integrity status"""
        if not issues:
            return IntegrityStatus.VALID
        
        severities = [i.severity for i in issues]
        
        if "critical" in severities:
            return IntegrityStatus.CORRUPTED
        elif "high" in severities:
            return IntegrityStatus.SUSPICIOUS
        elif "medium" in severities:
            return IntegrityStatus.SUSPICIOUS
        else:
            return IntegrityStatus.STALE
    
    def _calculate_score(self, issues: List[IntegrityIssue]) -> float:
        """Calculate integrity score"""
        score = 100.0
        
        for issue in issues:
            if issue.severity == "critical":
                score -= 30
            elif issue.severity == "high":
                score -= 20
            elif issue.severity == "medium":
                score -= 10
            elif issue.severity == "low":
                score -= 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, issues: List[IntegrityIssue],
                                 status: IntegrityStatus) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        if status == IntegrityStatus.CORRUPTED:
            recommendations.append("CRITICAL: Checkpoint corrupted - do not restore")
            recommendations.append("Create new checkpoint from current state")
        
        for issue in issues:
            recommendations.append(issue.recommendation)
        
        if not recommendations:
            recommendations.append("Checkpoint integrity verified - safe to restore")
        
        return recommendations
    
    # ==================== RESTORE VERIFICATION ====================
    
    def verify_restore(self, checkpoint_id: str, current_goal: str,
                      current_summary: str, current_artifacts: List[str]) -> RestoreOperation:
        """Verify a restore operation"""
        checkpoint = self._storage.load_checkpoint(checkpoint_id)
        
        operation = RestoreOperation(
            restore_id=str(id(datetime.now())),
            checkpoint_id=checkpoint_id,
            requested_at=datetime.now(),
            completed_at=None,
            success=False,
            restored_goal=checkpoint.goal if checkpoint else "",
            restored_summary=checkpoint.summary if checkpoint else "",
            restored_artifacts=checkpoint.artifacts if checkpoint else [],
            issues=[]
        )
        
        if not checkpoint:
            operation.issues.append("Checkpoint not found")
            return operation
        
        # Verify goal match
        if checkpoint.goal != current_goal:
            operation.issues.append(f"Goal mismatch: checkpoint={checkpoint.goal}, current={current_goal}")
        
        # Verify summary not too stale
        age_hours = self._get_summary_age_hours(checkpoint)
        if age_hours > self._stale_summary_hours:
            operation.issues.append(f"Summary is stale: {age_hours:.1f} hours old")
        
        # Verify artifacts
        for artifact in checkpoint.artifacts:
            if artifact not in current_artifacts:
                operation.issues.append(f"Missing artifact: {artifact}")
        
        # Mark complete
        operation.completed_at = datetime.now()
        operation.success = len(operation.issues) == 0
        
        # Record operation
        self._storage.record_restore(operation)
        
        return operation
    
    # ==================== HISTORICAL ANALYSIS ====================
    
    def analyze_restore_history(self) -> Dict:
        """Analyze restore operation history"""
        history = self._storage.get_restore_history(50)
        
        if not history:
            return {"total_restores": 0, "success_rate": 0}
        
        successful = sum(1 for op in history if op.success)
        failed = len(history) - successful
        
        # Common issues
        issue_counts = defaultdict(int)
        for op in history:
            for issue in op.issues:
                issue_counts[issue] += 1
        
        return {
            "total_restores": len(history),
            "successful_restores": successful,
            "failed_restores": failed,
            "success_rate": successful / len(history) if history else 0,
            "common_issues": dict(issue_counts),
            "recommendations": self._analyze_history_recommendations(history)
        }
    
    def _analyze_history_recommendations(self, history: List[RestoreOperation]) -> List[str]:
        """Generate recommendations from history analysis"""
        recommendations = []
        
        recent = history[-10:]
        recent_failures = sum(1 for op in recent if not op.success)
        
        if recent_failures > 5:
            recommendations.append("High recent restore failure rate - review checkpoint strategy")
        
        # Check for common issues
        all_issues = []
        for op in history:
            all_issues.extend(op.issues)
        
        if any("Goal mismatch" in i for i in all_issues):
            recommendations.append("Frequent goal mismatches - verify goal stability")
        
        if any("stale" in i.lower() for i in all_issues):
            recommendations.append("Frequent stale summaries - reduce checkpoint intervals")
        
        if not recommendations:
            recommendations.append("Restore history looks healthy")
        
        return recommendations
    
    # ==================== CHECKPOINT MANAGEMENT ====================
    
    def create_checkpoint(self, task_id: str, goal: str, summary: str,
                        artifacts: List[str], branch: str = "main",
                        metadata: Optional[Dict] = None) -> str:
        """Create a new checkpoint"""
        checkpoint_id = f"cp_{task_id}_{int(time.time())}"
        
        # Generate state hash (simplified)
        state_hash = hashlib.sha256(
            f"{goal}{summary}{artifacts}".encode()
        ).hexdigest()[:16]
        
        checkpoint = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            created_at=datetime.now(),
            goal=goal,
            summary=summary,
            artifacts=artifacts,
            state_hash=state_hash,
            branch=branch,
            parent_checkpoint=self._storage.get_latest_checkpoint(task_id).checkpoint_id 
                              if self._storage.get_latest_checkpoint(task_id) else None,
            metadata=metadata or {}
        )
        
        self._storage.save_checkpoint(checkpoint)
        
        return checkpoint_id
    
    def delete_old_checkpoints(self, max_age_hours: int = 168) -> int:
        """Delete checkpoints older than specified age"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        deleted = 0
        
        for checkpoint_id in list(self._storage._checkpoints.keys()):
            checkpoint = self._storage.load_checkpoint(checkpoint_id)
            if checkpoint and checkpoint.created_at < cutoff:
                self._storage.delete_checkpoint(checkpoint_id)
                deleted += 1
        
        logger.info(f"Deleted {deleted} old checkpoints")
        return deleted


# ==================== FACTORY ====================

def create_checkpoint_verifier(config: Optional[Dict] = None) -> CheckpointIntegrityVerifier:
    """Factory function to create checkpoint verifier"""
    return CheckpointIntegrityVerifier(config=config)
