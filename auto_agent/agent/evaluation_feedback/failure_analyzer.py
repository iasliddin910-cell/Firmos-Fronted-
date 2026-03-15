"""
Failure Analyzer - Evaluation-Driven Control System
==================================================

This module analyzes benchmark results and generates failure diagnoses.
It transforms raw scores into actionable insights for the agent.

The FailureAnalyzer:
1. Takes benchmark results, traces, and telemetry
2. Applies failure taxonomy to classify issues
3. Identifies root causes vs symptoms
4. Generates targeted intervention suggestions

This closes the loop between evaluation and improvement.
"""
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .signals.failure_taxonomy import (
    FailureType, FailureSeverity, Subsystem, FailureLabel,
    FailureEvidence, CAPABILITY_TAXONOMY, get_failure_patterns,
    get_subsystem_for_failure, get_intervention_for_failure
)

logger = logging.getLogger(__name__)


@dataclass
class TraceEvent:
    """Single event in an execution trace"""
    timestamp: float
    event_type: str  # "tool_call", "retry", "error", "memory_access"
    details: Dict
    subsystem: Optional[str] = None


@dataclass
class DiagnosisResult:
    """Complete diagnosis from analyzing a failure"""
    failure_label: FailureLabel
    
    # Root cause analysis
    root_cause: Optional[str] = None
    symptom_chain: List[str] = field(default_factory=list)
    
    # Affected capabilities
    affected_capabilities: List[str] = field(default_factory=list)
    severity_score: float = 0.0
    
    # Recommended actions
    immediate_action: Optional[str] = None
    long_term_actions: List[str] = field(default_factory=list)
    
    # Evidence summary
    evidence_count: int = 0
    confidence_factors: Dict[str, float] = field(default_factory=dict)


class FailureAnalyzer:
    """
    ADVANCED Failure Analyzer that transforms benchmark scores into diagnoses.
    
    This is the CORE of the feedback loop:
    - Input: benchmark results, traces, telemetry
    - Output: FailureLabel with root cause and intervention suggestions
    
    The analyzer uses multiple strategies:
    1. Pattern matching against known failure signatures
    2. Trace analysis for execution flow issues
    3. Telemetry correlation for performance issues
    4. Diff analysis for patch failures
    """
    
    def __init__(self):
        # Known failure patterns
        self.patterns = get_failure_patterns()
        
        # Diagnosis history
        self.diagnosis_history: List[DiagnosisResult] = []
        
        # Failure statistics
        self.failure_stats: Dict[FailureType, int] = defaultdict(int)
        
        # Subsystem failure rates
        self.subsystem_failure_rates: Dict[Subsystem, List[float]] = defaultdict(list)
        
        logger.info("🔍 FailureAnalyzer initialized - ADVANCED diagnosis ENABLED")
    
    def analyze(
        self,
        benchmark_result: Dict,
        trace: Optional[List[TraceEvent]] = None,
        telemetry: Optional[Dict] = None,
        verifier_result: Optional[Dict] = None,
        diff: Optional[str] = None
    ) -> FailureLabel:
        """
        Main entry point: Analyze a failure and generate diagnosis.
        
        This transforms raw benchmark output into a structured FailureLabel.
        """
        # Step 1: Extract failure indicators
        indicators = self._extract_indicators(
            benchmark_result, trace, telemetry, verifier_result, diff
        )
        
        # Step 2: Match against known patterns
        matched_type, confidence = self._match_patterns(indicators)
        
        # Step 3: Determine severity
        severity = self._determine_severity(indicators, benchmark_result)
        
        # Step 4: Identify affected subsystems
        affected_subsystems = self._identify_affected_subsystems(
            matched_type, indicators
        )
        
        # Step 5: Generate evidence list
        evidence = self._build_evidence(indicators, trace, telemetry, diff)
        
        # Step 6: Determine if root cause or symptom
        is_root_cause = self._is_root_cause(matched_type, indicators)
        
        # Step 7: Get suggested interventions
        suggested_interventions = self._get_interventions(
            matched_type, indicators
        )
        
        # Build the failure label
        failure_label = FailureLabel(
            failure_type=matched_type,
            severity=severity,
            confidence=confidence,
            is_root_cause=is_root_cause,
            evidence=evidence,
            affected_subsystems=affected_subsystems,
            failed_capability=self._get_failed_capability(indicators),
            error_message=indicators.get("error_message"),
            error_location=indicators.get("error_location"),
            task_id=benchmark_result.get("task_id"),
            suggested_interventions=suggested_interventions
        )
        
        # Update statistics
        self.failure_stats[matched_type] += 1
        for subsystem in affected_subsystems:
            self.subsystem_failure_rates[subsystem].append(1.0)
        
        # Build diagnosis result
        diagnosis = self._build_diagnosis(failure_label, indicators)
        self.diagnosis_history.append(diagnosis)
        
        logger.info(f"🔍 Failure diagnosed: {matched_type.value} "
                   f"(confidence: {confidence:.2f}, severity: {severity.value})")
        
        return failure_label
    
    def _extract_indicators(
        self,
        benchmark_result: Dict,
        trace: Optional[List[TraceEvent]],
        telemetry: Optional[Dict],
        verifier_result: Optional[Dict],
        diff: Optional[str]
    ) -> Dict:
        """Extract failure indicators from all sources"""
        indicators = {}
        
        # From benchmark result
        if benchmark_result:
            indicators["passed"] = benchmark_result.get("passed", False)
            indicators["score"] = benchmark_result.get("score", 0.0)
            indicators["success_rate"] = benchmark_result.get("success_rate", 0.0)
            indicators["latency_ms"] = benchmark_result.get("latency_ms", 0)
            indicators["error_message"] = benchmark_result.get("error")
            indicators["task_type"] = benchmark_result.get("task_type", "unknown")
            
            # Failure-specific indicators
            if benchmark_result.get("regression_detected"):
                indicators["regression"] = True
            if benchmark_result.get("timeout"):
                indicators["timeout"] = True
            if benchmark_result.get("step_count", 0) > 20:
                indicators["excessive_steps"] = True
            if benchmark_result.get("retry_count", 0) > 3:
                indicators["high_retries"] = True
        
        # From trace
        if trace:
            tool_calls = [e for e in trace if e.event_type == "tool_call"]
            errors = [e for e in trace if e.event_type == "error"]
            retries = [e for e in trace if e.event_type == "retry"]
            
            indicators["tool_call_count"] = len(tool_calls)
            indicators["error_count"] = len(errors)
            indicators["retry_count"] = len(retries)
            
            # Check for thrashing
            if len(retries) > 5:
                indicators["thrashing"] = True
            
            # Check for wrong tool
            if tool_calls:
                last_tool = tool_calls[-1].details.get("tool_name")
                indicators["last_tool"] = last_tool
        
        # From telemetry
        if telemetry:
            indicators["memory_usage"] = telemetry.get("memory_mb", 0)
            indicators["cpu_percent"] = telemetry.get("cpu_percent", 0)
            
            # Check for performance issues
            if telemetry.get("latency_ms", 0) > 30000:
                indicators["high_latency"] = True
        
        # From verifier result
        if verifier_result:
            if verifier_result.get("false_positive"):
                indicators["false_positive"] = True
            if verifier_result.get("false_negative"):
                indicators["false_negative"] = True
        
        # From diff
        if diff:
            indicators["has_diff"] = True
            if "benchmark" in diff.lower() and "fake" in diff.lower():
                indicators["potential_tampering"] = True
            if "forbidden" in diff.lower() or "restricted" in diff.lower():
                indicators["forbidden_edit"] = True
        
        return indicators
    
    def _match_patterns(self, indicators: Dict) -> Tuple[FailureType, float]:
        """Match indicators against known failure patterns"""
        matched_type = FailureType.PLANNING_FAILURE  # Default
        best_confidence = 0.0
        
        for failure_type, pattern in self.patterns.items():
            # Check each indicator in pattern
            matches = 0
            for indicator_name in pattern["indicators"]:
                if indicator_name in indicators:
                    matches += 1
            
            if matches > 0:
                confidence = matches / len(pattern["indicators"])
                if confidence > best_confidence:
                    best_confidence = confidence
                    matched_type = failure_type
        
        # Adjust confidence based on specific indicators
        if indicators.get("thrashing"):
            matched_type = FailureType.THRASH_FAILURE
            best_confidence = 0.85
        
        if indicators.get("high_retries") and indicators.get("excessive_steps"):
            matched_type = FailureType.PLANNING_ZERO_PROGRESS
            best_confidence = 0.75
        
        if indicators.get("false_positive"):
            matched_type = FailureType.VERIFICATION_FALSE_POSITIVE
            best_confidence = 0.9
        
        if indicators.get("forbidden_edit"):
            matched_type = FailureType.FORBIDDEN_EDIT_FAILURE
            best_confidence = 0.95
        
        if indicators.get("timeout") or indicators.get("high_latency"):
            matched_type = FailureType.LATENCY_FAILURE
            best_confidence = 0.8
        
        return matched_type, best_confidence
    
    def _determine_severity(
        self,
        indicators: Dict,
        benchmark_result: Dict
    ) -> FailureSeverity:
        """Determine failure severity"""
        # Critical indicators
        if indicators.get("forbidden_edit"):
            return FailureSeverity.CRITICAL
        if indicators.get("potential_tampering"):
            return FailureSeverity.CRITICAL
        
        # High severity
        if indicators.get("regression"):
            return FailureSeverity.HIGH
        if indicators.get("false_positive"):
            return FailureSeverity.HIGH
        
        # Medium severity
        score = indicators.get("score", 1.0)
        if score < 0.5:
            return FailureSeverity.MEDIUM
        if indicators.get("thrashing"):
            return FailureSeverity.MEDIUM
        
        # Low severity
        if indicators.get("high_latency"):
            return FailureSeverity.LOW
        
        return FailureSeverity.INFO
    
    def _identify_affected_subsystems(
        self,
        failure_type: FailureType,
        indicators: Dict
    ) -> List[Subsystem]:
        """Identify subsystems affected by this failure"""
        # Get base subsystems from taxonomy
        subsystems = get_subsystem_for_failure(failure_type)
        
        # Adjust based on indicators
        if indicators.get("high_retries"):
            if Subsystem.PLANNER not in subsystems:
                subsystems.append(Subsystem.PLANNER)
        
        if indicators.get("tool_call_count", 0) > 10:
            if Subsystem.TOOL_ROUTER not in subsystems:
                subsystems.append(Subsystem.TOOL_ROUTER)
        
        return subsystems if subsystems else [Subsystem.PLANNER]
    
    def _build_evidence(
        self,
        indicators: Dict,
        trace: Optional[List[TraceEvent]],
        telemetry: Optional[Dict],
        diff: Optional[str]
    ) -> List[FailureEvidence]:
        """Build evidence list for the failure"""
        evidence = []
        
        # Benchmark evidence
        if "error_message" in indicators:
            evidence.append(FailureEvidence(
                evidence_type="benchmark_result",
                description=f"Error: {indicators['error_message']}",
                raw_data=indicators
            ))
        
        # Trace evidence
        if trace:
            errors = [e for e in trace if e.event_type == "error"]
            if errors:
                evidence.append(FailureEvidence(
                    evidence_type="trace",
                    description=f"Found {len(errors)} errors in trace",
                    raw_data={"error_count": len(errors)}
                ))
        
        # Telemetry evidence
        if telemetry:
            evidence.append(FailureEvidence(
                evidence_type="telemetry",
                description="Performance telemetry available",
                raw_data=telemetry
            ))
        
        # Diff evidence
        if diff:
            evidence.append(FailureEvidence(
                evidence_type="diff",
                description="Code diff available for analysis",
                raw_data={"diff_length": len(diff)}
            ))
        
        return evidence
    
    def _is_root_cause(
        self,
        failure_type: FailureType,
        indicators: Dict
    ) -> bool:
        """Determine if this is root cause or symptom"""
        # These are typically root causes
        root_cause_types = [
            FailureType.PLANNING_FAILURE,
            FailureType.TOOL_SELECTION_FAILURE,
            FailureType.RETRIEVAL_FAILURE,
            FailureType.FORBIDDEN_EDIT_FAILURE
        ]
        
        if failure_type in root_cause_types:
            return True
        
        # Check for clear root indicators
        if indicators.get("excessive_steps") and indicators.get("high_retries"):
            return True
        
        return False
    
    def _get_interventions(
        self,
        failure_type: FailureType,
        indicators: Dict
    ) -> List[str]:
        """Get suggested interventions for this failure"""
        # Get base intervention from taxonomy
        intervention = get_intervention_for_failure(failure_type)
        
        interventions = [intervention]
        
        # Add specific interventions based on indicators
        if indicators.get("thrashing"):
            interventions.append("retry_budget_tuner:add_diversification")
        
        if indicators.get("high_retries"):
            interventions.append("planner_policy_adapter:add_early_checkpoint")
        
        if indicators.get("excessive_steps"):
            interventions.append("planner_policy_adapter:reduce_plan_depth")
        
        if indicators.get("high_latency"):
            interventions.append("planner_policy_adapter:tighten_timeout")
        
        if indicators.get("timeout"):
            interventions.append("retry_budget_tuner:add_timeout_handling")
        
        return interventions
    
    def _get_failed_capability(self, indicators: Dict) -> str:
        """Identify which capability failed"""
        task_type = indicators.get("task_type", "unknown")
        
        capability_map = {
            "planning": "planning",
            "retrieval": "retrieval",
            "tool_routing": "tool_routing",
            "patch": "patching",
            "browser": "browser_recovery",
            "coding": "code_generation",
            "debugging": "debugging"
        }
        
        return capability_map.get(task_type, "unknown")
    
    def _build_diagnosis(
        self,
        failure_label: FailureLabel,
        indicators: Dict
    ) -> DiagnosisResult:
        """Build comprehensive diagnosis result"""
        diagnosis = DiagnosisResult(
            failure_label=failure_label,
            affected_capabilities=[failure_label.failed_capability] if failure_label.failed_capability else [],
            severity_score=self._calculate_severity_score(indicators)
        )
        
        # Set immediate action
        if failure_label.suggested_interventions:
            diagnosis.immediate_action = failure_label.suggested_interventions[0]
            diagnosis.long_term_actions = failure_label.suggested_interventions[1:]
        
        # Set evidence count
        diagnosis.evidence_count = len(failure_label.evidence)
        
        return diagnosis
    
    def _calculate_severity_score(self, indicators: Dict) -> float:
        """Calculate numerical severity score (0-1)"""
        score = 0.5  # Base score
        
        if indicators.get("forbidden_edit"):
            score += 0.5
        if indicators.get("regression"):
            score += 0.3
        if indicators.get("thrashing"):
            score += 0.2
        if indicators.get("false_positive"):
            score += 0.3
        
        return min(1.0, score)
    
    def analyze_batch(
        self,
        results: List[Dict],
        traces: Optional[List[List[TraceEvent]]] = None
    ) -> List[FailureLabel]:
        """Analyze multiple failures and return diagnoses"""
        diagnoses = []
        
        for i, result in enumerate(results):
            trace = traces[i] if traces and i < len(traces) else None
            diagnosis = self.analyze(result, trace=trace)
            diagnoses.append(diagnosis)
        
        return diagnoses
    
    def get_failure_summary(self) -> Dict:
        """Get summary of all failures analyzed"""
        total = sum(self.failure_stats.values())
        
        return {
            "total_failures": total,
            "by_type": {
                ft.value: count for ft, count in self.failure_stats.items()
            },
            "top_failures": sorted(
                [(ft.value, count) for ft, count in self.failure_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def get_subsystem_health(self) -> Dict:
        """Get health report for each subsystem"""
        health = {}
        
        for subsystem, failures in self.subsystem_failure_rates.items():
            if failures:
                failure_rate = sum(failures) / len(failures)
                health[subsystem.value] = {
                    "failure_count": len(failures),
                    "failure_rate": failure_rate,
                    "health_score": 1.0 - failure_rate
                }
            else:
                health[subsystem.value] = {
                    "failure_count": 0,
                    "failure_rate": 0.0,
                    "health_score": 1.0
                }
        
        return health


def create_failure_analyzer() -> FailureAnalyzer:
    """Factory function to create FailureAnalyzer"""
    return FailureAnalyzer()
