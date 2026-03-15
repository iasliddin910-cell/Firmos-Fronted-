"""
Self-Code Understanding Engine - Core Module

This is the "brain" of the self-modifying agent. It provides multi-layer
code understanding through:
- Tree-sitter for syntax understanding
- LSP/SCIP for symbol understanding
- CPG for semantic graph
- CodeQL/Semgrep for security analysis
- Runtime traces for practical understanding

This is NOT a simple "repo summary" - it's a living digital twin of the codebase.
"""

from .syntax_layer import SyntaxUnderstandingLayer
from .symbol_layer import SymbolUnderstandingLayer
from .semantic_graph_layer import SemanticGraphLayer
from .security_layer import SecurityAnalysisLayer
from .runtime_layer import RuntimeUnderstandingLayer
from .intent_layer import IntentUnderstandingLayer
from .cards import ModuleCard, FunctionCard, InvariantCard, BlastRadiusReport, CodeTwin
from .confidence import ConfidenceScorer, UnknownnessDetector, ConfidenceLevel
from .engine import SelfCodeUnderstandingEngine, EngineConfig, EngineStatus

__version__ = "1.0.0"
__all__ = [
    # Main engine
    "SelfCodeUnderstandingEngine",
    "EngineConfig",
    "EngineStatus",
    # Layers
    "SyntaxUnderstandingLayer",
    "SymbolUnderstandingLayer", 
    "SemanticGraphLayer",
    "SecurityAnalysisLayer",
    "RuntimeUnderstandingLayer",
    "IntentUnderstandingLayer",
    # Output cards
    "ModuleCard",
    "FunctionCard", 
    "InvariantCard",
    "BlastRadiusReport",
    "CodeTwin",
    # Confidence
    "ConfidenceScorer",
    "UnknownnessDetector",
    "ConfidenceLevel",
]
