"""
Self-Code Understanding Engine
=============================

A multi-layer code understanding system for self-modifying agents.
This engine provides comprehensive code analysis through 6+ layers:

1. Syntax Understanding (Tree-sitter) - Fast syntax parsing and incremental diffs
2. Symbol Understanding (LSP/SCIP) - Go-to-definition, references, cross-repo
3. Semantic Graph (CPG/Joern) - Control-flow + data-flow + semantic graph
4. Security Analysis (CodeQL/Semgrep) - Vulnerabilities, correctness, policies
5. Runtime Understanding - Actual code behavior through traces
6. Intent Understanding - Why code exists, invariants, historical context

Key Concepts:
- Code Twin: A complete mirror of the codebase with all analysis layers
- Module Card: Summary of each module's purpose, inputs, outputs, criticality
- Function Card: Detailed function analysis with call graph, side effects
- Invariant Card: Extracted invariants from tests, docs, commit messages
- Blast-Radius Report: Impact analysis before making changes
- Confidence Scoring: How confident the engine is about each analysis
- Unknownness Detector: Identifies areas where understanding is uncertain
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .syntax_layer import SyntaxUnderstandingLayer
from .symbol_layer import SymbolUnderstandingLayer
from .semantic_graph_layer import SemanticGraphLayer
from .security_layer import SecurityAnalysisLayer
from .runtime_layer import RuntimeUnderstandingLayer
from .intent_layer import IntentUnderstandingLayer
from .cards import ModuleCard, FunctionCard, InvariantCard, BlastRadiusReport
from .confidence import ConfidenceScorer, UnknownnessDetector


class EngineStatus(Enum):
    """Engine lifecycle states"""
    INITIALIZING = "initializing"
    INGESTING = "ingesting"
    PARSING = "parsing"
    INDEXING = "indexing"
    GRAPH_BUILDING = "graph_building"
    ANALYZING_SECURITY = "analyzing_security"
    EXTRACTING_INTENT = "extracting_intent"
    READY = "ready"
    UPDATING = "updating"
    ERROR = "error"


class ConfidenceLevel(Enum):
    """Confidence levels for engine outputs"""
    CRITICAL = "critical"      # 0-20% - Almost certain to be wrong
    LOW = "low"               # 20-40% - High uncertainty
    MEDIUM = "medium"        # 40-60% - Moderate confidence
    HIGH = "high"            # 60-80% - Good confidence
    CERTAIN = "certain"      # 80-100% - Very high confidence


@dataclass
class CodeTwin:
    """
    A complete "digital twin" of the codebase for the agent.
    
    This is NOT a simple snapshot - it's a living model that includes:
    - Source snapshots
    - Semantic graphs
    - Symbol indexes
    - Runtime profiles
    - Invariant memories
    - Risk maps
    """
    repo_path: Path
    commit_hash: str = ""
    
    # Layer results
    syntax_data: dict = field(default_factory=dict)
    symbol_data: dict = field(default_factory=dict)
    semantic_graph: dict = field(default_factory=dict)
    security_findings: list = field(default_factory=list)
    runtime_traces: dict = field(default_factory=dict)
    intent_data: dict = field(default_factory=dict)
    
    # Confidence scores
    syntax_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    symbol_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    flow_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    intent_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    
    # Unknown areas
    unresolved_symbols: list = field(default_factory=list)
    dynamic_dispatch_uncertainty: list = field(default_factory=list)
    reflection_usage: list = field(default_factory=list)
    generated_code_areas: list = field(default_factory=list)
    framework_magic_routes: list = field(default_factory=list)
    config_driven_behavior: list = field(default_factory=list)
    
    # Output cards
    module_cards: dict[str, ModuleCard] = field(default_factory=dict)
    function_cards: dict[str, FunctionCard] = field(default_factory=dict)
    invariant_cards: list[InvariantCard] = field(default_factory=list)
    
    # Metadata
    last_updated: str = ""
    analysis_version: str = "1.0.0"


@dataclass
class EngineConfig:
    """Configuration for the Self-Code Understanding Engine"""
    # Tree-sitter settings
    tree_sitter_enabled: bool = True
    tree_sitter_languages: list[str] = field(default_factory=lambda: [
        "python", "javascript", "typescript", "go", "rust", "java"
    ])
    
    # LSP settings
    lsp_enabled: bool = True
    lsp_timeout: int = 30
    
    # SCIP settings
    scip_enabled: bool = True
    scip_index_path: Path = field(default_factory=lambda: Path(".scip"))
    
    # CPG/Joern settings
    cpg_enabled: bool = True
    cpg_server_url: str = "http://localhost:9090"
    
    # Security settings
    codeql_enabled: bool = True
    semgrep_enabled: bool = True
    
    # Runtime settings
    runtime_tracking_enabled: bool = True
    max_trace_depth: int = 100
    
    # Intent extraction
    intent_extraction_enabled: bool = True
    
    # Confidence settings
    confidence_threshold: ConfidenceLevel = ConfidenceLevel.MEDIUM
    
    # Performance settings
    incremental_updates: bool = True
    parallel_loading: bool = True
    cache_enabled: bool = True


class SelfCodeUnderstandingEngine:
    """
    No1 World-Level Code Understanding Engine
    
    This engine transforms the codebase from "text that needs to be read"
    into "a living model that understands itself."
    
    Key capabilities:
    - Multi-layer code analysis (syntax, symbol, semantic, security, runtime, intent)
    - Code Twin creation for each candidate edit
    - Confidence scoring for all outputs
    - Unknownness detection to prevent false confidence
    - Blast-radius analysis before changes
    - Edit contracts for safe modifications
    
    Usage:
        engine = SelfCodeUnderstandingEngine(config)
        await engine.ingest_repo("/path/to/repo")
        
        # Get module card
        module_card = engine.get_module_card("src/auth")
        
        # Get blast radius before edit
        blast_radius = await engine.analyze_blast_radius(changes)
        
        # Get confidence score
        confidence = engine.get_confidence("src/auth/login.py")
    """
    
    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()
        self.status = EngineStatus.INITIALIZING
        
        # Initialize layers
        self.syntax_layer = SyntaxUnderstandingLayer(self.config) if self.config.tree_sitter_enabled else None
        self.symbol_layer = SymbolUnderstandingLayer(self.config) if self.config.lsp_enabled else None
        self.semantic_layer = SemanticGraphLayer(self.config) if self.config.cpg_enabled else None
        self.security_layer = SecurityAnalysisLayer(self.config) if self.config.codeql_enabled or self.config.semgrep_enabled else None
        self.runtime_layer = RuntimeUnderstandingLayer(self.config) if self.config.runtime_tracking_enabled else None
        self.intent_layer = IntentUnderstandingLayer(self.config) if self.config.intent_extraction_enabled else None
        
        # Confidence and unknownness
        self.confidence_scorer = ConfidenceScorer(self.config)
        self.unknownness_detector = UnknownnessDetector(self.config)
        
        # Code twin storage
        self.current_twin: CodeTwin | None = None
        
        # Cache
        self._cache: dict[str, Any] = {}
        
        self.status = EngineStatus.READY
    
    async def ingest_repo(self, repo_path: str | Path) -> CodeTwin:
        """
        Ingest and analyze a complete repository.
        
        This is the main entry point for initial analysis.
        It will:
        1. Scan all source files
        2. Parse with Tree-sitter
        3. Build symbol index
        4. Create semantic graph
        5. Run security analysis
        6. Extract runtime traces (if enabled)
        7. Extract intent from docs/tests
        8. Generate all output cards
        9. Calculate confidence scores
        """
        repo_path = Path(repo_path)
        
        self.status = EngineStatus.INGESTING
        
        # Create initial code twin
        twin = CodeTwin(repo_path=repo_path)
        
        # Layer 1: Syntax Understanding
        if self.syntax_layer:
            self.status = EngineStatus.PARSING
            twin.syntax_data = await self.syntax_layer.parse_repo(repo_path)
        
        # Layer 2: Symbol Understanding
        if self.symbol_layer:
            self.status = EngineStatus.INDEXING
            twin.symbol_data = await self.symbol_layer.index_repo(repo_path)
        
        # Layer 3: Semantic Graph
        if self.semantic_layer:
            self.status = EngineStatus.GRAPH_BUILDING
            twin.semantic_graph = await self.semantic_layer.build_graph(repo_path)
        
        # Layer 4: Security Analysis
        if self.security_layer:
            self.status = EngineStatus.ANALYZING_SECURITY
            twin.security_findings = await self.security_layer.analyze(repo_path)
        
        # Layer 5: Runtime Understanding
        if self.runtime_layer:
            twin.runtime_traces = await self.runtime_layer.collect_traces(repo_path)
        
        # Layer 6: Intent Understanding
        if self.intent_layer:
            self.status = EngineStatus.EXTRACTING_INTENT
            twin.intent_data = await self.intent_layer.extract_intent(repo_path)
        
        # Generate output cards
        await self._generate_cards(twin)
        
        # Calculate confidence scores
        twin.syntax_confidence = self.confidence_scorer.calculate_syntax_confidence(twin)
        twin.symbol_confidence = self.confidence_scorer.calculate_symbol_confidence(twin)
        twin.flow_confidence = self.confidence_scorer.calculate_flow_confidence(twin)
        twin.intent_confidence = self.confidence_scorer.calculate_intent_confidence(twin)
        
        # Detect unknown areas
        twin.unresolved_symbols = self.unknownness_detector.find_unresolved_symbols(twin)
        twin.dynamic_dispatch_uncertainty = self.unknownness_detector.find_dynamic_dispatch(twin)
        twin.reflection_usage = self.unknownness_detector.find_reflection_usage(twin)
        
        self.current_twin = twin
        self.status = EngineStatus.READY
        
        return twin
    
    async def update_for_candidate(self, changed_files: list[str]) -> CodeTwin:
        """
        Update the code twin for a specific candidate edit.
        
        This performs incremental updates - only re-analyzing what's changed.
        This is critical for performance in self-modification loops.
        """
        if not self.current_twin:
            raise RuntimeError("No code twin available. Call ingest_repo first.")
        
        self.status = EngineStatus.UPDATING
        
        twin = self.current_twin
        
        if self.config.incremental_updates:
            # Incremental update - only analyze changed files
            if self.syntax_layer:
                twin.syntax_data = await self.syntax_layer.update_incremental(changed_files)
            if self.symbol_layer:
                twin.symbol_data = await self.symbol_layer.update_delta(changed_files)
            if self.semantic_layer:
                twin.semantic_graph = await self.semantic_layer.update_graph_delta(changed_files)
        else:
            # Full re-analysis
            return await self.ingest_repo(twin.repo_path)
        
        # Re-calculate confidence after changes
        twin.syntax_confidence = self.confidence_scorer.calculate_syntax_confidence(twin)
        twin.symbol_confidence = self.confidence_scorer.calculate_symbol_confidence(twin)
        twin.flow_confidence = self.confidence_scorer.calculate_flow_confidence(twin)
        
        # Re-detect unknowns
        twin.unresolved_symbols = self.unknownness_detector.find_unresolved_symbols(twin)
        
        self.status = EngineStatus.READY
        return twin
    
    async def analyze_blast_radius(self, proposed_changes: dict) -> BlastRadiusReport:
        """
        Analyze the blast radius of proposed changes BEFORE making them.
        
        This is critical for safe self-modification. It tells the agent:
        - Which symbols will be affected
        - Which modules might break
        - Which tests must run
        - Which runtime paths need replay
        - What could go wrong
        """
        if not self.current_twin:
            raise RuntimeError("No code twin available. Call ingest_repo first.")
        
        twin = self.current_twin
        
        # Determine affected symbols
        affected_symbols = self._get_affected_symbols(proposed_changes)
        
        # Determine affected modules
        affected_modules = self._get_affected_modules(affected_symbols, twin)
        
        # Determine required tests
        required_tests = self._get_required_tests(affected_modules, twin)
        
        # Determine risky areas
        risky_areas = self._find_risky_areas(affected_modules, twin)
        
        # Check for red zones
        red_zones = self._check_red_zones(affected_modules)
        
        return BlastRadiusReport(
            affected_symbols=list(affected_symbols),
            affected_modules=list(affected_modules),
            required_tests=required_tests,
            risky_areas=risky_areas,
            red_zones=red_zones,
            confidence=self.confidence_scorer.calculate_blast_radius_confidence(
                affected_modules, twin
            )
        )
    
    def get_module_card(self, module_path: str) -> ModuleCard | None:
        """Get the module card for a specific module."""
        if not self.current_twin:
            return None
        return self.current_twin.module_cards.get(module_path)
    
    def get_function_card(self, function_path: str) -> FunctionCard | None:
        """Get the function card for a specific function."""
        if not self.current_twin:
            return None
        return self.current_twin.function_cards.get(function_path)
    
    def get_confidence(self, file_path: str) -> dict[str, ConfidenceLevel]:
        """Get confidence scores for a specific file."""
        if not self.current_twin:
            return {}
        
        return {
            "syntax": self.current_twin.syntax_confidence,
            "symbol": self.current_twin.symbol_confidence,
            "flow": self.current_twin.flow_confidence,
            "intent": self.current_twin.intent_confidence,
        }
    
    def get_unknown_areas(self) -> dict[str, list]:
        """Get all detected unknown areas in the codebase."""
        if not self.current_twin:
            return {}
        
        return {
            "unresolved_symbols": self.current_twin.unresolved_symbols,
            "dynamic_dispatch": self.current_twin.dynamic_dispatch_uncertainty,
            "reflection": self.current_twin.reflection_usage,
            "generated_code": self.current_twin.generated_code_areas,
            "framework_magic": self.current_twin.framework_magic_routes,
            "config_driven": self.current_twin.config_driven_behavior,
        }
    
    def get_edit_contract(self, proposed_changes: dict) -> dict:
        """
        Generate an edit contract for proposed changes.
        
        This tells the candidate:
        - What files/symbols will be touched
        - What tests are relevant
        - What scans are required
        - What zones are forbidden
        - What migrations might be needed
        """
        blast_radius = asyncio.run(self.analyze_blast_radius(proposed_changes))
        
        return {
            "touched_files": list(blast_radius.affected_modules),
            "relevant_symbols": blast_radius.affected_symbols,
            "relevant_tests": blast_radius.required_tests,
            "required_scans": self._determine_required_scans(blast_radius),
            "forbidden_zones": blast_radius.red_zones,
            "migration_needed": self._check_migration_needed(proposed_changes),
            "rollback_points": self._identify_rollback_points(proposed_changes),
            "expected_metrics": self._define_expected_metrics(proposed_changes),
        }
    
    # Internal helper methods
    async def _generate_cards(self, twin: CodeTwin):
        """Generate all output cards from the analysis data."""
        # Generate module cards
        for module_path in twin.syntax_data.get("modules", {}):
            card = self._create_module_card(module_path, twin)
            twin.module_cards[module_path] = card
        
        # Generate function cards
        for func_path in twin.syntax_data.get("functions", {}):
            card = self._create_function_card(func_path, twin)
            twin.function_cards[func_path] = card
        
        # Generate invariant cards
        twin.invariant_cards = self._extract_invariants(twin)
    
    def _create_module_card(self, module_path: str, twin: CodeTwin) -> ModuleCard:
        """Create a module card from analysis data."""
        symbol_data = twin.symbol_data.get(module_path, {})
        semantic = twin.semantic_graph.get(module_path, {})
        
        return ModuleCard(
            module_path=module_path,
            purpose=semantic.get("purpose", "Unknown"),
            inputs=semantic.get("inputs", []),
            outputs=semantic.get("outputs", []),
            external_deps=symbol_data.get("imports", []),
            criticality=semantic.get("criticality", "medium"),
            owner_lineage=semantic.get("owners", []),
            tests=semantic.get("tests", []),
            change_risk=self._calculate_change_risk(module_path, twin),
            edit_history=semantic.get("edit_history", []),
        )
    
    def _create_function_card(self, func_path: str, twin: CodeTwin) -> FunctionCard:
        """Create a function card from analysis data."""
        semantic = twin.semantic_graph.get(func_path, {})
        symbol = twin.symbol_data.get(func_path, {})
        
        return FunctionCard(
            function_path=func_path,
            summary=semantic.get("summary", ""),
            callers=semantic.get("callers", []),
            callees=semantic.get("callees", []),
            side_effects=semantic.get("side_effects", []),
            io_usage=semantic.get("io_usage", {}),
            exceptions=semantic.get("exceptions", []),
            taint_relevance=semantic.get("taint_relevance", False),
            runtime_frequency=semantic.get("runtime_frequency", "unknown"),
        )
    
    def _extract_invariants(self, twin: CodeTwin) -> list[InvariantCard]:
        """Extract invariants from various sources."""
        invariants = []
        
        # From tests
        for test_data in twin.intent_data.get("tests", []):
            invariants.append(InvariantCard(
                invariant_text=test_data.get("assertion", ""),
                source_type="test",
                source_location=test_data.get("location", ""),
                confidence=ConfidenceLevel.HIGH,
                related_files=test_data.get("covers", []),
            ))
        
        # From docs
        for doc_data in twin.intent_data.get("docs", []):
            invariants.append(InvariantCard(
                invariant_text=doc_data.get("invariant", ""),
                source_type="documentation",
                source_location=doc_data.get("location", ""),
                confidence=ConfidenceLevel.MEDIUM,
                related_files=doc_data.get("references", []),
            ))
        
        return invariants
    
    def _get_affected_symbols(self, changes: dict) -> set:
        """Determine which symbols are affected by changes."""
        affected = set()
        
        for file_path in changes.get("files", []):
            if self.current_twin:
                # Find symbols defined in this file
                for func_card in self.current_twin.function_cards.values():
                    if file_path in func_card.function_path:
                        affected.add(func_card.function_path)
                        affected.update(func_card.callers)
                        affected.update(func_card.callees)
        
        return affected
    
    def _get_affected_modules(self, symbols: set, twin: CodeTwin) -> set:
        """Determine which modules are affected by symbol changes."""
        modules = set()
        
        for symbol in symbols:
            # Extract module from symbol path
            parts = symbol.split("/")
            if len(parts) > 1:
                modules.add("/".join(parts[:-1]))
        
        return modules
    
    def _get_required_tests(self, modules: set, twin: CodeTwin) -> list[str]:
        """Determine which tests must run for affected modules."""
        tests = []
        
        for module in modules:
            card = twin.module_cards.get(module)
            if card:
                tests.extend(card.tests)
        
        return list(set(tests))
    
    def _find_risky_areas(self, modules: set, twin: CodeTwin) -> list[dict]:
        """Identify risky areas in affected modules."""
        risky = []
        
        for module in modules:
            card = twin.module_cards.get(module)
            if card and card.criticality in ["high", "critical"]:
                risky.append({
                    "module": module,
                    "reason": f"Criticality: {card.criticality}",
                    "risk_factors": self._analyze_risk_factors(card, twin),
                })
        
        return risky
    
    def _check_red_zones(self, modules: set) -> list[str]:
        """Check if any affected modules are in red zones."""
        red_zones = ["auth", "billing", "deployment", "secret", "core"]
        
        return [m for m in modules if any(rz in m.lower() for rz in red_zones)]
    
    def _calculate_change_risk(self, module_path: str, twin: CodeTwin) -> str:
        """Calculate the risk level for changing a module."""
        card = twin.module_cards.get(module_path)
        
        if not card:
            return "unknown"
        
        risk_score = 0
        
        # Higher criticality = higher risk
        criticality_map = {"low": 1, "medium": 2, "high": 3, "critical": 5}
        risk_score += criticality_map.get(card.criticality, 2)
        
        # More dependencies = higher risk
        risk_score += len(card.external_deps) // 5
        
        # Recent changes = higher risk
        if card.edit_history:
            risk_score += len(card.edit_history) // 3
        
        if risk_score >= 8:
            return "critical"
        elif risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"
    
    def _analyze_risk_factors(self, card: ModuleCard, twin: CodeTwin) -> list[str]:
        """Analyze specific risk factors for a module."""
        factors = []
        
        if card.criticality in ["high", "critical"]:
            factors.append(f"High criticality: {card.criticality}")
        
        if len(card.external_deps) > 10:
            factors.append(f"Many external dependencies: {len(card.external_deps)}")
        
        if card.change_risk in ["high", "critical"]:
            factors.append(f"Historical change risk: {card.change_risk}")
        
        return factors
    
    def _determine_required_scans(self, blast_radius: BlastRadiusReport) -> list[str]:
        """Determine which security scans are required."""
        scans = ["syntax"]
        
        if blast_radius.red_zones:
            scans.extend(["codeql", "semgrep"])
        
        if blast_radius.risky_areas:
            scans.append("codeql_deep")
        
        return scans
    
    def _check_migration_needed(self, changes: dict) -> bool:
        """Check if database/migrations are needed."""
        # Check for model changes
        for file_path in changes.get("files", []):
            if "model" in file_path.lower() or "migration" in file_path.lower():
                return True
        return False
    
    def _identify_rollback_points(self, changes: dict) -> list[dict]:
        """Identify safe rollback points."""
        return [
            {"type": "git", "location": "last commit"},
            {"type": "snapshot", "location": "code twin"},
        ]
    
    def _define_expected_metrics(self, changes: dict) -> dict:
        """Define expected metrics after the change."""
        return {
            "test_coverage_impact": "neutral",
            "performance_impact": "neutral",
            "security_impact": "neutral",
        }
