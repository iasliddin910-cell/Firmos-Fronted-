"""
DifficultyCalibrator - Difficulty Prediction & Calibration Module

Bu modul task qiyinligini bashorat qiladi va real natijalar bilan 
qayta kalibrovka qiladi.

Kviz:
- predicted difficulty (bashorat)
- observed solve rate (haqiqiy)
- actual cost (haqiqiy xarajat)
- actual flakiness (noaniqlik)

Policy 1: Static benchmark yetmaydi.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict


class DifficultyLevel(Enum):
    """Task difficulty levels"""
    TRIVIAL = "trivial"       # >90% solve
    EASY = "easy"             # 70-90% solve
    MEDIUM = "medium"         # 40-70% solve
    HARD = "hard"             # 20-40% solve
    FRONTIER = "frontier"     # <20% solve


class CalibrationStatus(Enum):
    """Status of difficulty calibration"""
    UNCALIBRATED = "uncalibrated"
    CALIBRATING = "calibrating"
    CALIBRATED = "calibrated"
    STALE = "stale"
    RECALIBRATING = "recalibrating"


@dataclass
class DifficultyPrediction:
    """Initial difficulty prediction for a task"""
    task_id: str
    predicted_difficulty: float  # 0-1 scale
    confidence: float             # 0-1 confidence in prediction
    factors: Dict[str, float]    # Factors contributing to difficulty
    model_version: str
    timestamp: float


@dataclass
class CalibrationMetrics:
    """Observed metrics for calibration"""
    task_id: str
    run_count: int
    solve_rate: float
    median_time: float
    median_cost: float
    variance_time: float
    variance_cost: float
    flake_rate: float           # Rate of flaky failures
    first_pass_rate: float      # Pass on first attempt
    timestamp: float


@dataclass
class CalibratedDifficulty:
    """Final calibrated difficulty"""
    task_id: str
    predicted_difficulty: float
    observed_difficulty: float  # Derived from solve rate
    final_difficulty: float    # Blended prediction + observation
    confidence: float
    calibration_status: CalibrationStatus
    metrics: Optional[CalibrationMetrics]
    adjustment_history: List[Dict[str, Any]]


class DifficultyCalibrator:
    """
    Predicts and calibrates task difficulty.
    
    This module:
    1. Predicts difficulty before task runs
    2. Collects metrics during execution
    3. Recalibrates based on observed results
    4. Maintains difficulty labels over time
    """
    
    # Difficulty level thresholds
    DIFFICULTY_LEVELS = {
        DifficultyLevel.TRIVIAL: (0.9, 1.0),
        DifficultyLevel.EASY: (0.7, 0.9),
        DifficultyLevel.MEDIUM: (0.4, 0.7),
        DifficultyLevel.HARD: (0.2, 0.4),
        DifficultyLevel.FRONTIER: (0.0, 0.2)
    }
    
    # Calibration parameters
    MIN_RUNS_FOR_CALIBRATION = 5
    CONFIDENCE_DECAY_RATE = 0.95
    STALE_THRESHOLD_DAYS = 7
    RECALIBRATION_THRESHOLD = 0.15  # Recalibrate if observed differs by >15%
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.predictions: Dict[str, DifficultyPrediction] = {}
        self.calibrations: Dict[str, CalibrationMetrics] = {}
        self.final_difficulties: Dict[str, CalibratedDifficulty] = {}
        
    def predict_difficulty(
        self,
        task_id: str,
        task_features: Dict[str, Any]
    ) -> DifficultyPrediction:
        """
        Predict difficulty before task execution.
        
        Args:
            task_id: Unique task identifier
            task_features: Features of the task
            
        Returns:
            DifficultyPrediction with predicted difficulty
        """
        # Calculate difficulty from features
        factors = self._extract_difficulty_factors(task_features)
        predicted = self._compute_predicted_difficulty(factors)
        confidence = self._compute_confidence(factors)
        
        prediction = DifficultyPrediction(
            task_id=task_id,
            predicted_difficulty=predicted,
            confidence=confidence,
            factors=factors,
            model_version="v1.0",
            timestamp=0  # Will be set by caller
        )
        
        self.predictions[task_id] = prediction
        
        return prediction
    
    def record_metrics(
        self,
        task_id: str,
        passed: bool,
        time_taken: float,
        cost: float,
        is_flaky: bool = False,
        is_first_attempt: bool = True
    ) -> None:
        """
        Record execution metrics for calibration.
        
        Args:
            task_id: Task identifier
            passed: Whether task passed
            time_taken: Time taken in seconds
            cost: Cost of execution
            is_flaky: Whether this was a flaky result
            is_first_attempt: Whether this was first attempt
        """
        if task_id not in self.calibrations:
            self.calibrations[task_id] = CalibrationMetrics(
                task_id=task_id,
                run_count=0,
                solve_rate=0.0,
                median_time=0.0,
                median_cost=0.0,
                variance_time=0.0,
                variance_cost=0.0,
                flake_rate=0.0,
                first_pass_rate=0.0,
                timestamp=0
            )
        
        # Update metrics
        metrics = self.calibrations[task_id]
        
        # Initialize tracking lists if not exists
        if not hasattr(self, '_run_times'):
            self._run_times = defaultdict(list)
        if not hasattr(self, '_run_costs'):
            self._run_costs = defaultdict(list)
        if not hasattr(self, '_run_results'):
            self._run_results = defaultdict(list)
        if not hasattr(self, '_flaky_runs'):
            self._flaky_runs = defaultdict(list)
        if not hasattr(self, '_first_attempt'):
            self._first_attempt = defaultdict(list)
            
        # Track individual runs
        self._run_times[task_id].append(time_taken)
        self._run_costs[task_id].append(cost)
        self._run_results[task_id].append(passed)
        self._flaky_runs[task_id].append(is_flaky)
        self._first_attempt[task_id].append(is_first_attempt)
        
        # Recalculate aggregate metrics
        times = self._run_times[task_id]
        costs = self._run_costs[task_id]
        results = self._run_results[task_id]
        flakys = self._flaky_runs[task_id]
        firsts = self._first_attempt[task_id]
        
        metrics.run_count = len(results)
        metrics.solve_rate = sum(results) / len(results) if results else 0.0
        metrics.median_time = statistics.median(times) if times else 0.0
        metrics.median_cost = statistics.median(costs) if costs else 0.0
        metrics.variance_time = statistics.variance(times) if len(times) > 1 else 0.0
        metrics.variance_cost = statistics.variance(costs) if len(costs) > 1 else 0.0
        metrics.flake_rate = sum(flakys) / len(flakys) if flakys else 0.0
        metrics.first_pass_rate = sum(1 for r, f in zip(results, firsts) if r and f) / len(results) if results else 0.0
    
    def calibrate_difficulty(
        self,
        task_id: str,
        blending_weight: float = 0.5
    ) -> CalibratedDifficulty:
        """
        Calibrate difficulty based on observed results.
        
        Args:
            task_id: Task to calibrate
            blending_weight: Weight for prediction vs observation (0=pure prediction, 1=pure observation)
            
        Returns:
            CalibratedDifficulty with final difficulty
        """
        prediction = self.predictions.get(task_id)
        metrics = self.calibrations.get(task_id)
        
        if not metrics or metrics.run_count < self.MIN_RUNS_FOR_CALIBRATION:
            # Not enough data - use prediction only
            return CalibratedDifficulty(
                task_id=task_id,
                predicted_difficulty=prediction.predicted_difficulty if prediction else 0.5,
                observed_difficulty=0.5,
                final_difficulty=prediction.predicted_difficulty if prediction else 0.5,
                confidence=0.1,
                calibration_status=CalibrationStatus.CALIBRATING,
                metrics=metrics,
                adjustment_history=[]
            )
        
        # Convert solve rate to observed difficulty
        # Higher solve rate = lower difficulty
        observed_difficulty = 1.0 - metrics.solve_rate
        
        # Check if recalibration is needed
        needs_recalibration = False
        if prediction:
            diff = abs(observed_difficulty - prediction.predicted_difficulty)
            needs_recalibration = diff > self.RECALIBRATION_THRESHOLD
        
        # Blend prediction and observation
        final_difficulty = (
            (1 - blending_weight) * (prediction.predicted_difficulty if prediction else observed_difficulty) +
            blending_weight * observed_difficulty
        )
        
        # Calculate confidence based on run count and variance
        confidence = self._calculate_confidence(metrics)
        
        # Determine calibration status
        status = self._determine_status(metrics, needs_recalibration)
        
        # Build adjustment history
        history = []
        if prediction:
            history.append({
                "predicted": prediction.predicted_difficulty,
                "observed": observed_difficulty,
                "final": final_difficulty,
                "run_count": metrics.run_count
            })
        
        calibrated = CalibratedDifficulty(
            task_id=task_id,
            predicted_difficulty=prediction.predicted_difficulty if prediction else observed_difficulty,
            observed_difficulty=observed_difficulty,
            final_difficulty=final_difficulty,
            confidence=confidence,
            calibration_status=status,
            metrics=metrics,
            adjustment_history=history
        )
        
        self.final_difficulties[task_id] = calibrated
        
        return calibrated
    
    def _extract_difficulty_factors(
        self,
        features: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract factors that contribute to difficulty"""
        factors = {}
        
        # Code complexity factors
        factors['code_length'] = min(features.get('code_lines', 0) / 1000, 1.0)
        factors['file_count'] = min(features.get('file_count', 0) / 20, 1.0)
        factors['dependency_depth'] = min(features.get('dep_depth', 0) / 5, 1.0)
        
        # Task complexity
        factors['step_count'] = min(features.get('steps', 0) / 10, 1.0)
        factors['tool_diversity'] = min(features.get('tools_needed', 0) / 5, 1.0)
        
        # Ambiguity factors
        factors['spec_ambiguity'] = features.get('ambiguity', 0.0)
        factors['edge_cases'] = min(features.get('edge_cases', 0) / 5, 1.0)
        
        # Resource constraints
        factors['time_pressure'] = 1.0 - min(features.get('time_budget', 60) / 60, 1.0)
        factors['cost_pressure'] = 1.0 - min(features.get('cost_budget', 10) / 10, 1.0)
        
        return factors
    
    def _compute_predicted_difficulty(
        self,
        factors: Dict[str, float]
    ) -> float:
        """Compute predicted difficulty from factors"""
        # Weighted combination of factors
        weights = {
            'code_length': 0.15,
            'file_count': 0.1,
            'dependency_depth': 0.1,
            'step_count': 0.2,
            'tool_diversity': 0.1,
            'spec_ambiguity': 0.15,
            'edge_cases': 0.1,
            'time_pressure': 0.05,
            'cost_pressure': 0.05
        }
        
        predicted = sum(
            factors.get(factor, 0) * weight
            for factor, weight in weights.items()
        )
        
        return min(max(predicted, 0.0), 1.0)
    
    def _compute_confidence(
        self,
        factors: Dict[str, float]
    ) -> float:
        """Compute confidence in prediction based on feature completeness"""
        # More features = higher confidence
        present_features = sum(1 for v in factors.values() if v > 0)
        total_features = len(factors)
        
        base_confidence = present_features / total_features if total_features > 0 else 0.5
        
        # Boost for well-known factor ranges
        if 0.3 < factors.get('code_length', 0.5) < 0.7:
            base_confidence += 0.1
        if 0.3 < factors.get('step_count', 0.5) < 0.7:
            base_confidence += 0.1
            
        return min(base_confidence, 1.0)
    
    def _calculate_confidence(
        self,
        metrics: CalibrationMetrics
    ) -> float:
        """Calculate confidence from calibration metrics"""
        # More runs = higher confidence
        run_confidence = min(metrics.run_count / 20, 1.0) * 0.4
        
        # Lower variance = higher confidence
        time_confidence = max(0, 1 - metrics.variance_time / 100) * 0.3
        
        # Lower flakiness = higher confidence
        flake_confidence = (1 - metrics.flake_rate) * 0.3
        
        return run_confidence + time_confidence + flake_confidence
    
    def _determine_status(
        self,
        metrics: CalibrationMetrics,
        needs_recalibration: bool
    ) -> CalibrationStatus:
        """Determine calibration status"""
        if metrics.run_count < self.MIN_RUNS_FOR_CALIBRATION:
            return CalibrationStatus.CALIBRATING
        elif needs_recalibration:
            return CalibrationStatus.RECALIBRATING
        else:
            return CalibrationStatus.CALIBRATED
    
    def get_difficulty_level(
        self,
        difficulty: float
    ) -> DifficultyLevel:
        """Get difficulty level from difficulty score"""
        for level, (low, high) in self.DIFFICULTY_LEVELS.items():
            if low <= difficulty < high:
                return level
        return DifficultyLevel.MEDIUM
    
    def get_calibration_report(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """Get detailed calibration report for a task"""
        calibrated = self.final_difficulties.get(task_id)
        
        if not calibrated:
            return {"error": "No calibration data available"}
        
        return {
            "task_id": task_id,
            "predicted_difficulty": calibrated.predicted_difficulty,
            "observed_difficulty": calibrated.observed_difficulty,
            "final_difficulty": calibrated.final_difficulty,
            "difficulty_level": self.get_difficulty_level(calibrated.final_difficulty).value,
            "confidence": calibrated.confidence,
            "status": calibrated.calibration_status.value,
            "metrics": {
                "run_count": calibrated.metrics.run_count if calibrated.metrics else 0,
                "solve_rate": calibrated.metrics.solve_rate if calibrated.metrics else 0,
                "median_time": calibrated.metrics.median_time if calibrated.metrics else 0,
                "median_cost": calibrated.metrics.median_cost if calibrated.metrics else 0,
                "flake_rate": calibrated.metrics.flake_rate if calibrated.metrics else 0,
                "first_pass_rate": calibrated.metrics.first_pass_rate if calibrated.metrics else 0,
            } if calibrated.metrics else None,
            "adjustment_history": calibrated.adjustment_history
        }
    
    def get_overall_report(self) -> Dict[str, Any]:
        """Get overall calibration report"""
        calibrated_count = len(self.final_difficulties)
        calibrating_count = len([
            t for t in self.final_difficulties.values()
            if t.calibration_status == CalibrationStatus.CALIBRATING
        ])
        
        # Calculate difficulty distribution
        distribution = defaultdict(int)
        for diff in self.final_difficulties.values():
            level = self.get_difficulty_level(diff.final_difficulty)
            distribution[level.value] += 1
        
        return {
            "total_tasks": calibrated_count,
            "calibrating": calibrating_count,
            "difficulty_distribution": dict(distribution),
            "avg_confidence": statistics.mean(
                [c.confidence for c in self.final_difficulties.values()]
            ) if self.final_difficulties else 0
        }


__all__ = [
    'DifficultyCalibrator',
    'DifficultyLevel',
    'CalibrationStatus',
    'DifficultyPrediction',
    'CalibrationMetrics',
    'CalibratedDifficulty'
]
