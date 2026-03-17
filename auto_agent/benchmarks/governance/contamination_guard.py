"""
ContaminationGuard - Contamination Detection
=======================================

Task contamination tekshirish va himoya qilish.

Bu modul:
- Train/validation/release/canary splitlarni tekshirish
- Self-improvement history bilan overlap
- Task exposure level tracking
- Canary tasklarni himoya qilish

Definition of Done:
4. Dedup va contamination scan ishlaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime
import os
import json


# ==================== EXPOSURE TYPES ====================

class ExposureLevel(str, Enum):
    """Task exposure level."""
    NEVER_EXPOSED = "never_exposed"      # Hech qachon ko'rsatilmagan
    INTERNAL_ONLY = "internal_only"       # Faqat internal
    CANARY = "canary"                    # Canary release
    VALIDATION = "validation"             # Validation set
    RELEASE = "release"                   # Public release
    TRAIN_LIKE = "train_like"            # Trainingga o'xshash


class ContaminationType(str, Enum):
    """Contamination turlari."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== CONTAMINATION RESULT ====================

@dataclass
class ContaminationResult:
    """Contamination tekshirish natijasi."""
    task_id: str
    contamination_type: str
    risk_level: str
    
    # Details
    exposure_history: List[str] = field(default_factory=list)
    overlap_with_training: List[str] = field(default_factory=list)
    similarity_score: float = 0.0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def is_clean(self) -> bool:
        """Task toza (contamination yo'q)mi?"""
        return self.risk_level in [ContaminationType.NONE.value, ContaminationType.LOW.value]


# ==================== EXPOSURE TRACKER ====================

class ExposureTracker:
    """Task exposure level tracking."""
    
    def __init__(self):
        # task_id -> exposure history
        self.exposure_history: Dict[str, List[str]] = {}
        
        # Current exposure level
        self.current_exposure: Dict[str, str] = {}
    
    def record_exposure(
        self,
        task_id: str,
        exposure_type: str,
        timestamp: str = None,
    ) -> None:
        """Exposure record qilish."""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        if task_id not in self.exposure_history:
            self.exposure_history[task_id] = []
        
        self.exposure_history[task_id].append(f"{exposure_type}:{timestamp}")
        self.current_exposure[task_id] = exposure_type
    
    def get_exposure_history(self, task_id: str) -> List[str]:
        """Task exposure history olish."""
        return self.exposure_history.get(task_id, [])
    
    def get_current_exposure(self, task_id: str) -> str:
        """Task current exposure level."""
        return self.current_exposure.get(task_id, ExposureLevel.NEVER_EXPOSED.value)
    
    def is_exposed_to_release(self, task_id: str) -> bool:
        """Task releasega exposemi?"""
        exposure = self.get_current_exposure(task_id)
        return exposure in [
            ExposureLevel.RELEASE.value,
            ExposureLevel.TRAIN_LIKE.value,
        ]


# ==================== CONTAMINATION GUARD ====================

class ContaminationGuard:
    """
    Contamination tekshirish va himoya.
    
    Definition of Done:
    4. Dedup va contamination scan ishlaydi.
    """
    
    def __init__(self):
        # Task packs
        self.train_tasks: Set[str] = set()
        self.validation_tasks: Set[str] = set()
        self.release_tasks: Set[str] = set()
        self.canary_tasks: Set[str] = set()
        self.never_exposed_tasks: Set[str] = set()
        
        # Exposure tracker
        self.exposure_tracker = ExposureTracker()
        
        # Self-improvement history
        self.self_improvement_history: List[Dict[str, Any]] = []
        
        # Task metadata
        self.task_metadata: Dict[str, Dict[str, Any]] = {}
    
    def load_task_packs(
        self,
        train_tasks: List[str] = None,
        validation_tasks: List[str] = None,
        release_tasks: List[str] = None,
        canary_tasks: List[str] = None,
    ) -> None:
        """Task packlarni yuklash."""
        if train_tasks:
            self.train_tasks = set(train_tasks)
        if validation_tasks:
            self.validation_tasks = set(validation_tasks)
        if release_tasks:
            self.release_tasks = set(release_tasks)
        if canary_tasks:
            self.canary_tasks = set(canary_tasks)
        
        # Mark never exposed
        all_known = (
            self.train_tasks | 
            self.validation_tasks | 
            self.release_tasks | 
            self.canary_tasks
        )
        # This is simplified - in reality would track which tasks exist
    
    def register_task(
        self,
        task_id: str,
        exposure_level: str,
    ) -> None:
        """Taskni ro'yxatga olish."""
        # Record exposure
        self.exposure_tracker.record_exposure(task_id, exposure_level)
        
        # Add to appropriate pack
        if exposure_level == ExposureLevel.TRAIN_LIKE.value:
            self.train_tasks.add(task_id)
        elif exposure_level == ExposureLevel.VALIDATION.value:
            self.validation_tasks.add(task_id)
        elif exposure_level == ExposureLevel.RELEASE.value:
            self.release_tasks.add(task_id)
        elif exposure_level == ExposureLevel.CANARY.value:
            self.canary_tasks.add(task_id)
        elif exposure_level == ExposureLevel.NEVER_EXPOSED.value:
            self.never_exposed_tasks.add(task_id)
    
    def record_self_improvement(
        self,
        improvement_id: str,
        affected_tasks: List[str],
        improvement_type: str,
    ) -> None:
        """Self-improvement historyni record qilish."""
        self.self_improvement_history.append({
            "improvement_id": improvement_id,
            "affected_tasks": affected_tasks,
            "improvement_type": improvement_type,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def check_task_contamination(
        self,
        task_id: str,
    ) -> ContaminationResult:
        """Task contamination tekshirish."""
        result = ContaminationResult(
            task_id=task_id,
            contamination_type=ContaminationType.NONE.value,
            risk_level=ContaminationType.NONE.value,
        )
        
        # Get exposure history
        result.exposure_history = self.exposure_tracker.get_exposure_history(task_id)
        
        # Check if task is in self-improvement history
        for improvement in self.self_improvement_history:
            if task_id in improvement.get("affected_tasks", []):
                result.overlap_with_training.append(improvement["improvement_id"])
        
        # Calculate contamination risk
        risk_score = 0.0
        
        # High risk: train-like tasks that have been improved
        if task_id in self.train_tasks:
            risk_score += 0.4
            result.recommendations.append("Task is in training-like set")
        
        # Check overlap with improvements
        if result.overlap_with_training:
            risk_score += 0.3
            result.recommendations.append(
                f"Task affected by {len(result.overlap_with_training)} improvements"
            )
        
        # Check exposure to release
        if self.exposure_tracker.is_exposed_to_release(task_id):
            risk_score += 0.2
            result.recommendations.append("Task exposed in release")
        
        # Determine contamination type
        if risk_score >= 0.7:
            result.contamination_type = ContaminationType.CRITICAL.value
            result.risk_level = ContaminationType.CRITICAL.value
        elif risk_score >= 0.5:
            result.contamination_type = ContaminationType.HIGH.value
            result.risk_level = ContaminationType.HIGH.value
        elif risk_score >= 0.3:
            result.contamination_type = ContaminationType.MEDIUM.value
            result.risk_level = ContaminationType.MEDIUM.value
        elif risk_score >= 0.1:
            result.contamination_type = ContaminationType.LOW.value
            result.risk_level = ContaminationType.LOW.value
        else:
            result.contamination_type = ContaminationType.NONE.value
            result.risk_level = ContaminationType.NONE.value
        
        result.similarity_score = risk_score
        
        return result
    
    def check_batch_contamination(
        self,
        task_ids: List[str],
    ) -> List[ContaminationResult]:
        """Bir nechta task contamination tekshirish."""
        return [self.check_task_contamination(tid) for tid in task_ids]
    
    def get_canary_protection_report(self) -> Dict[str, Any]:
        """Canary protection hisoboti."""
        total_canary = len(self.canary_tasks)
        exposed_canary = 0
        
        for task_id in self.canary_tasks:
            if self.exposure_tracker.is_exposed_to_release(task_id):
                exposed_canary += 1
        
        return {
            "total_canary_tasks": total_canary,
            "exposed_canary_tasks": exposed_canary,
            "protection_status": "COMPROMISED" if exposed_canary > 0 else "PROTECTED",
            "exposure_rate": exposed_canary / total_canary if total_canary > 0 else 0,
        }
    
    def get_contamination_summary(self) -> Dict[str, Any]:
        """Umumiy contamination summary."""
        all_tasks = (
            self.train_tasks |
            self.validation_tasks |
            self.release_tasks |
            self.canary_tasks |
            self.never_exposed_tasks
        )
        
        results = self.check_batch_contamination(list(all_tasks))
        
        risk_counts = {
            ContaminationType.CRITICAL.value: 0,
            ContaminationType.HIGH.value: 0,
            ContaminationType.MEDIUM.value: 0,
            ContaminationType.LOW.value: 0,
            ContaminationType.NONE.value: 0,
        }
        
        for result in results:
            risk_counts[result.risk_level] = risk_counts.get(result.risk_level, 0) + 1
        
        return {
            "total_tasks": len(all_tasks),
            "risk_distribution": risk_counts,
            "high_risk_count": risk_counts[ContaminationType.HIGH.value] + risk_counts[ContaminationType.CRITICAL.value],
            "clean_count": risk_counts[ContaminationType.NONE.value],
            "contamination_rate": (
                (risk_counts[ContaminationType.HIGH.value] + risk_counts[ContaminationType.CRITICAL.value])
                / len(all_tasks) if all_tasks else 0
            ),
        }
    
    def validate_release_is_clean(
        self,
        release_tasks: List[str],
    ) -> bool:
        """Release pack to'zami tekshirish."""
        results = self.check_batch_contamination(release_tasks)
        
        # Any critical or high contamination?
        for result in results:
            if result.risk_level in [ContaminationType.CRITICAL.value, ContaminationType.HIGH.value]:
                return False
        
        return True
    
    def suggest_safe_release_candidates(
        self,
        candidate_tasks: List[str],
        max_count: int = 100,
    ) -> List[str]:
        """Xavfsiz release candidate'lar."""
        results = self.check_batch_contamination(candidate_tasks)
        
        # Sort by risk (low to high)
        safe_tasks = [r.task_id for r in results if r.is_clean()]
        
        return safe_tasks[:max_count]


# ==================== FACTORY ====================

def create_contamination_guard() -> ContaminationGuard:
    """ContaminationGuard yaratish."""
    return ContaminationGuard()
