"""
Output Cards
============

This module provides the structured output types that the engine returns:
- ModuleCard: Summary of a module
- FunctionCard: Detailed function analysis
- InvariantCard: Extracted invariant information
- BlastRadiusReport: Impact analysis for changes
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleCard:
    """
    Module Card - Summary of a module's purpose and characteristics
    
    Provides a quick overview of what a module does, its dependencies,
    criticality, and change risk.
    """
    module_path: str
    purpose: str
    
    # Dependencies
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    external_deps: list[str] = field(default_factory=list)
    
    # Analysis
    criticality: str = "medium"  # low, medium, high, critical
    owner_lineage: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    change_risk: str = "medium"  # low, medium, high, critical
    
    # History
    edit_history: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "module_path": self.module_path,
            "purpose": self.purpose,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "external_deps": self.external_deps,
            "criticality": self.criticality,
            "owner_lineage": self.owner_lineage,
            "tests": self.tests,
            "change_risk": self.change_risk,
            "edit_history": self.edit_history,
        }


@dataclass
class FunctionCard:
    """
    Function Card - Detailed analysis of a function
    
    Provides comprehensive information about a function including
    its call graph, side effects, I/O usage, and runtime characteristics.
    """
    function_path: str
    summary: str
    
    # Call graph
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)
    
    # Effects
    side_effects: list[str] = field(default_factory=list)
    
    # I/O
    io_usage: dict = field(default_factory=dict)  # network, filesystem, database
    
    # Error handling
    exceptions: list[str] = field(default_factory=list)
    
    # Security
    taint_relevance: bool = False
    
    # Runtime
    runtime_frequency: str = "unknown"  # hot, warm, cold, unknown
    
    def to_dict(self) -> dict:
        return {
            "function_path": self.function_path,
            "summary": self.summary,
            "callers": self.callers,
            "callees": self.callees,
            "side_effects": self.side_effects,
            "io_usage": self.io_usage,
            "exceptions": self.exceptions,
            "taint_relevance": self.taint_relevance,
            "runtime_frequency": self.runtime_frequency,
        }


@dataclass
class InvariantCard:
    """
    Invariant Card - Extracted invariant information
    
    Represents a behavioral guarantee or constraint extracted from
    tests, docs, or code.
    """
    invariant_text: str
    source_type: str  # test, documentation, code_comment
    
    # Source location
    source_location: str
    
    # Confidence
    confidence: Any = None  # ConfidenceLevel enum
    
    # Related code
    related_files: list[str] = field(default_factory=list)
    
    # Properties
    is_historical: bool = False
    is_debatable: bool = False
    edge_cases: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "invariant_text": self.invariant_text,
            "source_type": self.source_type,
            "source_location": self.source_location,
            "confidence": str(self.confidence) if self.confidence else None,
            "related_files": self.related_files,
            "is_historical": self.is_historical,
            "is_debatable": self.is_debatable,
            "edge_cases": self.edge_cases,
        }


@dataclass
class BlastRadiusReport:
    """
    Blast Radius Report - Impact analysis for proposed changes
    
    Analyzes what would be affected if certain changes are made,
    including affected modules, required tests, and risk areas.
    """
    affected_symbols: list[str] = field(default_factory=list)
    affected_modules: list[str] = field(default_factory=list)
    
    # Testing
    required_tests: list[str] = field(default_factory=list)
    
    # Risk analysis
    risky_areas: list[dict] = field(default_factory=list)
    red_zones: list[str] = field(default_factory=list)  # auth, billing, etc.
    
    # Confidence
    confidence: Any = None  # ConfidenceLevel
    
    # Additional info
    suggestions: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "affected_symbols": self.affected_symbols,
            "affected_modules": self.affected_modules,
            "required_tests": self.required_tests,
            "risky_areas": self.risky_areas,
            "red_zones": self.red_zones,
            "confidence": str(self.confidence) if self.confidence else None,
            "suggestions": self.suggestions,
        }
    
    def is_safe(self) -> bool:
        """Check if the change appears safe"""
        return (
            len(self.red_zones) == 0 and
            len([r for r in self.risky_areas if r.get("risk_factors")] ) == 0
        )
    
    def requires_manual_review(self) -> bool:
        """Check if manual review is required"""
        return len(self.red_zones) > 0


@dataclass
class CodeTwin:
    """
    Code Twin - Complete living model of the codebase
    
    This is the main output of the engine - a complete digital twin
    that includes all analysis layers.
    """
    repo_path: str
    commit_hash: str = ""
    
    # Analysis data
    syntax_data: dict = field(default_factory=dict)
    symbol_data: dict = field(default_factory=dict)
    semantic_graph: dict = field(default_factory=dict)
    security_findings: list = field(default_factory=list)
    runtime_traces: dict = field(default_factory=dict)
    intent_data: dict = field(default_factory=dict)
    
    # Confidence scores
    syntax_confidence: Any = None
    symbol_confidence: Any = None
    flow_confidence: Any = None
    intent_confidence: Any = None
    
    # Unknown areas
    unresolved_symbols: list = field(default_factory=list)
    dynamic_dispatch_uncertainty: list = field(default_factory=list)
    reflection_usage: list = field(default_factory=list)
    generated_code_areas: list = field(default_factory=list)
    framework_magic_routes: list = field(default_factory=list)
    config_driven_behavior: list = field(default_factory=list)
    
    # Output cards
    module_cards: dict = field(default_factory=dict)
    function_cards: dict = field(default_factory=dict)
    invariant_cards: list = field(default_factory=list)
    
    # Metadata
    last_updated: str = ""
    analysis_version: str = "1.0.0"
    
    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "commit_hash": self.commit_hash,
            "syntax_confidence": str(self.syntax_confidence) if self.syntax_confidence else None,
            "symbol_confidence": str(self.symbol_confidence) if self.symbol_confidence else None,
            "flow_confidence": str(self.flow_confidence) if self.flow_confidence else None,
            "intent_confidence": str(self.intent_confidence) if self.intent_confidence else None,
            "unresolved_symbols": self.unresolved_symbols,
            "unknown_areas_count": (
                len(self.unresolved_symbols) +
                len(self.dynamic_dispatch_uncertainty) +
                len(self.reflection_usage)
            ),
            "total_modules": len(self.module_cards),
            "total_functions": len(self.function_cards),
            "total_invariants": len(self.invariant_cards),
            "total_security_findings": len(self.security_findings),
            "last_updated": self.last_updated,
            "analysis_version": self.analysis_version,
        }
