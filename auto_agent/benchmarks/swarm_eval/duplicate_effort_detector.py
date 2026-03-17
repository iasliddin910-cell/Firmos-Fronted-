"""
DuplicateEffortDetector - Duplicate Work Detection

Bu modul bir xil ish ustida ishlayotgan workerlarni aniqlaydi:
- bir xil fayl
- bir xil log
- bir xil root cause

Policy 3: Duplicate effort penalti oladi.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import difflib


class DuplicateType(Enum):
    """Types of duplicate effort"""
    FILE_OVERLAP = "file_overlap"
    ROOT_CAUSE = "root_cause"
    LOG_MESSAGE = "log_message"
    SEARCH_QUERY = "search_query"
    CODE_SNIPPET = "code_snippet"


@dataclass
class DuplicateInstance:
    """A detected duplicate effort"""
    duplicate_id: str
    duplicate_type: DuplicateType
    severity: str
    workers_involved: List[str]
    overlapping_items: List[str]
    wasted_effort_ratio: float
    suggestion: str


class DuplicateEffortDetector:
    """
    Detects duplicate effort across workers.
    
    Policy 3: Duplicate effort penalti oladi.
    """
    
    # Thresholds
    FILE_OVERLAP_THRESHOLD = 0.3
    ROOT_CAUSE_SIMILARITY = 0.6
    CODE_SIMILARITY_THRESHOLD = 0.7
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.worker_files: Dict[str, Set[str]] = {}
        self.worker_analyses: Dict[str, List[str]] = {}
        self.duplicates_found: List[DuplicateInstance] = []
        
    def register_worker_file_access(
        self,
        worker_id: str,
        files_accessed: List[str]
    ) -> None:
        """Register files accessed by a worker"""
        if worker_id not in self.worker_files:
            self.worker_files[worker_id] = set()
        self.worker_files[worker_id].update(files_accessed)
    
    def register_worker_analysis(
        self,
        worker_id: str,
        analysis: List[str]
    ) -> None:
        """Register analysis/root cause findings by a worker"""
        if worker_id not in self.worker_analyses:
            self.worker_analyses[worker_id] = []
        self.worker_analyses[worker_id].extend(analysis)
    
    def detect_duplicates(self) -> List[DuplicateInstance]:
        """Detect all duplicate efforts"""
        duplicates = []
        
        # Check file overlaps
        file_duplicates = self._detect_file_overlaps()
        duplicates.extend(file_duplicates)
        
        # Check root cause overlaps
        root_cause_duplicates = self._detect_root_cause_duplicates()
        duplicates.extend(root_cause_duplicates)
        
        self.duplicates_found.extend(duplicates)
        
        return duplicates
    
    def _detect_file_overlaps(self) -> List[DuplicateInstance]:
        """Detect file access overlaps"""
        duplicates = []
        workers = list(self.worker_files.keys())
        
        for i, w1 in enumerate(workers):
            for w2 in workers[i+1:]:
                files1 = self.worker_files.get(w1, set())
                files2 = self.worker_files.get(w2, set())
                
                if not files1 or not files2:
                    continue
                
                overlap = files1 & files2
                union = files1 | files2
                
                if not union:
                    continue
                    
                overlap_ratio = len(overlap) / len(union)
                
                if overlap_ratio > self.FILE_OVERLAP_THRESHOLD:
                    duplicate = DuplicateInstance(
                        duplicate_id=f"file_dup_{w1}_{w2}",
                        duplicate_type=DuplicateType.FILE_OVERLAP,
                        severity="high" if overlap_ratio > 0.5 else "medium",
                        workers_involved=[w1, w2],
                        overlapping_items=list(overlap),
                        wasted_effort_ratio=overlap_ratio,
                        suggestion="Coordinate file access to avoid duplicate work"
                    )
                    duplicates.append(duplicate)
        
        return duplicates
    
    def _detect_root_cause_duplicates(self) -> List[DuplicateInstance]:
        """Detect root cause analysis overlaps"""
        duplicates = []
        workers = list(self.worker_analyses.keys())
        
        for i, w1 in enumerate(workers):
            for w2 in workers[i+1:]:
                analyses1 = self.worker_analyses.get(w1, [])
                analyses2 = self.worker_analyses.get(w2, [])
                
                if not analyses1 or not analyses2:
                    continue
                
                # Calculate similarity
                max_similarity = 0.0
                most_similar = []
                
                for a1 in analyses1:
                    for a2 in analyses2:
                        similarity = difflib.SequenceMatcher(
                            None, a1.lower(), a2.lower()
                        ).ratio()
                        
                        if similarity > max_similarity:
                            max_similarity = similarity
                            most_similar = [a1, a2]
                
                if max_similarity > self.ROOT_CAUSE_SIMILARITY:
                    duplicate = DuplicateInstance(
                        duplicate_id=f"root_cause_dup_{w1}_{w2}",
                        duplicate_type=DuplicateType.ROOT_CAUSE,
                        severity="high" if max_similarity > 0.8 else "medium",
                        workers_involved=[w1, w2],
                        overlapping_items=most_similar,
                        wasted_effort_ratio=max_similarity,
                        suggestion="Share findings to avoid duplicate analysis"
                    )
                    duplicates.append(duplicate)
        
        return duplicates
    
    def calculate_penalty(self, duplicates: List[DuplicateInstance]) -> float:
        """
        Calculate duplicate effort penalty.
        
        Policy 3: Duplicate effort penalti oladi.
        """
        if not duplicates:
            return 0.0
        
        # Penalize based on severity
        penalty = 0.0
        
        for dup in duplicates:
            if dup.severity == "high":
                penalty += 0.3
            elif dup.severity == "medium":
                penalty += 0.15
            else:
                penalty += 0.05
        
        # Cap penalty
        return min(penalty, 1.0)
    
    def get_duplicate_report(self) -> Dict[str, Any]:
        """Get comprehensive duplicate report"""
        if not self.duplicates_found:
            return {
                "total_duplicates": 0,
                "penalty": 0.0,
                "message": "No duplicate work detected"
            }
        
        by_type = {}
        for dup in self.duplicates_found:
            dtype = dup.duplicate_type.value
            by_type[dtype] = by_type.get(dtype, 0) + 1
        
        return {
            "total_duplicates": len(self.duplicates_found),
            "by_type": by_type,
            "penalty": self.calculate_penalty(self.duplicates_found),
            "duplicates": [
                {
                    "id": d.duplicate_id,
                    "type": d.duplicate_type.value,
                    "severity": d.severity,
                    "workers": d.workers_involved,
                    "overlap": d.wasted_effort_ratio
                }
                for d in self.duplicates_found
            ]
        }


__all__ = [
    'DuplicateEffortDetector',
    'DuplicateType',
    'DuplicateInstance'
]
