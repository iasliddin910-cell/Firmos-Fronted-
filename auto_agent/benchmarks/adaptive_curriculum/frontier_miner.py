"""
FrontierMiner - Frontier Zone Discovery Module

This module identifies frontier zones where the agent is "almost solving" but not yet fully succeeding.
These zones (typically 30-70% solve rate) are the most valuable for generating new benchmark tasks.

Key signals:
- Solve rate between 30-70%
- High variance in results
- Repeated near-miss patterns
- Good partial artifacts but failed final verifier

Ushbu modul No1 World+ tizim uchun eng muhim qismlardan biri hisoblanadi.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict


class FrontierZoneType(Enum):
    """Frontier zone difficulty levels"""
    NEAR_EASY = "near_easy"        # 60-70% solve rate
    TRANSITION = "transition"       # 40-60% solve rate  
    NEAR_HARD = "near_hard"        # 30-40% solve rate
    FRONTIER = "frontier"          # <30% but >0% - breakthrough candidates


class SignalStrength(Enum):
    """Strength of frontier signals"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class FrontierSignal:
    """A signal indicating frontier zone potential"""
    task_id: str
    signal_type: str
    strength: SignalStrength
    solve_rate: float
    variance: float
    near_miss_count: int
    partial_artifact_quality: float
    raw_score: float


@dataclass
class DiscoveredZone:
    """A discovered frontier zone"""
    zone_type: FrontierZoneType
    task_ids: List[str]
    avg_solve_rate: float
    variance: float
    signal_strength: SignalStrength
    recommended_action: str
    diagnostic_value: float


@dataclass
class TaskResult:
    """Individual task result from evaluation"""
    task_id: str
    passed: bool
    score: float
    time_taken: float
    cost: float
    partial_artifact: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    near_miss: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class FrontierMiner:
    """
    Discovers frontier zones in benchmark results.
    
    Frontier zones are areas where the agent is "almost but not quite" succeeding.
    These are the most valuable zones for generating new tasks because:
    1. They indicate genuine capability boundaries
    2. They provide clear diagnostic signals
    3. They offer the best learning opportunities for improvement
    
    Policy 1: Static benchmark yetmaydi.
    Policy 4: Near-frontier zone benchmarkning eng qimmat qismi.
    """
    
    # Configuration thresholds
    NEAR_EASY_THRESHOLD = (0.60, 0.70)
    TRANSITION_THRESHOLD = (0.40, 0.60)
    NEAR_HARD_THRESHOLD = (0.30, 0.40)
    FRONTIER_THRESHOLD = (0.01, 0.30)
    
    # Signal thresholds
    HIGH_VARIANCE_THRESHOLD = 0.15
    NEAR_MISS_THRESHOLD = 2
    PARTIAL_ARTIFACT_THRESHOLD = 0.5
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.thresholds = self._load_thresholds()
        self._zone_cache: Dict[str, DiscoveredZone] = {}
        
    def _load_thresholds(self) -> Dict[str, Tuple[float, float]]:
        """Load configurable thresholds"""
        return {
            'near_easy': self.config.get('near_easy', self.NEAR_EASY_THRESHOLD),
            'transition': self.config.get('transition', self.TRANSITION_THRESHOLD),
            'near_hard': self.config.get('near_hard', self.NEAR_HARD_THRESHOLD),
            'frontier': self.config.get('frontier', self.FRONTIER_THRESHOLD),
        }
    
    def analyze_results(self, results: List[TaskResult]) -> List[FrontierSignal]:
        """
        Analyze task results and identify frontier signals.
        
        Args:
            results: List of TaskResult from benchmark evaluation
            
        Returns:
            List of FrontierSignal objects indicating potential frontier zones
        """
        # Group results by task_id
        task_groups: Dict[str, List[TaskResult]] = defaultdict(list)
        for result in results:
            task_groups[result.task_id].append(result)
        
        signals = []
        
        for task_id, task_results in task_groups.items():
            signal = self._analyze_task_group(task_id, task_results)
            if signal and self._is_frontier_signal(signal):
                signals.append(signal)
        
        # Sort by diagnostic value (most valuable first)
        signals.sort(key=lambda s: self._compute_diagnostic_value(s), reverse=True)
        
        return signals
    
    def _analyze_task_group(self, task_id: str, results: List[TaskResult]) -> Optional[FrontierSignal]:
        """Analyze a group of results for a single task"""
        if len(results) < 1:
            return None
            
        passed = sum(1 for r in results if r.passed)
        solve_rate = passed / len(results)
        
        # Calculate variance
        scores = [r.score for r in results]
        variance = statistics.variance(scores) if len(scores) > 1 else 0.0
        
        # Count near-misses
        near_miss_count = sum(1 for r in results if r.near_miss)
        
        # Assess partial artifact quality
        partial_qualities = [r.partial_artifact.get('quality', 0) for r in results if r.partial_artifact]
        avg_partial_quality = statistics.mean(partial_qualities) if partial_qualities else 0.0
        
        # Determine signal strength
        strength = self._compute_signal_strength(
            solve_rate=solve_rate,
            variance=variance,
            near_miss_count=near_miss_count,
            partial_artifact_quality=avg_partial_quality
        )
        
        # Compute raw score (composite metric)
        raw_score = self._compute_raw_score(
            solve_rate=solve_rate,
            variance=variance,
            near_miss_count=near_miss_count,
            partial_artifact_quality=avg_partial_quality
        )
        
        return FrontierSignal(
            task_id=task_id,
            signal_type=self._classify_signal_type(solve_rate, variance),
            strength=strength,
            solve_rate=solve_rate,
            variance=variance,
            near_miss_count=near_miss_count,
            partial_artifact_quality=avg_partial_quality,
            raw_score=raw_score
        )
    
    def _is_frontier_signal(self, signal: FrontierSignal) -> bool:
        """Check if a signal indicates a frontier zone"""
        return (
            self.thresholds['near_easy'][0] <= signal.solve_rate <= self.thresholds['near_easy'][1] or
            self.thresholds['transition'][0] <= signal.solve_rate <= self.thresholds['transition'][1] or
            self.thresholds['near_hard'][0] <= signal.solve_rate <= self.thresholds['near_hard'][1] or
            self.thresholds['frontier'][0] <= signal.solve_rate <= self.thresholds['frontier'][1]
        )
    
    def _compute_signal_strength(
        self,
        solve_rate: float,
        variance: float,
        near_miss_count: int,
        partial_artifact_quality: float
    ) -> SignalStrength:
        """Compute the strength of a frontier signal"""
        score = 0
        
        # Solve rate in optimal range (30-70%) gets points
        if 0.30 <= solve_rate <= 0.70:
            score += 2
        elif 0.20 <= solve_rate <= 0.80:
            score += 1
            
        # High variance indicates instability (good for frontier)
        if variance > self.HIGH_VARIANCE_THRESHOLD:
            score += 2
        elif variance > self.HIGH_VARIANCE_THRESHOLD / 2:
            score += 1
            
        # Near-misses indicate almost-succeeding
        if near_miss_count >= self.NEAR_MISS_THRESHOLD:
            score += 2
        elif near_miss_count > 0:
            score += 1
            
        # Partial artifacts show progress
        if partial_artifact_quality > self.PARTIAL_ARTIFACT_THRESHOLD:
            score += 1
            
        if score >= 6:
            return SignalStrength.VERY_STRONG
        elif score >= 4:
            return SignalStrength.STRONG
        elif score >= 2:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _compute_raw_score(
        self,
        solve_rate: float,
        variance: float,
        near_miss_count: int,
        partial_artifact_quality: float
    ) -> float:
        """Compute raw diagnostic score for a signal"""
        score = 0.0
        
        # Optimal solve rate zone (most diagnostic)
        if 0.30 <= solve_rate <= 0.70:
            score += 1.0
        elif 0.20 <= solve_rate <= 0.80:
            score += 0.5
            
        # Variance adds diagnostic value
        score += min(variance * 2, 1.0)
        
        # Near-misses are highly diagnostic
        score += min(near_miss_count * 0.2, 0.5)
        
        # Partial artifacts show progress toward solution
        score += partial_artifact_quality * 0.5
        
        return score
    
    def _classify_signal_type(self, solve_rate: float, variance: float) -> str:
        """Classify the type of frontier signal"""
        if solve_rate >= 0.60:
            return "near_success"
        elif solve_rate >= 0.40:
            return "transition_zone"
        elif solve_rate >= 0.30:
            return "struggling"
        else:
            return "breakthrough_candidate"
    
    def _compute_diagnostic_value(self, signal: FrontierSignal) -> float:
        """Compute the diagnostic value of a signal"""
        value = signal.raw_score
        value += signal.variance * 0.5
        value += signal.near_miss_count * 0.1
        if signal.partial_artifact_quality > 0.5:
            value += 0.2
        return value
    
    def discover_zones(self, signals: List[FrontierSignal]) -> List[DiscoveredZone]:
        """Group signals into frontier zones"""
        zones = {
            FrontierZoneType.NEAR_EASY: [],
            FrontierZoneType.TRANSITION: [],
            FrontierZoneType.NEAR_HARD: [],
            FrontierZoneType.FRONTIER: []
        }
        
        for signal in signals:
            zone_type = self._classify_zone(signal.solve_rate)
            zones[zone_type].append(signal)
        
        result = []
        for zone_type, zone_signals in zones.items():
            if zone_signals:
                zone = self._create_zone(zone_type, zone_signals)
                result.append(zone)
        
        result.sort(key=lambda z: self._zone_priority(z.zone_type), reverse=True)
        
        return result
    
    def _classify_zone(self, solve_rate: float) -> FrontierZoneType:
        """Classify solve rate into frontier zone type"""
        if self.thresholds['near_easy'][0] <= solve_rate <= self.thresholds['near_easy'][1]:
            return FrontierZoneType.NEAR_EASY
        elif self.thresholds['transition'][0] <= solve_rate <= self.thresholds['transition'][1]:
            return FrontierZoneType.TRANSITION
        elif self.thresholds['near_hard'][0] <= solve_rate <= self.thresholds['near_hard'][1]:
            return FrontierZoneType.NEAR_HARD
        else:
            return FrontierZoneType.FRONTIER
    
    def _create_zone(self, zone_type: FrontierZoneType, signals: List[FrontierSignal]) -> DiscoveredZone:
        """Create a DiscoveredZone from signals"""
        solve_rates = [s.solve_rate for s in signals]
        variances = [s.variance for s in signals]
        
        avg_solve_rate = statistics.mean(solve_rates)
        avg_variance = statistics.mean(variances)
        
        strengths = [s.strength for s in signals]
        overall_strength = max(strengths, key=lambda s: s.value)
        
        recommended_action = self._get_recommended_action(zone_type)
        diagnostic_value = statistics.mean([self._compute_diagnostic_value(s) for s in signals])
        
        return DiscoveredZone(
            zone_type=zone_type,
            task_ids=[s.task_id for s in signals],
            avg_solve_rate=avg_solve_rate,
            variance=avg_variance,
            signal_strength=overall_strength,
            recommended_action=recommended_action,
            diagnostic_value=diagnostic_value
        )
    
    def _get_recommended_action(self, zone_type: FrontierZoneType) -> str:
        """Get recommended action for a zone type"""
        actions = {
            FrontierZoneType.NEAR_EASY: "maintain_monitor",
            FrontierZoneType.TRANSITION: "generate_harder_variants",
            FrontierZoneType.NEAR_HARD: "focus_improvement",
            FrontierZoneType.FRONTIER: "breakthrough_exploration"
        }
        return actions.get(zone_type, "analyze_further")
    
    def _zone_priority(self, zone_type: FrontierZoneType) -> float:
        """Get priority score for zone type"""
        priorities = {
            FrontierZoneType.TRANSITION: 1.0,
            FrontierZoneType.NEAR_HARD: 0.8,
            FrontierZoneType.FRONTIER: 0.6,
            FrontierZoneType.NEAR_EASY: 0.4
        }
        return priorities.get(zone_type, 0.0)
    
    def get_frontier_report(self, results: List[TaskResult]) -> Dict[str, Any]:
        """Generate a comprehensive frontier report"""
        signals = self.analyze_results(results)
        zones = self.discover_zones(signals)
        
        return {
            "total_signals": len(signals),
            "zones": [
                {
                    "type": z.zone_type.value,
                    "task_count": len(z.task_ids),
                    "avg_solve_rate": z.avg_solve_rate,
                    "variance": z.variance,
                    "signal_strength": z.signal_strength.value,
                    "recommended_action": z.recommended_action,
                    "diagnostic_value": z.diagnostic_value,
                    "task_ids": z.task_ids[:10]
                }
                for z in zones
            ],
            "top_frontier_tasks": [s.task_id for s in signals[:20]],
            "summary": self._generate_summary(zones)
        }
    
    def _generate_summary(self, zones: List[DiscoveredZone]) -> str:
        """Generate text summary of frontier analysis"""
        if not zones:
            return "No frontier zones detected."
            
        lines = []
        for zone in zones:
            lines.append(
                f"{zone.zone_type.value}: {len(zone.task_ids)} tasks "
                f"(solve rate: {zone.avg_solve_rate:.1%}, "
                f"action: {zone.recommended_action})"
            )
        
        return "\n".join(lines)


__all__ = [
    'FrontierMiner',
    'FrontierSignal', 
    'DiscoveredZone',
    'TaskResult',
    'FrontierZoneType',
    'SignalStrength'
]
