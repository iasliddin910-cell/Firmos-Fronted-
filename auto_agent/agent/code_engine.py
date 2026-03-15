"""
OmniAgent X - Enhanced Code Engine (Devin-Level)
"""
import os
import ast
import logging
import subprocess
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class CodeEntity:
    name: str
    type: str
    file: str
    line_start: int
    line_end: int

class ASTParser:
    def __init__(self):
        self.entities: Dict[str, List[CodeEntity]] = defaultdict(list)
    
    def parse_file(self, filepath: str) -> List[CodeEntity]:
        entities = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    entities.append(CodeEntity(name=node.name, type="function", file=filepath,
                        line_start=node.lineno, line_end=node.end_lineno or node.lineno))
                elif isinstance(node, ast.ClassDef):
                    entities.append(CodeEntity(name=node.name, type="class", file=filepath,
                        line_start=node.lineno, line_end=node.end_lineno or node.lineno))
            self.entities[filepath] = entities
        except Exception as e: logger.warning(f"Code parsing error: {e}")
        return entities

class TestOrchestrator:
    def discover_tests(self, root_dir: str) -> List[str]:
        return [str(f) for f in Path(root_dir).rglob("test_*.py")]
    
    def run_test(self, test_file: str) -> Dict:
        try:
            result = subprocess.run(["python", "-m", "pytest", test_file, "-v"],
                capture_output=True, text=True, timeout=120)
            return {"file": test_file, "passed": result.returncode == 0}
        except Exception as e: logger.warning(f"Test run error: {e}"); return {"file": test_file, "passed": False, "error": str(e)}
    
    def run_all_tests(self, root_dir: str) -> Dict:
        test_files = self.discover_tests(root_dir)
        results = [self.run_test(f) for f in test_files]
        return {"total": len(test_files), "passed": sum(1 for r in results if r["passed"]), "results": results}

class CodeEngine:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.ast_parser = ASTParser()
        self.test_orchestrator = TestOrchestrator()
        logger.info("Code Engine Devin-Level initialized")
    
    def run_tests(self) -> Dict:
        return self.test_orchestrator.run_all_tests(str(self.workspace_dir))

def create_code_engine(workspace_dir: str) -> CodeEngine:
    return CodeEngine(workspace_dir)
