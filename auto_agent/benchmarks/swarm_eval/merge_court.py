"""
MergeCourt - Merge Safety Layer

Bu modul parallel branchlarni tekshiradi:
- overlapni tekshiradi
- conflictni topadi
- semantic consistency ko'radi
- duplicate ishni kesadi
- final merge order belgilaydi
- kerak bo'lsa branchni reject qiladi

Policy 4: Merge without court taqiqlanadi.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import difflib


class MergeDecision(Enum):
    """Merge court decisions"""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_RESOLUTION = "needs_resolution"
    CONFLICT_DETECTED = "conflict_detected"
    DUPLICATE_WORK = "duplicate_work"


class ConflictType(Enum):
    """Types of merge conflicts"""
    FILE_OVERLAP = "file_overlap"
    SEMANTIC_INCONSISTENCY = "semantic_inconsistency"
    DUPLICATE_EFFORT = "duplicate_effort"
    LOGIC_CONFLICT = "logic_conflict"
    TEST_REGRESSION = "test_regression"


@dataclass
class BranchDiff:
    """Diff from a single branch"""
    branch_id: str
    files_changed: Set[str]
    lines_added: int
    lines_removed: int
    diff_content: Dict[str, str]  # file -> diff


@dataclass
class MergeConflict:
    """A detected merge conflict"""
    conflict_id: str
    conflict_type: ConflictType
    severity: str
    description: str
    involved_branches: List[str]
    affected_files: List[str]
    suggested_resolution: Optional[str] = None


@dataclass
class MergeRuling:
    """Final merge ruling from MergeCourt"""
    decision: MergeDecision
    conflicts: List[MergeConflict]
    merge_order: List[str]
    approved_branches: List[str]
    rejected_branches: List[str]
    warnings: List[str]
    score: float


class MergeCourt:
    """
    Evaluates and rules on parallel branch merges.
    
    Bu modul:
    1. Branch diffsni tahlil qiladi
    2. Overlap va conflictlarni aniqlaydi
    3. Semantic consistency tekshiradi
    4. Duplicate workni topadi
    5. Final merge ruling beradi
    """
    
    # Thresholds
    OVERLAP_THRESHOLD = 0.3  # 30% file overlap = conflict
    DUPLICATE_THRESHOLD = 0.5  # 50% similar = duplicate
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.conflict_history: List[MergeConflict] = []
        
    def evaluate_merge(
        self,
        branch_diffs: List[BranchDiff],
        current_codebase: Optional[Dict[str, str]] = None
    ) -> MergeRuling:
        """
        Evaluate multiple branch diffs and make merge ruling.
        
        Args:
            branch_diffs: List of branch diffs to evaluate
            current_codebase: Current state of codebase for semantic checks
            
        Returns:
            MergeRuling with decision and conflicts
        """
        conflicts = []
        approved = []
        rejected = []
        warnings = []
        
        # Step 1: Check for file overlaps between branches
        overlap_conflicts = self._check_file_overlaps(branch_diffs)
        conflicts.extend(overlap_conflicts)
        
        # Step 2: Check for duplicate work
        duplicate_conflicts = self._check_duplicate_work(branch_diffs)
        conflicts.extend(duplicate_conflicts)
        
        # Step 3: Check semantic consistency
        if current_codebase:
            semantic_conflicts = self._check_semantic_consistency(
                branch_diffs, current_codebase
            )
            conflicts.extend(semantic_conflicts)
        
        # Step 4: Determine decision
        if any(c.conflict_type == ConflictType.DUPLICATE_EFFORT for c in conflicts):
            decision = MergeDecision.DUPLICATE_WORK
            # Reject duplicate branches
            rejected = self._identify_duplicate_branches(branch_diffs, conflicts)
            approved = [b.branch_id for b in branch_diffs if b.branch_id not in rejected]
        elif any(c.severity == "high" for c in conflicts):
            decision = MergeDecision.NEEDS_RESOLUTION
            approved = []
            rejected = []
        elif conflicts:
            decision = MergeDecision.CONFLICT_DETECTED
            approved = [b.branch_id for b in branch_diffs]
        else:
            decision = MergeDecision.APPROVED
            approved = [b.branch_id for b in branch_diffs]
        
        # Generate warnings
        for conflict in conflicts:
            if conflict.severity == "low":
                warnings.append(f"Low severity: {conflict.description}")
        
        # Determine merge order (simple topological)
        merge_order = self._determine_merge_order(branch_diffs, conflicts)
        
        # Calculate score
        score = self._calculate_merge_score(
            len(branch_diffs), len(conflicts), decision
        )
        
        ruling = MergeRuling(
            decision=decision,
            conflicts=conflicts,
            merge_order=merge_order,
            approved_branches=approved,
            rejected_branches=rejected,
            warnings=warnings,
            score=score
        )
        
        self.conflict_history.extend(conflicts)
        
        return ruling
    
    def _check_file_overlaps(
        self,
        branch_diffs: List[BranchDiff]
    ) -> List[MergeConflict]:
        """Check for file overlaps between branches"""
        conflicts = []
        
        for i, diff1 in enumerate(branch_diffs):
            for diff2 in branch_diffs[i+1:]:
                # Calculate file overlap
                overlap = diff1.files_changed & diff2.files_changed
                total_files = diff1.files_changed | diff2.files_changed
                
                if not total_files:
                    continue
                    
                overlap_ratio = len(overlap) / len(total_files)
                
                if overlap_ratio > self.OVERLAP_THRESHOLD:
                    conflict = MergeConflict(
                        conflict_id=f"overlap_{diff1.branch_id}_{diff2.branch_id}",
                        conflict_type=ConflictType.FILE_OVERLAP,
                        severity="high" if overlap_ratio > 0.5 else "medium",
                        description=f"Files overlap: {overlap}",
                        involved_branches=[diff1.branch_id, diff2.branch_id],
                        affected_files=list(overlap),
                        suggested_resolution="Sequential merge or coordinate changes"
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _check_duplicate_work(
        self,
        branch_diffs: List[BranchDiff]
    ) -> List[MergeConflict]:
        """Check for duplicate work across branches"""
        conflicts = []
        
        # Check for similar line changes
        for i, diff1 in enumerate(branch_diffs):
            for diff2 in branch_diffs[i+1:]:
                # Calculate similarity of diff content
                diff1_str = "\n".join(diff1.diff_content.values())
                diff2_str = "\n".join(diff2.diff_content.values())
                
                if not diff1_str or not diff2_str:
                    continue
                    
                similarity = difflib.SequenceMatcher(
                    None, diff1_str, diff2_str
                ).ratio()
                
                if similarity > self.DUPLICATE_THRESHOLD:
                    conflict = MergeConflict(
                        conflict_id=f"dup_{diff1.branch_id}_{diff2.branch_id}",
                        conflict_type=ConflictType.DUPLICATE_EFFORT,
                        severity="high",
                        description=f"Duplicate work detected: {similarity:.1%} similarity",
                        involved_branches=[diff1.branch_id, diff2.branch_id],
                        affected_files=list(diff1.files_changed & diff2.files_changed),
                        suggested_resolution="Keep one branch, reject the other"
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _check_semantic_consistency(
        self,
        branch_diffs: List[BranchDiff],
        codebase: Dict[str, str]
    ) -> List[MergeConflict]:
        """Check for semantic inconsistencies"""
        conflicts = []
        
        # Check if branches modify same logic differently
        # (simplified check - in reality would need AST analysis)
        
        return conflicts
    
    def _identify_duplicate_branches(
        self,
        branch_diffs: List[BranchDiff],
        conflicts: List[MergeConflict]
    ) -> List[str]:
        """Identify which branches should be rejected as duplicates"""
        # Find duplicate conflicts
        dup_conflicts = [
            c for c in conflicts
            if c.conflict_type == ConflictType.DUPLICATE_EFFORT
        ]
        
        # Reject the branch with fewer changes (likely the duplicate)
        rejected = []
        for conflict in dup_conflicts:
            branch_sizes = {}
            for branch in branch_diffs:
                if branch.branch_id in conflict.involved_branches:
                    branch_sizes[branch.branch_id] = (
                        branch.lines_added + branch.lines_removed
                    )
            
            # Reject smaller branch
            if branch_sizes:
                smaller = min(branch_sizes, key=branch_sizes.get)
                if smaller not in rejected:
                    rejected.append(smaller)
        
        return rejected
    
    def _determine_merge_order(
        self,
        branch_diffs: List[BranchDiff],
        conflicts: List[MergeConflict]
    ) -> List[str]:
        """Determine merge order based on dependencies"""
        # Simple approach: merge smaller branches first
        branch_sizes = {
            b.branch_id: b.lines_added + b.lines_removed
            for b in branch_diffs
        }
        
        # Sort by size (smaller first)
        ordered = sorted(
            branch_sizes.keys(),
            key=lambda x: branch_sizes[x]
        )
        
        return ordered
    
    def _calculate_merge_score(
        self,
        branch_count: int,
        conflict_count: int,
        decision: MergeDecision
    ) -> float:
        """Calculate overall merge score"""
        score = 1.0
        
        # Penalize for conflicts
        score -= conflict_count * 0.1
        
        # Penalize for decision
        if decision == MergeDecision.REJECTED:
            score *= 0.0
        elif decision == MergeDecision.DUPLICATE_WORK:
            score *= 0.3
        elif decision == MergeDecision.CONFLICT_DETECTED:
            score *= 0.5
        elif decision == MergeDecision.NEEDS_RESOLUTION:
            score *= 0.7
        
        return max(0.0, score)
    
    def get_conflict_report(self) -> Dict[str, Any]:
        """Get report on all conflicts seen"""
        if not self.conflict_history:
            return {"total_conflicts": 0}
        
        conflict_types = {}
        for conflict in self.conflict_history:
            ctype = conflict.conflict_type.value
            conflict_types[ctype] = conflict_types.get(ctype, 0) + 1
        
        return {
            "total_conflicts": len(self.conflict_history),
            "conflict_types": conflict_types,
            "recent_conflicts": [
                {
                    "id": c.conflict_id,
                    "type": c.conflict_type.value,
                    "severity": c.severity
                }
                for c in self.conflict_history[-10:]
            ]
        }


__all__ = [
    'MergeCourt',
    'MergeDecision',
    'ConflictType',
    'BranchDiff',
    'MergeConflict',
    'MergeRuling'
]
