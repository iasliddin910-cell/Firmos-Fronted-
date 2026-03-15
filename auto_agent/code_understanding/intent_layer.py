"""
Intent Understanding Layer
========================

This layer extracts the "why" behind code - understanding purpose, invariants,
and historical context that static analysis cannot provide.

Key capabilities:
- Extract invariants from tests, docs, commits
- Understand why code was written
- Distinguish intentional behavior from bugs
- Track architectural decisions (ADR)
- Identify historical baggage

This is often the most overlooked layer but critical for No1-level understanding.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class IntentSource(Enum):
    """Sources of intent information"""
    TEST_ASSERTION = "test_assertion"
    DOCSTRING = "docstring"
    README = "readme"
    ADR = "adr"
    COMMIT_MESSAGE = "commit_message"
    PR_NOTE = "pr_note"
    CODE_COMMENT = "code_comment"
    FUNCTION_NAME = "function_name"
    VARIABLE_NAME = "variable_name"
    CONFIG = "config"


class InvariantType(Enum):
    """Types of invariants"""
    CORRECTNESS = "correctness"
    BUSINESS_RULE = "business_rule"
    SECURITY = "security"
    PERFORMANCE = "performance"
    API_CONTRACT = "api_contract"
    DATA_INTEGRITY = "data_integrity"
    ERROR_HANDLING = "error_handling"
    TIMING = "timing"
    STATE_MACHINE = "state_machine"


@dataclass
class Invariant:
    """Represents an invariant extracted from code"""
    id: str
    text: str
    invariant_type: InvariantType
    
    # Source
    source_type: IntentSource
    source_file: str
    source_line: int
    
    # Confidence
    confidence: float = 0.5  # 0.0-1.0
    
    # Related
    related_functions: list[str] = field(default_factory=list)
    related_tests: list[str] = field(default_factory=list)
    
    # Properties
    is_historical: bool = False  # Legacy code, may be outdated
    is_debatable: bool = False   # May not be universally true
    edge_cases: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "text": self.text,
            "type": self.invariant_type.value,
            "source_type": self.source_type.value,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "confidence": self.confidence,
            "related_functions": self.related_functions,
            "related_tests": self.related_tests,
            "is_historical": self.is_historical,
            "is_debatable": self.is_debatable,
            "edge_cases": self.edge_cases,
        }


@dataclass
class ArchitecturalDecision:
    """Represents an architectural decision"""
    id: str
    title: str
    status: str  # proposed, accepted, deprecated, superseded
    
    # Context
    context: str
    decision: str
    consequences: str
    
    # Metadata
    date: str
    author: str = ""
    pr_number: str = ""
    
    # Related code
    affected_files: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "consequences": self.consequences,
            "date": self.date,
            "author": self.author,
            "pr_number": self.pr_number,
            "affected_files": self.affected_files,
        }


@dataclass
class IntentSummary:
    """Summary of intent for a module or function"""
    purpose: str  # What this code is trying to achieve
    
    # Invariants
    invariants: list[Invariant] = field(default_factory=list)
    
    # Decisions
    architectural_decisions: list[ArchitecturalDecision] = field(default_factory=list)
    
    # Historical context
    history: list[dict] = field(default_factory=list)
    
    # Caveats
    known_limitations: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    
    # Quality
    is_well_documented: bool = False
    has_clear_invariants: bool = False


class IntentUnderstandingLayer:
    """
    Intent Understanding Layer
    
    This layer extracts the "why" behind code:
    - Why was this function written?
    - What invariants must hold?
    - What is intentional vs accidental behavior?
    - What architectural decisions were made?
    - What is historical baggage?
    
    Key sources:
    - Test assertions (what behavior is tested)
    - Docstrings (what the author documented)
    - README/ADR (architectural context)
    - Commit messages (historical context)
    - Function/variable names (intent signals)
    """
    
    def __init__(self, config: Any):
        self.config = config
        
        # Extracted data
        self.invariants: list[Invariant] = []
        self.decisions: list[ArchitecturalDecision] = []
        self.intent_summaries: dict[str, IntentSummary] = {}
        
        # Patterns for extraction
        self._load_extraction_patterns()
    
    def _load_extraction_patterns(self):
        """Load patterns for extracting intent"""
        
        # Test assertion patterns
        self.test_patterns = [
            # Correctness assertions
            (r"assert.*==\s*(\w+)", InvariantType.CORRECTNESS),
            (r"assert.*!=\s*(\w+)", InvariantType.CORRECTNESS),
            (r"assert.*\.startswith\(", InvariantType.CORRECTNESS),
            (r"assert.*\.endswith\(", InvariantType.CORRECTNESS),
            (r"assert.*\.contains\(", InvariantType.CORRECTNESS),
            (r"assert.*is not None", InvariantType.CORRECTNESS),
            (r"assert.*isinstance\(", InvariantType.CORRECTNESS),
            
            # Business rules
            (r"assert.*status.*==", InvariantType.BUSINESS_RULE),
            (r"assert.*state.*==", InvariantType.BUSINESS_RULE),
            (r"assert.*balance.*>=", InvariantType.BUSINESS_RULE),
            
            # Security
            (r"assert.*auth", InvariantType.SECURITY),
            (r"assert.*permission", InvariantType.SECURITY),
            (r"assert.*role", InvariantType.SECURITY),
            
            # Performance
            (r"assert.*time", InvariantType.PERFORMANCE),
            (r"assert.*duration", InvariantType.PERFORMANCE),
            (r"assert.*latency", InvariantType.PERFORMANCE),
            
            # Error handling
            (r"assert.*raises\(", InvariantType.ERROR_HANDLING),
            (r"assert.*exception", InvariantType.ERROR_HANDLING),
        ]
        
        # Function name intent patterns
        self.function_intent_patterns = [
            # Validation
            (r"^validate_", "Validates input data"),
            (r"^check_", "Checks conditions"),
            (r"^verify_", "Verifies correctness"),
            (r"^ensure_", "Ensures invariants"),
            
            # Transformation
            (r"^transform_", "Transforms data"),
            (r"^convert_", "Converts between formats"),
            (r"^parse_", "Parses input"),
            (r"^serialize_", "Serializes data"),
            
            # Actions
            (r"^create_", "Creates a new resource"),
            (r"^update_", "Updates existing resource"),
            (r"^delete_", "Deletes a resource"),
            (r"^fetch_", "Fetches data"),
            
            # Safety
            (r"^safe_", "Safe version with guards"),
            (r"^try_", "Attempt with error handling"),
            (r"^maybe_", "Optional result handling"),
        ]
    
    async def extract_intent(self, repo_path: Path) -> dict[str, Any]:
        """
        Extract intent from the entire repository.
        
        This analyzes:
        1. Test files for invariants
        2. Documentation for purpose
        3. ADRs for decisions
        4. Commit history for context
        5. Code for implicit intent
        """
        intent_data = {
            "invariants": [],
            "decisions": [],
            "summaries": {},
        }
        
        # Extract from tests
        test_invariants = await self._extract_from_tests(repo_path)
        intent_data["invariants"] = [i.to_dict() for i in test_invariants]
        self.invariants.extend(test_invariants)
        
        # Extract from docs
        doc_invariants = await self._extract_from_docs(repo_path)
        intent_data["invariants"].extend([i.to_dict() for i in doc_invariants])
        self.invariants.extend(doc_invariants)
        
        # Extract from ADRs
        decisions = await self._extract_adrs(repo_path)
        intent_data["decisions"] = [d.to_dict() for d in decisions]
        self.decisions.extend(decisions)
        
        # Extract from code (function names, comments)
        code_intent = await self._extract_from_code(repo_path)
        intent_data["invariants"].extend([i.to_dict() for i in code_intent])
        self.invariants.extend(code_intent)
        
        # Build summaries
        summaries = self._build_intent_summaries(repo_path)
        intent_data["summaries"] = {
            k: {
                "purpose": v.purpose,
                "invariant_count": len(v.invariants),
                "is_well_documented": v.is_well_documented,
            }
            for k, v in summaries.items()
        }
        self.intent_summaries = summaries
        
        return intent_data
    
    async def _extract_from_tests(self, repo_path: Path) -> list[Invariant]:
        """Extract invariants from test files"""
        invariants = []
        invariant_id = 0
        
        # Find test files
        test_files = []
        
        for root, dirs, filenames in repo_path.walk():
            # Look for test directories
            if "test" in root.lower():
                for filename in filenames:
                    if filename.startswith("test_") or filename.endswith("_test.py"):
                        test_files.append(Path(root) / filename)
        
        for test_file in test_files:
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")
                
                # Extract from test function names
                for line_num, line in enumerate(lines, 1):
                    # Test function name
                    if line.strip().startswith("def test_"):
                        test_name = line.split("def ")[1].split("(")[0].strip()
                        
                        # Extract invariants from test name
                        extracted = self._extract_from_test_name(test_name, test_file, line_num)
                        invariants.extend(extracted)
                    
                    # Test assertions
                    for pattern, inv_type in self.test_patterns:
                        import re
                        if re.search(pattern, line):
                            invariant_id += 1
                            
                            # Extract code snippet
                            snippet = line.strip()
                            
                            invariants.append(Invariant(
                                id=f"test-{invariant_id}",
                                text=f"Test asserts: {snippet}",
                                invariant_type=inv_type,
                                source_type=IntentSource.TEST_ASSERTION,
                                source_file=str(test_file),
                                source_line=line_num,
                                confidence=0.9,  # Tests have high confidence
                                related_tests=[test_file.name],
                            ))
            
            except Exception:
                pass
        
        return invariants
    
    def _extract_from_test_name(self, test_name: str, 
                              file_path: Path, 
                              line: int) -> list[Invariant]:
        """Extract invariants from test function names"""
        invariants = []
        
        # Parse test name for intent
        # Example: test_user_cannot_login_with_wrong_password
        
        # Split by underscores
        parts = test_name.replace("test_", "").split("_")
        
        # This is a simplified version - in production would use NLP
        # For now, create basic invariants
        
        return invariants
    
    async def _extract_from_docs(self, repo_path: Path) -> list[Invariant]:
        """Extract invariants from documentation"""
        invariants = []
        invariant_id = 0
        
        # Find documentation files
        doc_files = []
        
        for root, dirs, filenames in repo_path.walk():
            for filename in filenames:
                if filename.lower() in ("readme.md", "readme.rst", "readme.txt", 
                                      "doc.md", "documentation.md"):
                    doc_files.append(Path(root) / filename)
        
        for doc_file in doc_files:
            try:
                with open(doc_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")
                
                # Extract from code blocks
                in_code_block = False
                code_lines = []
                
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith("```"):
                        if in_code_block:
                            # End of code block - analyze
                            code_content = "\n".join(code_lines)
                            extracted = self._extract_from_code_content(code_content, doc_file, line_num)
                            invariants.extend(extracted)
                            code_lines = []
                        in_code_block = not in_code_block
                    elif in_code_block:
                        code_lines.append(line)
                
                # Extract requirements/guarantees from text
                for line_num, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    
                    if any(kw in line_lower for kw in ["always", "never", "must", "will", "guarantee"]):
                        invariant_id += 1
                        
                        invariants.append(Invariant(
                            id=f"doc-{invariant_id}",
                            text=line.strip(),
                            invariant_type=InvariantType.CORRECTNESS,
                            source_type=IntentSource.DOCSTRING,
                            source_file=str(doc_file),
                            source_line=line_num,
                            confidence=0.7,
                        ))
            
            except Exception:
                pass
        
        return invariants
    
    async def _extract_adrs(self, repo_path: Path) -> list[ArchitecturalDecision]:
        """Extract architectural decisions from ADRs"""
        decisions = []
        
        # Find ADR directory
        adr_dir = None
        
        for root, dirs, filenames in repo_path.walk():
            if "adr" in root.lower():
                adr_dir = Path(root)
                break
        
        if not adr_dir:
            # Look for ADR files in docs
            for root, dirs, filenames in repo_path.walk():
                for filename in filenames:
                    if filename.upper().startswith("ADR"):
                        if adr_dir is None:
                            adr_dir = Path(root)
                        break
        
        if not adr_dir:
            return decisions
        
        # Parse ADR files
        for adr_file in adr_dir.glob("*.md"):
            try:
                with open(adr_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Simple ADR parsing
                lines = content.split("\n")
                
                title = ""
                status = "proposed"
                context = ""
                decision = ""
                consequences = ""
                
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith("# "):
                        title = line[2:]
                    elif line.startswith("## Status"):
                        status = line.split(":")[-1].strip().lower()
                    elif line.startswith("## Context"):
                        section = "context"
                    elif line.startswith("## Decision"):
                        section = "decision"
                    elif line.startswith("## Consequences"):
                        section = "consequences"
                    elif line.startswith("## "):
                        section = ""
                    elif section == "context":
                        context += line + " "
                    elif section == "decision":
                        decision += line + " "
                    elif section == "consequences":
                        consequences += line + " "
                
                if title:
                    decisions.append(ArchitecturalDecision(
                        id=adr_file.stem,
                        title=title,
                        status=status,
                        context=context.strip(),
                        decision=decision.strip(),
                        consequences=consequences.strip(),
                        date="",  # Would extract from file
                        affected_files=[],  # Would analyze
                    ))
            
            except Exception:
                pass
        
        return decisions
    
    async def _extract_from_code(self, repo_path: Path) -> list[Invariant]:
        """Extract intent from code (function names, comments)"""
        invariants = []
        invariant_id = 0
        
        # Find source files
        source_files = []
        
        for root, dirs, filenames in repo_path.walk():
            dirs[:] = [d for d in dirs if not d.startswith('.') 
                      and d not in ('test', 'tests', '__pycache__', 'venv')]
            
            for filename in filenames:
                if filename.endswith((".py", ".js", ".ts", ".go", ".rs")):
                    source_files.append(Path(root) / filename)
        
        for source_file in source_files:
            try:
                with open(source_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")
                
                # Extract from function definitions
                for line_num, line in enumerate(lines, 1):
                    # Function definition
                    if "def " in line and ":" in line:
                        func_name = line.split("def ")[1].split("(")[0].strip()
                        
                        # Get intent from function name
                        import re
                        for pattern, intent in self.function_intent_patterns:
                            if re.search(pattern, func_name):
                                invariant_id += 1
                                
                                invariants.append(Invariant(
                                    id=f"code-{invariant_id}",
                                    text=f"Function {func_name}: {intent}",
                                    invariant_type=InvariantType.CORRECTNESS,
                                    source_type=IntentSource.FUNCTION_NAME,
                                    source_file=str(source_file),
                                    source_line=line_num,
                                    confidence=0.6,
                                    related_functions=[func_name],
                                ))
                                break
                    
                    # Comments
                    if line.strip().startswith("# ") or line.strip().startswith("// "):
                        comment = line.strip().lstrip("# ").lstrip("// ")
                        
                        # Look for intent signals
                        if any(kw in comment.lower() for kw in 
                              ["always", "never", "must", "should", "important", "note", "warning"]):
                            invariant_id += 1
                            
                            invariants.append(Invariant(
                                id=f"comment-{invariant_id}",
                                text=comment,
                                invariant_type=InvariantType.CORRECTNESS,
                                source_type=IntentSource.CODE_COMMENT,
                                source_file=str(source_file),
                                source_line=line_num,
                                confidence=0.5,
                            ))
            
            except Exception:
                pass
        
        return invariants
    
    def _extract_from_code_content(self, code: str, 
                                   file_path: Path, 
                                   line_offset: int) -> list[Invariant]:
        """Extract invariants from code snippets in documentation"""
        invariants = []
        
        # Simple extraction - look for patterns in code
        
        return invariants
    
    def _build_intent_summaries(self, repo_path: Path) -> dict[str, IntentSummary]:
        """Build intent summaries for modules"""
        summaries = {}
        
        # Group invariants by module
        module_invariants: dict[str, list[Invariant]] = {}
        
        for invariant in self.invariants:
            # Extract module from file path
            parts = Path(invariant.source_file).parts
            if len(parts) > 1:
                module = str(Path(*parts[:-1]))
                
                if module not in module_invariants:
                    module_invariants[module] = []
                
                module_invariants[module].append(invariant)
        
        # Build summary for each module
        for module, invs in module_invariants.items():
            # Determine purpose (from most common types)
            type_counts = {}
            for inv in invs:
                t = inv.invariant_type.value
                type_counts[t] = type_counts.get(t, 0) + 1
            
            # Most common type is likely the purpose
            purpose_type = max(type_counts, key=type_counts.get) if type_counts else "general"
            
            summary = IntentSummary(
                purpose=f"Module provides {purpose_type} functionality",
                invariants=invs,
                architectural_decisions=[d for d in self.decisions 
                                       if any(f in d.affected_files for f in [module])],
                is_well_documented=len(invs) > 3,
                has_clear_invariants=len(invs) > 0,
            )
            
            summaries[module] = summary
        
        return summaries
    
    def get_invariants_for_function(self, function_path: str) -> list[Invariant]:
        """Get all invariants related to a specific function"""
        related = []
        
        for invariant in self.invariants:
            if function_path in invariant.related_functions:
                related.append(invariant)
            elif function_path in invariant.source_file:
                related.append(invariant)
        
        return related
    
    def get_invariants_for_test(self, test_path: str) -> list[Invariant]:
        """Get all invariants tested by a specific test"""
        return [
            inv for inv in self.invariants 
            if test_path in inv.related_tests
        ]
    
    def get_decisions_for_file(self, file_path: str) -> list[ArchitecturalDecision]:
        """Get architectural decisions related to a file"""
        return [
            dec for dec in self.decisions
            if any(file_path in f for f in dec.affected_files)
        ]
    
    def is_behavior_intentional(self, behavior: str, file_path: str) -> bool:
        """
        Determine if a behavior is intentional (documented/expected)
        vs accidental (bug).
        
        This helps avoid "fixing" intentional behavior.
        """
        # Check if there's an invariant describing this behavior
        for invariant in self.invariants:
            if file_path in invariant.source_file:
                # Check if behavior is mentioned in invariants
                if behavior.lower() in invariant.text.lower():
                    return True
        
        # Check if there's a test for this behavior
        for invariant in self.invariants:
            if behavior.lower() in invariant.text.lower():
                if invariant.source_type == IntentSource.TEST_ASSERTION:
                    return True
        
        return False
    
    def get_intent_confidence(self, file_path: str) -> float:
        """Calculate confidence in our understanding of a file's intent"""
        file_invariants = [
            inv for inv in self.invariants
            if file_path in inv.source_file
        ]
        
        if not file_invariants:
            return 0.1
        
        # Average confidence
        avg_confidence = sum(inv.confidence for inv in file_invariants) / len(file_invariants)
        
        # Boost for having tests
        has_tests = any(
            inv.source_type == IntentSource.TEST_ASSERTION 
            for inv in file_invariants
        )
        
        if has_tests:
            avg_confidence = min(1.0, avg_confidence + 0.2)
        
        return avg_confidence
