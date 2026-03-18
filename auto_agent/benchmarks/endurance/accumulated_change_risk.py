"""
Accumulated Change Risk Analyzer - Self-Modification Risk Tracking
=============================================================

This module tracks and analyzes cumulative self-modification risks:
- Patch stack depth tracking
- Overlapping edits detection
- Repeated module modifications
- Rollback probability estimation
- Accumulated regression risk scoring

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
import statistics
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ChangeType(str, Enum):
    """Types of self-modifications"""
    PATCH = "patch"
    TOOL_ADDITION = "tool_addition"
    ROUTING_CHANGE = "routing_change"
    MEMORY_UPDATE = "memory_update"
    POLICY_CHANGE = "policy_change"
    CONFIG_CHANGE = "config_change"


class RiskLevel(str, Enum):
    """Risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== DATA CLASSES ====================

@dataclass
class ChangeRecord:
    """Record of a single change"""
    change_id: str
    change_type: ChangeType
    module: str
    description: str
    timestamp: datetime
    file_path: str
    lines_changed: int
    risk_score: float
    metadata: Dict


@dataclass
class ModuleModification:
    """Track modifications to a specific module"""
    module_name: str
    modification_count: int
    first_modified: datetime
    last_modified: datetime
    change_ids: List[str]
    total_lines_changed: int
    risk_history: List[float]


@dataclass
class OverlapAnalysis:
    """Analysis of overlapping changes"""
    overlapping_changes: List[str]
    modules_affected: List[str]
    time_window_hours: float
    risk_increase: float


@dataclass
class RiskReport:
    """Comprehensive risk report"""
    timestamp: datetime
    
    # Statistics
    total_changes: int
    changes_last_24h: int
    changes_last_hour: int
    
    # Module analysis
    most_modified_modules: List[Tuple[str, int]]
    modules_at_risk: List[str]
    
    # Patch stack
    patch_stack_depth: int
    overlapping_patches: int
    
    # Risk assessment
    current_risk_level: RiskLevel
    risk_score: float              # 0-100
    
    # Specific risks
    regression_risk: float
    rollback_difficulty: float
    conflict_probability: float
    
    # Recommendations
    recommendations: List[str]


# ==================== CHANGE TRACKER ====================

class ChangeTracker:
    """Tracks all self-modifications"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._changes: List[ChangeRecord] = []
        self._module_index: Dict[str, List[str]] = defaultdict(list)  # module -> change_ids
        self._change_types: Dict[ChangeType, List[str]] = defaultdict(list)
    
    def record_change(self, change_type: ChangeType, module: str, description: str,
                    file_path: str, lines_changed: int, metadata: Optional[Dict] = None):
        """Record a change"""
        change_id = f"{change_type.value}_{module}_{int(time.time())}"
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(change_type, lines_changed, metadata)
        
        change = ChangeRecord(
            change_id=change_id,
            change_type=change_type,
            module=module,
            description=description,
            timestamp=datetime.now(),
            file_path=file_path,
            lines_changed=lines_changed,
            risk_score=risk_score,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._changes.append(change)
            self._module_index[module].append(change_id)
            self._change_types[change_type].append(change_id)
        
        logger.info(f"Recorded change: {change_id} - {module}")
        return change_id
    
    def _calculate_risk_score(self, change_type: ChangeType, lines_changed: int,
                            metadata: Optional[Dict]) -> float:
        """Calculate risk score for a change"""
        score = 0.0
        
        # Base score by change type
        type_scores = {
            ChangeType.PATCH: 20,
            ChangeType.TOOL_ADDITION: 25,
            ChangeType.ROUTING_CHANGE: 15,
            ChangeType.MEMORY_UPDATE: 10,
            ChangeType.POLICY_CHANGE: 30,
            ChangeType.CONFIG_CHANGE: 5
        }
        score += type_scores.get(change_type, 10)
        
        # Additional risk for large changes
        if lines_changed > 100:
            score += 20
        elif lines_changed > 50:
            score += 10
        elif lines_changed > 20:
            score += 5
        
        # Risk multipliers from metadata
        if metadata:
            if metadata.get("breaking_change"):
                score += 25
            if metadata.get("affects_core"):
                score += 20
            if metadata.get("experimental"):
                score += 10
        
        return min(100, score)
    
    def get_changes(self, since: Optional[datetime] = None,
                   module: Optional[str] = None,
                   change_type: Optional[ChangeType] = None) -> List[ChangeRecord]:
        """Get changes with filters"""
        with self._lock:
            filtered = list(self._changes)
        
        if since:
            filtered = [c for c in filtered if c.timestamp >= since]
        
        if module:
            filtered = [c for c in filtered if c.module == module]
        
        if change_type:
            filtered = [c for c in filtered if c.change_type == change_type]
        
        return filtered
    
    def get_module_modifications(self) -> Dict[str, ModuleModification]:
        """Get modification stats per module"""
        with self._lock:
            modules = {}
            
            for module, change_ids in self._module_index.items():
                changes = [c for c in self._changes if c.change_id in change_ids]
                
                if changes:
                    modules[module] = ModuleModification(
                        module_name=module,
                        modification_count=len(changes),
                        first_modified=min(c.timestamp for c in changes),
                        last_modified=max(c.timestamp for c in changes),
                        change_ids=change_ids,
                        total_lines_changed=sum(c.lines_changed for c in changes),
                        risk_history=[c.risk_score for c in changes]
                    )
            
            return modules


# ==================== RISK ANALYZER ====================

class RiskAnalyzer:
    """Analyzes accumulated change risks"""
    
    def __init__(self, change_tracker: ChangeTracker):
        self._tracker = change_tracker
        
        # Thresholds
        self._critical_module_changes = 5
        self._warning_module_changes = 3
        self._critical_patch_depth = 10
        self._warning_patch_depth = 5
    
    def analyze(self) -> RiskReport:
        """Perform comprehensive risk analysis"""
        # Get recent changes
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_1h = now - timedelta(hours=1)
        
        changes_24h = self._tracker.get_changes(since=last_24h)
        changes_1h = self._tracker.get_changes(since=last_1h)
        
        # Get module modifications
        module_mods = self._tracker.get_module_modifications()
        
        # Find most modified modules
        most_modified = sorted(
            [(m, mod.modification_count) for m, mod in module_mods.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Find modules at risk
        at_risk = [
            m for m, mod in module_mods.items()
            if mod.modification_count >= self._warning_module_changes
        ]
        
        # Patch stack analysis
        patch_changes = self._tracker.get_changes(change_type=ChangeType.PATCH)
        patch_stack_depth = len(patch_changes)
        
        # Find overlapping patches
        overlapping = self._detect_overlapping_patches(patch_changes)
        
        # Calculate risk scores
        risk_score = self._calculate_overall_risk(module_mods, patch_stack_depth, len(changes_24h))
        regression_risk = self._calculate_regression_risk(module_mods, patch_stack_depth)
        rollback_difficulty = self._calculate_rollback_difficulty(patch_changes)
        conflict_probability = self._calculate_conflict_probability(module_mods)
        
        # Determine risk level
        current_risk = self._determine_risk_level(risk_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            module_mods, at_risk, patch_stack_depth, current_risk
        )
        
        return RiskReport(
            timestamp=now,
            total_changes=len(self._tracker.get_changes()),
            changes_last_24h=len(changes_24h),
            changes_last_hour=len(changes_1h),
            most_modified_modules=most_modified,
            modules_at_risk=at_risk,
            patch_stack_depth=patch_stack_depth,
            overlapping_patches=len(overlapping),
            current_risk_level=current_risk,
            risk_score=risk_score,
            regression_risk=regression_risk,
            rollback_difficulty=rollback_difficulty,
            conflict_probability=conflict_probability,
            recommendations=recommendations
        )
    
    def _detect_overlapping_patches(self, patches: List[ChangeRecord]) -> List[str]:
        """Detect overlapping patches in same modules"""
        module_patches = defaultdict(list)
        
        for patch in patches:
            module_patches[patch.module].append(patch.change_id)
        
        overlapping = []
        for module, patch_ids in module_patches.items():
            if len(patch_ids) > 1:
                # Check if recent (within 1 hour)
                recent = [
                    p for p in patches 
                    if p.module == module and p.timestamp > datetime.now() - timedelta(hours=1)
                ]
                if len(recent) > 1:
                    overlapping.extend([p.change_id for p in recent])
        
        return overlapping
    
    def _calculate_overall_risk(self, module_mods: Dict[str, ModuleModification],
                              patch_depth: int, recent_changes: int) -> float:
        """Calculate overall risk score"""
        score = 0.0
        
        # Module modification risk
        for mod in module_mods.values():
            if mod.modification_count >= self._critical_module_changes:
                score += 30
            elif mod.modification_count >= self._warning_module_changes:
                score += 15
        
        # Patch stack risk
        if patch_depth >= self._critical_patch_depth:
            score += 25
        elif patch_depth >= self._warning_patch_depth:
            score += 10
        
        # Recent change volume risk
        if recent_changes > 20:
            score += 20
        elif recent_changes > 10:
            score += 10
        
        return min(100, score)
    
    def _calculate_regression_risk(self, module_mods: Dict[str, ModuleModification],
                                  patch_depth: int) -> float:
        """Calculate regression risk"""
        risk = 0.0
        
        # High module modification count increases regression risk
        for mod in module_mods.values():
            risk += min(0.3, mod.modification_count * 0.05)
        
        # Deep patch stacks increase regression risk
        risk += min(0.4, patch_depth * 0.03)
        
        return min(1.0, risk)
    
    def _calculate_rollback_difficulty(self, patches: List[ChangeRecord]) -> float:
        """Calculate rollback difficulty (0-1, higher = harder)"""
        if not patches:
            return 0.0
        
        difficulty = 0.0
        
        # More patches = harder to rollback
        difficulty += min(0.5, len(patches) * 0.04)
        
        # Check for dependent changes
        # (simplified - would need dependency graph)
        
        return min(1.0, difficulty)
    
    def _calculate_conflict_probability(self, module_mods: Dict[str, ModuleModification]) -> float:
        """Calculate probability of conflicts"""
        if not module_mods:
            return 0.0
        
        # More concurrent modifications = higher conflict probability
        recent_mods = {
            m: mod for m, mod in module_mods.items()
            if mod.last_modified > datetime.now() - timedelta(hours=1)
        }
        
        prob = len(recent_mods) * 0.15
        return min(1.0, prob)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score"""
        if score >= 70:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(self, module_mods: Dict[str, ModuleModification],
                                 at_risk: List[str], patch_depth: int,
                                 risk_level: RiskLevel) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("CRITICAL: Pause further self-modifications")
            recommendations.append("Review and potentially rollback recent changes")
        
        if patch_depth >= self._critical_patch_depth:
            recommendations.append(f"Patch stack depth ({patch_depth}) is critical - consider consolidating patches")
        
        if len(at_risk) > 0:
            recommendations.append(f"Modules at risk: {', '.join(at_risk[:5])}")
        
        # Check for modules with many small changes
        for module, mod in module_mods.items():
            if mod.modification_count >= 5 and mod.total_lines_changed < 50:
                recommendations.append(f"Module {module} has many small changes - consider consolidating")
        
        if not recommendations:
            recommendations.append("Self-modification risk is within acceptable limits")
        
        return recommendations


# ==================== ACCUMULATED CHANGE RISK ANALYZER ====================

class AccumulatedChangeRiskAnalyzer:
    """
    Main analyzer for accumulated self-modification risks.
    
    Features:
    - Change tracking
    - Module-level analysis
    - Patch stack depth monitoring
    - Overlap detection
    - Regression risk scoring
    - Rollback difficulty estimation
    - Conflict probability
    - Historical analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Components
        self._tracker = ChangeTracker()
        self._analyzer = RiskAnalyzer(self._tracker)
        
        # State
        self._is_monitoring = False
        self._last_report: Optional[RiskReport] = None
        
        # Callbacks
        self._on_risk_increased: Optional[Callable] = None
        self._on_critical_risk: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_risk_increased: Optional[Callable] = None,
                     on_critical_risk: Optional[Callable] = None):
        """Set callback functions"""
        self._on_risk_increased = on_risk_increased
        self._on_critical_risk = on_critical_risk
    
    # ==================== CHANGE RECORDING ====================
    
    def record_patch(self, module: str, description: str, file_path: str,
                    lines_changed: int, metadata: Optional[Dict] = None) -> str:
        """Record a patch change"""
        return self._tracker.record_change(
            ChangeType.PATCH, module, description, file_path, lines_changed, metadata
        )
    
    def record_tool_addition(self, module: str, tool_name: str, file_path: str,
                           metadata: Optional[Dict] = None) -> str:
        """Record tool addition"""
        return self._tracker.record_change(
            ChangeType.TOOL_ADDITION, module, f"Added tool: {tool_name}",
            file_path, 0, metadata
        )
    
    def record_routing_change(self, module: str, description: str, file_path: str,
                            lines_changed: int, metadata: Optional[Dict] = None) -> str:
        """Record routing change"""
        return self._tracker.record_change(
            ChangeType.ROUTING_CHANGE, module, description, file_path, lines_changed, metadata
        )
    
    def record_change(self, change_type: ChangeType, module: str, description: str,
                    file_path: str, lines_changed: int = 0,
                    metadata: Optional[Dict] = None) -> str:
        """Generic change recording"""
        return self._tracker.record_change(
            change_type, module, description, file_path, lines_changed, metadata
        )
    
    # ==================== ANALYSIS ====================
    
    def analyze(self) -> RiskReport:
        """Perform comprehensive risk analysis"""
        report = self._analyzer.analyze()
        self._last_report = report
        
        # Check for critical risk
        if report.current_risk_level == RiskLevel.CRITICAL:
            if self._on_critical_risk:
                self._on_critical_risk(report)
        elif report.risk_score > 50:
            if self._on_risk_increased:
                self._on_risk_increased(report)
        
        return report
    
    def get_module_risk(self, module: str) -> Optional[Dict]:
        """Get risk metrics for a specific module"""
        modules = self._tracker.get_module_modifications()
        
        if module not in modules:
            return None
        
        mod = modules[module]
        
        return {
            "module": module,
            "modification_count": mod.modification_count,
            "first_modified": mod.first_modified.isoformat(),
            "last_modified": mod.last_modified.isoformat(),
            "total_lines_changed": mod.total_lines_changed,
            "avg_risk": statistics.mean(mod.risk_history) if mod.risk_history else 0,
            "max_risk": max(mod.risk_history) if mod.risk_history else 0,
            "at_risk": mod.modification_count >= self._analyzer._warning_module_changes
        }
    
    # ==================== ROLLBACK SUPPORT ====================
    
    def get_changes_for_rollback(self, module: str, count: int = 1) -> List[ChangeRecord]:
        """Get changes that could be rolled back for a module"""
        changes = self._tracker.get_changes(module=module)
        
        # Get most recent changes
        return sorted(changes, key=lambda c: c.timestamp, reverse=True)[:count]
    
    def estimate_rollback_impact(self, change_ids: List[str]) -> Dict:
        """Estimate impact of rolling back changes"""
        changes = [c for c in self._tracker.get_changes() if c.change_id in change_ids]
        
        if not changes:
            return {"error": "No changes found"}
        
        return {
            "changes_count": len(changes),
            "modules_affected": list(set(c.module for c in changes)),
            "total_lines_affected": sum(c.lines_changed for c in changes),
            "estimated_effort": len(changes) * 2,  # hours
            "risk_level": RiskLevel.HIGH if len(changes) > 5 else RiskLevel.MEDIUM
        }
    
    # ==================== MONITORING ====================
    
    def start_monitoring(self):
        """Start risk monitoring"""
        self._is_monitoring = True
        logger.info("Change risk monitoring started")
    
    def stop_monitoring(self):
        """Stop risk monitoring"""
        self._is_monitoring = False
        logger.info("Change risk monitoring stopped")
    
    @property
    def is_monitoring(self) -> bool:
        return self._is_monitoring
    
    @property
    def current_risk_report(self) -> Optional[RiskReport]:
        return self._last_report
    
    @property
    def risk_score(self) -> float:
        if self._last_report:
            return self._last_report.risk_score
        return 0.0


# ==================== FACTORY ====================

def create_change_risk_analyzer(config: Optional[Dict] = None) -> AccumulatedChangeRiskAnalyzer:
    """Factory function to create change risk analyzer"""
    return AccumulatedChangeRiskAnalyzer(config=config)
