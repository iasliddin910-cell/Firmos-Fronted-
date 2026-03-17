"""
RealityGapReport - Internal vs External Gap Analysis
==============================================

Ichki va tashqi natijalar farqini hisoblash.

Bu modul:
- Ichki score > tashqi score farq
- Suite-level gap
- Capability-level gap
- Overfit detection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime


@dataclass
class GapAnalysis:
    """Gap analysis."""
    suite: str
    internal_score: float
    external_score: float
    gap: float  # internal - external
    gap_percentage: float  # (gap / external) * 100
    
    is_overfit: bool = False
    is_underfit: bool = False


@dataclass
class RealityGapReport:
    """Reality gap report."""
    generated_at: str
    
    # Overall
    avg_internal_score: float = 0.0
    avg_external_score: float = 0.0
    overall_gap: float = 0.0
    
    # By suite
    suite_gaps: List[GapAnalysis] = field(default_factory=list)
    
    # By capability
    capability_gaps: List[GapAnalysis] = field(default_factory=list)
    
    # Summary
    overfit_suites: List[str] = field(default_factory=list)
    underfit_suites: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)


class RealityGapAnalyzer:
    """
    Reality gap analyzer.
    """
    
    def __init__(self):
        self.threshold_overfit = 0.15  # 15% gap = overfit
        self.threshold_underfit = -0.10  # -10% gap = underfit
    
    def generate_report(
        self,
        internal_scores: Dict[str, float],
        external_scores: Dict[str, float],
    ) -> RealityGapReport:
        """Report generatsiya."""
        # Calculate overall
        avg_internal = sum(internal_scores.values()) / len(internal_scores) if internal_scores else 0
        avg_external = sum(external_scores.values()) / len(external_scores) if external_scores else 0
        overall_gap = avg_internal - avg_external
        
        # Suite gaps
        suite_gaps = []
        all_suites = set(internal_scores.keys()) | set(external_scores.keys())
        
        for suite in all_suites:
            internal = internal_scores.get(suite, 0)
            external = external_scores.get(suite, 0)
            gap = internal - external
            
            gap_pct = (gap / external * 100) if external > 0 else 0
            
            suite_gaps.append(GapAnalysis(
                suite=suite,
                internal_score=internal,
                external_score=external,
                gap=gap,
                gap_percentage=gap_pct,
                is_overfit=gap > self.threshold_overfit,
                is_underfit=gap < self.threshold_underfit,
            ))
        
        # Find overfit/underfit suites
        overfit = [g.suite for g in suite_gaps if g.is_overfit]
        underfit = [g.suite for g in suite_gaps if g.is_underfit]
        
        # Generate recommendations
        recommendations = []
        if overfit:
            recommendations.append(
                f"Overfit detected in: {', '.join(overfit)}. "
                "Consider external-style tasks in these suites."
            )
        if underfit:
            recommendations.append(
                f"Underfit detected in: {', '.join(underfit)}. "
                "Internal benchmarks may be too easy compared to external."
            )
        if overall_gap > 0.10:
            recommendations.append(
                f"Overall internal score {overall_gap:.1%} higher than external. "
                "Verify this isn't overfitting."
            )
        
        return RealityGapReport(
            generated_at=datetime.utcnow().isoformat(),
            avg_internal_score=avg_internal,
            avg_external_score=avg_external,
            overall_gap=overall_gap,
            suite_gaps=suite_gaps,
            overfit_suites=overfit,
            underfit_suites=underfit,
            recommendations=recommendations,
        )


def create_gap_analyzer() -> RealityGapAnalyzer:
    """Analyzer yaratish."""
    return RealityGapAnalyzer()
