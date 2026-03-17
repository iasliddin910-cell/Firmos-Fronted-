"""
DatasetHealthReport - Benchmark Health Metrics
==========================================

Benchmark sog'liq metrikalari.

Bu modul:
- Task soni
- Suite balans
- Difficulty balans
- Flake rate
- Duplicate risk
- Deprecated task ulushi
- Owner coverage
- Freshness score

hisoblaydi.

Definition of Done:
5. Dataset health report mavjud.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os


@dataclass
class HealthMetrics:
    """Sog'liq metrikalari."""
    # Task counts
    total_tasks: int = 0
    stable_tasks: int = 0
    candidate_tasks: int = 0
    deprecated_tasks: int = 0
    quarantined_tasks: int = 0
    
    # Coverage
    suite_coverage: Dict[str, int] = field(default_factory=dict)
    difficulty_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Quality
    flake_rate: float = 0.0
    duplicate_ratio: float = 0.0
    contamination_risk_ratio: float = 0.0
    
    # Ownership
    owner_coverage: float = 0.0
    ownerless_count: int = 0
    
    # Freshness
    avg_task_age_days: float = 0.0
    stale_tasks_count: int = 0
    
    # Validation
    validated_tasks: int = 0
    schema_valid_tasks: int = 0


@dataclass
class HealthReport:
    """Sog'liq hisoboti."""
    report_id: str
    generated_at: str
    
    metrics: HealthMetrics
    
    # Issues
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Score
    health_score: float = 0.0  # 0-1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "metrics": {
                "total_tasks": self.metrics.total_tasks,
                "stable_tasks": self.metrics.stable_tasks,
                "candidate_tasks": self.metrics.candidate_tasks,
                "deprecated_tasks": self.metrics.deprecated_tasks,
                "quarantined_tasks": self.metrics.quarantined_tasks,
                "suite_coverage": self.metrics.suite_coverage,
                "difficulty_distribution": self.metrics.difficulty_distribution,
                "flake_rate": self.metrics.flake_rate,
                "duplicate_ratio": self.metrics.duplicate_ratio,
                "contamination_risk_ratio": self.metrics.contamination_risk_ratio,
                "owner_coverage": self.metrics.owner_coverage,
                "ownerless_count": self.metrics.ownerless_count,
                "avg_task_age_days": self.metrics.avg_task_age_days,
                "stale_tasks_count": self.metrics.stale_tasks_count,
                "validated_tasks": self.metrics.validated_tasks,
                "schema_valid_tasks": self.metrics.schema_valid_tasks,
            },
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "health_score": self.health_score,
        }


class DatasetHealthReport:
    """
    Dataset sog'liq hisoboti.
    
    Definition of Done:
    5. Dataset health report mavjud.
    """
    
    def __init__(self, registry=None, dedup_analyzer=None, contamination_guard=None):
        self.registry = registry
        self.dedup_analyzer = dedup_analyzer
        self.contamination_guard = contamination_guard
        
        # Configuration
        self.stale_threshold_days = 90
        self.min_owner_coverage = 0.8
        self.max_flake_rate = 0.1
        self.max_duplicate_ratio = 0.05
    
    def generate_report(self) -> HealthReport:
        """Hisobot generatsiya."""
        report_id = f"health_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        metrics = HealthMetrics()
        
        if not self.registry:
            return HealthReport(
                report_id=report_id,
                generated_at=datetime.utcnow().isoformat(),
                metrics=metrics,
                critical_issues=["Registry not configured"],
                health_score=0.0,
            )
        
        # Get all tasks
        all_tasks = self.registry.get_all_tasks()
        metrics.total_tasks = len(all_tasks)
        
        # Get tasks by state
        metrics.stable_tasks = len(self.registry.get_stable())
        metrics.candidate_tasks = len(self.registry.get_candidates())
        metrics.deprecated_tasks = len(self.registry.get_deprecated())
        metrics.quarantined_tasks = len(self.registry.get_quarantined())
        
        # Suite coverage
        metrics.suite_coverage = self.registry.get_suite_summary()
        
        # Difficulty distribution
        metrics.difficulty_distribution = self.registry.get_difficulty_summary()
        
        # Flake rate
        flaky_tasks = self.registry.get_flaky()
        metrics.flake_rate = len(flaky_tasks) / metrics.total_tasks if metrics.total_tasks > 0 else 0
        
        # Owner coverage
        ownerless = self.registry.get_ownerless()
        metrics.ownerless_count = len(ownerless)
        metrics.owner_coverage = 1.0 - (metrics.ownerless_count / metrics.total_tasks) if metrics.total_tasks > 0 else 0
        
        # Validated tasks
        metrics.validated_tasks = len([
            t for t in all_tasks
            if t.state in ["validated", "stable"]
        ])
        metrics.schema_valid_tasks = len([
            t for t in all_tasks if t.schema_valid
        ])
        
        # Freshness
        now = datetime.utcnow()
        total_age = 0
        stale_count = 0
        
        for task in all_tasks:
            created = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
            age_days = (now - created.replace(tzinfo=None)).days
            total_age += age_days
            
            if age_days > self.stale_threshold_days:
                stale_count += 1
        
        metrics.avg_task_age_days = total_age / metrics.total_tasks if metrics.total_tasks > 0 else 0
        metrics.stale_tasks_count = stale_count
        
        # Dedup analysis
        if self.dedup_analyzer:
            dedup_report = self.dedup_analyzer.get_dedup_report()
            metrics.duplicate_ratio = dedup_report.get("duplicate_ratio", 0)
        
        # Contamination
        if self.contamination_guard:
            contam_summary = self.contamination_guard.get_contamination_summary()
            metrics.contamination_risk_ratio = contam_summary.get("contamination_rate", 0)
        
        # Generate issues and recommendations
        critical_issues = []
        warnings = []
        recommendations = []
        
        # Check issues
        if metrics.flake_rate > self.max_flake_rate:
            critical_issues.append(
                f"High flake rate: {metrics.flake_rate:.1%} (max: {self.max_flake_rate:.1%})"
            )
            recommendations.append("Review and quarantine flaky tasks")
        
        if metrics.duplicate_ratio > self.max_duplicate_ratio:
            critical_issues.append(
                f"High duplicate ratio: {metrics.duplicate_ratio:.1%} (max: {self.max_duplicate_ratio:.1%})"
            )
            recommendations.append("Run dedup analysis and merge duplicates")
        
        if metrics.owner_coverage < self.min_owner_coverage:
            critical_issues.append(
                f"Low owner coverage: {metrics.owner_coverage:.1%} (min: {self.min_owner_coverage:.1%})"
            )
            recommendations.append("Assign owners to all tasks")
        
        if metrics.contamination_risk_ratio > 0.1:
            critical_issues.append(
                f"High contamination risk: {metrics.contamination_risk_ratio:.1%}"
            )
            recommendations.append("Review contamination risks")
        
        # Warnings
        if metrics.stale_tasks_count > metrics.total_tasks * 0.2:
            warnings.append(
                f"Many stale tasks: {metrics.stale_tasks_count} ({metrics.stale_tasks_count/metrics.total_tasks:.1%})"
            )
            recommendations.append("Review stale tasks for deprecation")
        
        if metrics.deprecated_tasks > metrics.total_tasks * 0.3:
            warnings.append(
                f"High deprecated ratio: {metrics.deprecated_tasks} ({metrics.deprecated_tasks/metrics.total_tasks:.1%})"
            )
        
        # Calculate health score
        health_score = self._calculate_health_score(metrics, critical_issues)
        
        return HealthReport(
            report_id=report_id,
            generated_at=datetime.utcnow().isoformat(),
            metrics=metrics,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations,
            health_score=health_score,
        )
    
    def _calculate_health_score(
        self,
        metrics: HealthMetrics,
        critical_issues: List[str],
    ) -> float:
        """Sog'liq ballini hisoblash."""
        score = 1.0
        
        # Critical issues reduce score heavily
        score -= len(critical_issues) * 0.2
        
        # Flake rate
        if metrics.flake_rate > 0:
            score -= metrics.flake_rate * 0.3
        
        # Duplicate ratio
        if metrics.duplicate_ratio > 0:
            score -= metrics.duplicate_ratio * 0.2
        
        # Owner coverage (reward high coverage)
        score += metrics.owner_coverage * 0.1
        
        # Validated ratio
        if metrics.total_tasks > 0:
            validated_ratio = metrics.validated_tasks / metrics.total_tasks
            score += validated_ratio * 0.1
        
        # Contamination
        if metrics.contamination_risk_ratio > 0:
            score -= metrics.contamination_risk_ratio * 0.3
        
        return max(0.0, min(1.0, score))
    
    def save_report(self, report: HealthReport, path: str) -> None:
        """Hisobotni saqlash."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
    
    def load_report(self, path: str) -> Optional[HealthReport]:
        """Hisobotni yuklash."""
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        metrics = HealthMetrics(**data["metrics"])
        
        return HealthReport(
            report_id=data["report_id"],
            generated_at=data["generated_at"],
            metrics=metrics,
            critical_issues=data.get("critical_issues", []),
            warnings=data.get("warnings", []),
            recommendations=data.get("recommendations", []),
            health_score=data.get("health_score", 0.0),
        )


# ==================== FACTORY ====================

def create_health_report(
    registry=None,
    dedup_analyzer=None,
    contamination_guard=None,
) -> DatasetHealthReport:
    """DatasetHealthReport yaratish."""
    return DatasetHealthReport(registry, dedup_analyzer, contamination_guard)
