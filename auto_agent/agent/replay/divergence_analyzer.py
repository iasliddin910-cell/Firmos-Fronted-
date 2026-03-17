"""
Divergence Analyzer - Farqlarni aniqlash va tahlil qilish
=====================================================

Bu analyzer replay natijalarini tahlil qilib:
- Qaysi eventda farq boshlandi
- Bu farq legalmi yoki regressionmi
- Final outcome yaxshilandimi yoki yomonlashdimi
- Budget drift qanchalik katta

Bu self-improvement gate uchun juda foydali.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


class DivergenceType(str, Enum):
    """Divergence turlari"""
    NONE = "none"
    MINOR = "minor"           # Kichik farq, ahamiyatsiz
    SIGNIFICANT = "significant"  # Muhim farq
    CRITICAL = "critical"      # Kritik farq
    REGRESSION = "regression"  # Regression - yomonlashish
    IMPROVEMENT = "improvement" # Yaxshilanish


class DivergenceSeverity(str, Enum):
    """Divergence og'irligi"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DivergencePoint:
    """Divergence nuqtasi"""
    event_index: int
    event_type: str
    description: str
    expected_value: Any
    actual_value: Any
    severity: DivergenceSeverity
    is_regression: bool = False
    
    def to_dict(self) -> dict:
        return {
            'event_index': self.event_index,
            'event_type': self.event_type,
            'description': self.description,
            'expected_value': str(self.expected_value)[:100],
            'actual_value': str(self.actual_value)[:100],
            'severity': self.severity.value,
            'is_regression': self.is_regression
        }


@dataclass
class DivergenceReport:
    """
    Divergence Report - To'liq divergence tahlili
    
    Bu report quyidagilarni o'z ichiga oladi:
    - Divergence bormi?
    - Qayerda boshlandi
    - Og'irligi
    - Sababi
    - Ta'siri
    - Tavsiyalar
    """
    # Identity
    run_id: str
    baseline_run_id: Optional[str] = None
    
    # Overall status
    identical: bool = True
    divergence_type: DivergenceType = DivergenceType.NONE
    severity: DivergenceSeverity = DivergenceSeverity.NONE
    
    # Details
    divergence_points: List[DivergencePoint] = field(default_factory=list)
    first_divergence_index: Optional[int] = None
    
    # Outcome comparison
    baseline_outcome: Optional[Dict[str, Any]] = None
    current_outcome: Optional[Dict[str, Any]] = None
    outcome_improved: bool = False
    outcome_changed: bool = False
    
    # Performance
    baseline_performance: Optional[float] = None
    current_performance: Optional[float] = None
    performance_delta: float = 0.0
    
    # Metrics
    total_events: int = 0
    diverged_events: int = 0
    divergence_ratio: float = 0.0
    
    # Analysis
    root_cause: Optional[str] = None
    affected_components: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    
    def to_dict(self) -> dict:
        return {
            'run_id': self.run_id,
            'baseline_run_id': self.baseline_run_id,
            'identical': self.identical,
            'divergence_type': self.divergence_type.value,
            'severity': self.severity.value,
            'divergence_points': [p.to_dict() for p in self.divergence_points],
            'first_divergence_index': self.first_divergence_index,
            'outcome_improved': self.outcome_improved,
            'outcome_changed': self.outcome_changed,
            'performance_delta': self.performance_delta,
            'total_events': self.total_events,
            'diverged_events': self.diverged_events,
            'divergence_ratio': self.divergence_ratio,
            'root_cause': self.root_cause,
            'affected_components': self.affected_components,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp
        }


class DivergenceAnalyzer:
    """
    Divergence Analyzer - Replay va benchmark natijalarini tahlil qilish
    
    Bu analyzer quyidagi imkoniyatlarni beradi:
    - Ikkita runni taqqoslash
    - Divergence nuqtalarini aniqlash
    - Root cause tahlili
    - Tavsiyalar berish
    - Self-improvement uchun qaror qabul qilish
    
    Usage:
        analyzer = DivergenceAnalyzer()
        
        # Replaydan keyin
        report = analyzer.analyze(ledger, replay_state)
        
        # Ikkita runni taqqoslash
        comparison = analyzer.compare_runs(baseline_run, current_run)
        
        # Root cause tahloli
        root_cause = analyzer.find_root_cause(report)
    """
    
    def __init__(self):
        # Analysis history
        self.analysis_history: List[DivergenceReport] = []
        
        # Thresholds
        self.divergence_thresholds = {
            'minor': 0.05,      # 5% dan kam = minor
            'significant': 0.2, # 20% dan kam = significant
            'critical': 0.5      # 50% dan kam = critical
        }
        
        # Component mappings
        self.event_to_component = {
            'task_created': 'task_manager',
            'task_completed': 'task_manager',
            'tool_call': 'execution_engine',
            'verification_passed': 'verification_engine',
            'recovery_decided': 'recovery_engine',
            'checkpoint_restored': 'checkpoint_system'
        }
        
        logger.info("DivergenceAnalyzer initialized")
    
    def analyze(
        self,
        ledger: Any,
        replay_state: Any,
        baseline_state: Optional[Any] = None
    ) -> DivergenceReport:
        """
        Replay natijasini tahlil qilish
        
        Args:
            ledger: RunLedger
            replay_state: ReplayState
            baseline_state: (optional) Baseline ReplayState
            
        Returns:
            DivergenceReport
        """
        report = DivergenceReport(
            run_id=getattr(ledger, 'run_id', 'unknown'),
            total_events=getattr(replay_state, 'total_events', 0)
        )
        
        # Get divergence points from replay state
        diverged_indices = getattr(replay_state, 'diverged_events', [])
        report.diverged_events = len(diverged_indices)
        
        if report.total_events > 0:
            report.divergence_ratio = report.diverged_events / report.total_events
        
        # Determine divergence type and severity
        if report.diverged_events == 0:
            report.identical = True
            report.divergence_type = DivergenceType.NONE
            report.severity = DivergenceSeverity.NONE
            report.recommendations.append("No action needed - runs are identical")
        else:
            report.identical = False
            self._classify_divergence(report)
            self._analyze_divergence_points(report, diverged_indices, ledger)
        
        # Compare outcomes if baseline provided
        if baseline_state:
            report.baseline_run_id = getattr(baseline_state, 'run_id', 'unknown')
            self._compare_outcomes(report, baseline_state, replay_state)
        
        # Find root cause
        if not report.identical:
            report.root_cause = self._find_root_cause(report)
            report.affected_components = self._get_affected_components(report)
            report.recommendations = self._generate_recommendations(report)
        
        # Store in history
        self.analysis_history.append(report)
        
        logger.info(f"Divergence analysis complete: {report.divergence_type.value}, severity={report.severity.value}")
        
        return report
    
    def compare_runs(
        self,
        baseline_state: Dict[str, Any],
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ikkita runni taqqoslash
        
        Args:
            baseline_state: Baseline run holati
            current_state: Current run holati
            
        Returns:
            Comparison dict
        """
        diverged = False
        divergence_points = []
        
        # Compare status
        baseline_status = baseline_state.get('status')
        current_status = current_state.get('status')
        
        if baseline_status != current_status:
            diverged = True
            divergence_points.append({
                'type': 'status',
                'baseline': baseline_status,
                'current': current_status
            })
        
        # Compare events processed
        baseline_events = baseline_state.get('current_event_index', 0)
        current_events = current_state.get('current_event_index', 0)
        
        if abs(baseline_events - current_events) > 1:
            diverged = True
            divergence_points.append({
                'type': 'events',
                'baseline': baseline_events,
                'current': current_events
            })
        
        # Compare divergence counts
        baseline_div = baseline_state.get('divergence_count', 0)
        current_div = current_state.get('divergence_count', 0)
        
        if current_div > baseline_div:
            diverged = True
            divergence_points.append({
                'type': 'divergence',
                'baseline': baseline_div,
                'current': current_div,
                'is_regression': True
            })
        
        # Calculate divergence count
        divergence_count = len(divergence_points)
        
        return {
            'diverged': diverged,
            'divergence_count': divergence_count,
            'divergence_points': divergence_points,
            'baseline_status': baseline_status,
            'current_status': current_status
        }
    
    def _classify_divergence(self, report: DivergenceReport) -> None:
        """Divergence type va severity ni aniqlash"""
        ratio = report.divergence_ratio
        
        # Determine type
        if ratio <= self.divergence_thresholds['minor']:
            report.divergence_type = DivergenceType.MINOR
            report.severity = DivergenceSeverity.LOW
        elif ratio <= self.divergence_thresholds['significant']:
            report.divergence_type = DivergenceType.SIGNIFICANT
            report.severity = DivergenceSeverity.MEDIUM
        elif ratio <= self.divergence_thresholds['critical']:
            report.divergence_type = DivergenceType.CRITICAL
            report.severity = DivergenceSeverity.HIGH
        else:
            report.divergence_type = DivergenceType.REGRESSION
            report.severity = DivergenceSeverity.CRITICAL
    
    def _analyze_divergence_points(
        self,
        report: DivergenceReport,
        diverged_indices: List[int],
        ledger: Any
    ) -> None:
        """Divergence nuqtalarini tahlil qilish"""
        if not diverged_indices:
            return
        
        report.first_divergence_index = diverged_indices[0]
        
        # Get events for each divergence point
        events = getattr(ledger, 'events', [])
        
        for idx in diverged_indices:
            if idx < len(events):
                event = events[idx]
                event_type = getattr(event, 'event_type', 'unknown')
                
                # Determine severity
                if idx == report.first_divergence_index:
                    severity = DivergenceSeverity.HIGH
                else:
                    severity = DivergenceSeverity.MEDIUM
                
                divergence_point = DivergencePoint(
                    event_index=idx,
                    event_type=event_type,
                    description=f"Divergence at event {idx}",
                    expected_value="baseline value",
                    actual_value="current value",
                    severity=severity
                )
                
                report.divergence_points.append(divergence_point)
    
    def _compare_outcomes(
        self,
        report: DivergenceReport,
        baseline: Any,
        current: Any
    ) -> None:
        """Outcome larni taqqoslash"""
        # Extract outcome metrics
        baseline_success = baseline.get('status') == 'completed'
        current_success = current.get('status') == 'completed'
        
        report.outcome_changed = baseline_success != current_success
        report.outcome_improved = current_success and not baseline_success
        
        # Performance delta
        baseline_perf = baseline.get('execution_time', 0)
        current_perf = current.get('execution_time', 0)
        
        if baseline_perf > 0:
            report.performance_delta = (current_perf - baseline_perf) / baseline_perf
        
        report.baseline_outcome = {'success': baseline_success, 'time': baseline_perf}
        report.current_outcome = {'success': current_success, 'time': current_perf}
        
        # Update divergence type based on outcome
        if report.outcome_improved:
            if report.divergence_type in [DivergenceType.MINOR, DivergenceType.SIGNIFICANT]:
                report.divergence_type = DivergenceType.IMPROVEMENT
                report.severity = DivergenceSeverity.LOW
        elif report.outcome_changed and not report.outcome_improved:
            report.divergence_type = DivergenceType.REGRESSION
            report.severity = DivergenceSeverity.CRITICAL
    
    def _find_root_cause(self, report: DivergenceReport) -> str:
        """Root cause ni topish"""
        if not report.divergence_points:
            return "Unknown"
        
        # Analyze divergence patterns
        event_types = [p.event_type for p in report.divergence_points]
        
        # Most common event type
        if event_types:
            from collections import Counter
            most_common = Counter(event_types).most_common(1)[0]
            
            # Map to component
            component = self.event_to_component.get(most_common[0], 'unknown')
            
            return f"Likely caused by {component} at event {report.first_divergence_index}"
        
        return "Unable to determine root cause"
    
    def _get_affected_components(self, report: DivergenceReport) -> List[str]:
        """Ta'sirlangan componentlarni aniqlash"""
        components = set()
        
        for point in report.divergence_points:
            component = self.event_to_component.get(point.event_type, 'unknown')
            if component != 'unknown':
                components.add(component)
        
        return list(components)
    
    def _generate_recommendations(self, report: DivergenceReport) -> List[str]:
        """Tavsiyalar generatsiya qilish"""
        recommendations = []
        
        # Based on severity
        if report.severity == DivergenceSeverity.CRITICAL:
            recommendations.append("CRITICAL: Do not deploy - significant issues detected")
            recommendations.append("Review kernel changes and fix before deployment")
        elif report.severity == DivergenceSeverity.HIGH:
            recommendations.append("HIGH: Requires review before deployment")
            recommendations.append("Investigate divergence points")
        elif report.severity == DivergenceSeverity.MEDIUM:
            recommendations.append("MEDIUM: Monitor closely after deployment")
        elif report.severity == DivergenceSeverity.LOW:
            recommendations.append("LOW: Acceptable - minor variations expected")
        
        # Based on outcome
        if report.outcome_improved:
            recommendations.append("POSITIVE: Outcome improved despite some divergence")
        elif report.outcome_changed and not report.outcome_improved:
            recommendations.append("NEGATIVE: Outcome changed - investigate immediately")
        
        # Based on root cause
        if report.root_cause:
            recommendations.append(f"Root cause: {report.root_cause}")
        
        # Based on components
        if report.affected_components:
            components = ", ".join(report.affected_components)
            recommendations.append(f"Affected components: {components}")
        
        return recommendations
    
    def analyze_batch(
        self,
        reports: List[DivergenceReport]
    ) -> Dict[str, Any]:
        """
        Bir nechta reportlarni tahlil qilish
        
        Args:
            reports: DivergenceReportlar ro'yxati
            
        Returns:
            Batch analysis summary
        """
        if not reports:
            return {'total': 0}
        
        total = len(reports)
        identical = sum(1 for r in reports if r.identical)
        regressions = sum(1 for r in reports if r.divergence_type == DivergenceType.REGRESSION)
        improvements = sum(1 for r in reports if r.divergence_type == DivergenceType.IMPROVEMENT)
        
        return {
            'total': total,
            'identical': identical,
            'identical_percent': (identical / total) * 100,
            'regressions': regressions,
            'regressions_percent': (regressions / total) * 100,
            'improvements': improvements,
            'improvements_percent': (improvements / total) * 100,
            'average_severity': self._average_severity(reports)
        }
    
    def _average_severity(self, reports: List[DivergenceReport]) -> str:
        """O'rtacha severity olish"""
        severity_values = {
            DivergenceSeverity.NONE: 0,
            DivergenceSeverity.LOW: 1,
            DivergenceSeverity.MEDIUM: 2,
            DivergenceSeverity.HIGH: 3,
            DivergenceSeverity.CRITICAL: 4
        }
        
        if not reports:
            return "none"
        
        avg = sum(severity_values.get(r.severity, 0) for r in reports) / len(reports)
        
        if avg < 0.5:
            return "none"
        elif avg < 1.5:
            return "low"
        elif avg < 2.5:
            return "medium"
        elif avg < 3.5:
            return "high"
        else:
            return "critical"
    
    def get_safe_to_deploy(
        self,
        report: DivergenceReport,
        tolerance: float = 0.1
    ) -> Tuple[bool, str]:
        """
        Deployment uchun xavfsizligini aniqlash
        
        Args:
            report: DivergenceReport
            tolerance: Qabul qilish mumkin bo'lgan divergence foizi
            
        Returns:
            (is_safe, reason)
        """
        # Check severity
        if report.severity == DivergenceSeverity.CRITICAL:
            return False, "Critical divergence detected - not safe to deploy"
        
        if report.severity == DivergenceSeverity.HIGH:
            # Check if it's an improvement
            if report.divergence_type == DivergenceType.IMPROVEMENT:
                return True, "High severity but outcome improved"
            return False, "High severity divergence - review required"
        
        # Check tolerance
        if report.divergence_ratio > tolerance:
            return False, f"Divergence ratio {report.divergence_ratio:.1%} exceeds tolerance {tolerance:.1%}"
        
        # Check outcome
        if report.outcome_changed and not report.outcome_improved:
            return False, "Outcome changed negatively"
        
        return True, "Safe to deploy"
    
    def export_report(self, report: DivergenceReport, path: str) -> None:
        """Reportni faylga eksport qilish"""
        with open(path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"Divergence report exported to {path}")
    
    def get_analysis_history(self) -> List[DivergenceReport]:
        """Analysis historyni olish"""
        return self.analysis_history.copy()
    
    def clear_history(self) -> None:
        """Historyni tozalash"""
        self.analysis_history.clear()
        logger.info("Analysis history cleared")
