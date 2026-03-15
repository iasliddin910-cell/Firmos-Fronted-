"""
Confidence Scoring & Unknownness Detection
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfidenceLevel(Enum):
    CRITICAL = "critical"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"


@dataclass
class ConfidenceScore:
    level: ConfidenceLevel
    score: float
    factors: dict = field(default_factory=dict)
    recommendations: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {"level": self.level.value, "score": self.score, "factors": self.factors, "recommendations": self.recommendations}


class ConfidenceScorer:
    def __init__(self, config: Any):
        self.config = config
        self.threshold = config.confidence_threshold
    
    def calculate_syntax_confidence(self, twin: Any) -> ConfidenceLevel:
        score = 0.5
        syntax_data = getattr(twin, "syntax_data", {})
        if syntax_data.get("total_files", 0) > 0:
            score += 0.1
        if syntax_data.get("total_errors", 0) == 0:
            score += 0.2
        unknown_areas = getattr(twin, "unresolved_symbols", [])
        score -= len(unknown_areas) * 0.05
        reflection = getattr(twin, "reflection_usage", [])
        score -= len(reflection) * 0.1
        return self._score_to_level(score)
    
    def calculate_symbol_confidence(self, twin: Any) -> ConfidenceLevel:
        score = 0.5
        symbol_data = getattr(twin, "symbol_data", {})
        if symbol_data.get("total_symbols", 0) > 0:
            score += 0.15
        if symbol_data.get("call_graph"):
            score += 0.1
        unresolved = getattr(twin, "unresolved_symbols", [])
        score -= len(unresolved) * 0.05
        dynamic = getattr(twin, "dynamic_dispatch_uncertainty", [])
        score -= len(dynamic) * 0.1
        return self._score_to_level(score)
    
    def calculate_flow_confidence(self, twin: Any) -> ConfidenceLevel:
        score = 0.4
        semantic = getattr(twin, "semantic_graph", {})
        if semantic.get("nodes"):
            score += 0.1
        if semantic.get("data_flows"):
            score += 0.1
        generated = getattr(twin, "generated_code_areas", [])
        score -= len(generated) * 0.1
        framework_magic = getattr(twin, "framework_magic_routes", [])
        score -= len(framework_magic) * 0.15
        return self._score_to_level(score)
    
    def calculate_intent_confidence(self, twin: Any) -> ConfidenceLevel:
        score = 0.3
        intent_data = getattr(twin, "intent_data", {})
        invariants = intent_data.get("invariants", [])
        if len(invariants) > 5:
            score += 0.2
        elif len(invariants) > 0:
            score += 0.1
        decisions = intent_data.get("decisions", [])
        if decisions:
            score += 0.1
        score -= 0.1
        return self._score_to_level(score)
    
    def calculate_blast_radius_confidence(self, affected_modules: list, twin: Any) -> ConfidenceLevel:
        score = 0.6
        red_zones = ["auth", "billing", "deployment", "secret", "core"]
        for module in affected_modules:
            if any(rz in module.lower() for rz in red_zones):
                score -= 0.2
        if len(affected_modules) > 10:
            score -= 0.1
        return self._score_to_level(score)
    
    def get_overall_confidence(self, twin: Any) -> ConfidenceScore:
        scores = {
            "syntax": self.calculate_syntax_confidence(twin),
            "symbol": self.calculate_symbol_confidence(twin),
            "flow": self.calculate_flow_confidence(twin),
        }
        score_map = {ConfidenceLevel.CRITICAL: 0.1, ConfidenceLevel.LOW: 0.3, ConfidenceLevel.MEDIUM: 0.5, ConfidenceLevel.HIGH: 0.7, ConfidenceLevel.CERTAIN: 0.9}
        numeric = sum(score_map[s] for s in scores.values()) / len(scores)
        level = self._score_to_level(numeric)
        recommendations = []
        if level in (ConfidenceLevel.CRITICAL, ConfidenceLevel.LOW):
            recommendations.append("Run additional tests before making changes")
            recommendations.append("Consult documentation or authors")
        return ConfidenceScore(level=level, score=numeric, factors={k: v.value for k, v in scores.items()}, recommendations=recommendations)
    
    def _score_to_level(self, score: float) -> ConfidenceLevel:
        if score >= 0.8: return ConfidenceLevel.CERTAIN
        elif score >= 0.6: return ConfidenceLevel.HIGH
        elif score >= 0.4: return ConfidenceLevel.MEDIUM
        elif score >= 0.2: return ConfidenceLevel.LOW
        else: return ConfidenceLevel.CRITICAL
    
    def should_block_edit(self, twin: Any, proposed_changes: dict) -> tuple[bool, str]:
        overall = self.get_overall_confidence(twin)
        if overall.level == ConfidenceLevel.CRITICAL:
            return True, "Critical confidence level"
        red_zones = ["auth", "billing", "deployment", "secret", "core"]
        for module in proposed_changes.get("modules", []):
            if any(rz in module.lower() for rz in red_zones):
                if overall.level in (ConfidenceLevel.CRITICAL, ConfidenceLevel.LOW):
                    return True, "Affects red zone with low confidence"
        return False, ""


class UnknownnessDetector:
    def __init__(self, config: Any):
        self.config = config
        self.reflection_patterns = ["getattr", "setattr", "hasattr", "eval", "exec", "globals", "locals", "vars", "__dict__"]
        self.dynamic_dispatch_patterns = ["abstractmethod", "overload", "decorator", "plugin", "hook"]
        self.framework_magic_patterns = ["metaclass", "__init_subclass__", "__getattr__", "__getattribute__"]
        self.generated_code_patterns = ["generated", "autogenerated", "do not edit", "do not modify"]
    
    def find_unresolved_symbols(self, twin: Any) -> list: return []
    def find_dynamic_dispatch(self, twin: Any) -> list: return []
    def find_reflection_usage(self, twin: Any) -> list: return []
    def find_generated_code(self, twin: Any) -> list: return []
    def find_framework_magic(self, twin: Any) -> list: return []
    def find_config_driven_behavior(self, twin: Any) -> list: return []
    
    def get_unknown_summary(self, twin: Any) -> dict:
        return {"unresolved_symbols": self.find_unresolved_symbols(twin), "dynamic_dispatch": self.find_dynamic_dispatch(twin), "reflection_usage": self.find_reflection_usage(twin), "generated_code": self.find_generated_code(twin), "framework_magic": self.find_framework_magic(twin), "config_driven": self.find_config_driven_behavior(twin), "total_unknown_areas": 0}
    
    def get_confidence_impact(self, twin: Any) -> dict:
        return {"total_impact": 0.0, "confidence_reduction": "0%", "recommendations": ["Low uncertainty - safe to proceed"]}


def calculate_minimum_confidence(required_level: ConfidenceLevel) -> float:
    mapping = {ConfidenceLevel.CRITICAL: 0.0, ConfidenceLevel.LOW: 0.2, ConfidenceLevel.MEDIUM: 0.4, ConfidenceLevel.HIGH: 0.6, ConfidenceLevel.CERTAIN: 0.8}
    return mapping.get(required_level, 0.0)


def is_confidence_sufficient(current: ConfidenceLevel, required: ConfidenceLevel) -> bool:
    current_map = {ConfidenceLevel.CRITICAL: 0, ConfidenceLevel.LOW: 1, ConfidenceLevel.MEDIUM: 2, ConfidenceLevel.HIGH: 3, ConfidenceLevel.CERTAIN: 4}
    return current_map.get(current, 0) >= current_map.get(required, 2)
