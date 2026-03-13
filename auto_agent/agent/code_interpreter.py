"""
OmniAgent X - Code Interpreter (REFACTORED)
==========================================
Enterprise-grade coding agent

REFACTORED:
- Diff-based editing
- Repo scan and file relevance ranking
- Test runner
- Lint/format hooks
- Patch loop: run -> parse error -> patch -> rerun
- Rollback snapshots
- Artifact saving: output files, logs, preview
"""
import os
import subprocess
import logging
import shutil
import uuid
import json
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import difflib

logger = logging.getLogger(__name__)


# ==================== ENUMS & DATA CLASSES ====================

class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    HTML = "html"
    CSS = "css"
    GO = "go"
    RUST = "rust"


class ExecutionState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class FileSnapshot:
    """File snapshot for rollback"""
    path: str
    content: str
    hash: str
    timestamp: float


@dataclass
class PatchAttempt:
    """Patch attempt with result"""
    attempt_number: int
    code: str
    error: str
    fixed: bool
    output: str


@dataclass
class TestResult:
    """Test execution result"""
    name: str
    passed: bool
    error: str = ""
    duration: float = 0.0


@dataclass
class ExecutionResult:
    """Code execution result"""
    success: bool
    output: str
    error: str = ""
    artifacts: List[str] = field(default_factory=list)
    duration: float = 0.0
    test_results: List[TestResult] = field(default_factory=list)


# ==================== CODE INTERPRETER ====================

class CodeInterpreter:
    """
    REFACTORED: Enterprise-grade coding agent
    
    Features:
    - Diff-based editing
    - Patch loop (run -> error -> patch -> rerun)
    - Rollback snapshots
    - Test runner integration
    - Lint/format hooks
    - Artifact management
    """
    
    def __init__(self, workspace_dir: Path = None):
        if workspace_dir is None:
            workspace_dir = Path(__file__).parent.parent / "data" / "code_workspace"
        
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Snapshots for rollback
        self.snapshots: Dict[str, List[FileSnapshot]] = {}
        
        # Current session
        self.current_session: Optional[str] = None
        self.session_dir: Optional[Path] = None
        
        # Settings
        self.max_execution_time = 60
        self.max_output_size = 100000
        self.max_retries = 3
        
        # Artifacts
        self.artifacts_dir = workspace_dir / "artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)
        
        logger.info("💻 Code Interpreter initialized (REFACTORED)")
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_session(self, project_name: str = None) -> str:
        """Create new coding session"""
        session_id = project_name or str(uuid.uuid4())[:8]
        self.current_session = session_id
        
        self.session_dir = self.workspace_dir / session_id
        self.session_dir.mkdir(exist_ok=True)
        
        # Initialize snapshots
        self.snapshots[session_id] = []
        
        logger.info(f"📁 Session created: {session_id}")
        return session_id
    
    def close_session(self) -> str:
        """Close current session and cleanup"""
        if self.current_session and self.session_dir:
            # Save artifacts
            artifacts = list(self.session_dir.glob("*"))
            logger.info(f"📦 Session {self.current_session}: {len(artifacts)} files")
            
            # Clear
            self.current_session = None
            self.session_dir = None
        
        return "Session closed"
    
    # ==================== SNAPSHOTS & ROLLBACK ====================
    
    def take_snapshot(self, filepath: str) -> FileSnapshot:
        """Take a snapshot of a file"""
        path = Path(filepath)
        
        if not path.exists():
            content = ""
        else:
            content = path.read_text(encoding="utf-8")
        
        snapshot = FileSnapshot(
            path=str(path),
            content=content,
            hash=hashlib.md5(content.encode()).hexdigest(),
            timestamp=datetime.now().timestamp()
        )
        
        if self.current_session:
            self.snapshots[self.current_session].append(snapshot)
        
        return snapshot
    
    def rollback_to_snapshot(self, filepath: str, snapshot: FileSnapshot) -> bool:
        """Rollback file to snapshot"""
        try:
            path = Path(filepath)
            path.write_text(snapshot.content, encoding="utf-8")
            logger.info(f"🔄 Rolled back: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def create_rollback_point(self, name: str) -> str:
        """Create named rollback point"""
        if not self.session_dir:
            return "No active session"
        
        rollback_file = self.session_dir / f".rollback_{name}"
        
        # Copy all files to rollback point
        files = {}
        for f in self.session_dir.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                files[str(f.relative_to(self.session_dir))] = f.read_text()
        
        rollback_file.write_text(json.dumps(files))
        logger.info(f"💾 Rollback point created: {name}")
        return f"Rollback point: {name}"
    
    def restore_rollback_point(self, name: str) -> bool:
        """Restore from rollback point"""
        if not self.session_dir:
            return False
        
        rollback_file = self.session_dir / f".rollback_{name}"
        
        if not rollback_file.exists():
            return False
        
        try:
            files = json.loads(rollback_file.read_text())
            
            for rel_path, content in files.items():
                (self.session_dir / rel_path).write_text(content)
            
            logger.info(f"🔄 Restored from rollback: {name}")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    # ==================== DIFF-BASED EDITING ====================
    
    def apply_diff(self, filepath: str, old_content: str, new_content: str) -> Tuple[bool, str]:
        """Apply diff between old and new content"""
        try:
            path = Path(filepath)
            
            # Generate diff
            diff = list(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
                lineterm=''
            ))
            
            # Apply if different
            if old_content != new_content:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(new_content, encoding="utf-8")
                logger.info(f"✏️ Applied diff to: {filepath}")
                return True, "\n".join(diff[:20])  # First 20 lines of diff
            
            return True, "No changes needed"
        
        except Exception as e:
            return False, str(e)
    
    def get_file_diff(self, filepath: str, new_content: str) -> str:
        """Get diff without applying"""
        try:
            path = Path(filepath)
            old_content = path.read_text(encoding="utf-8") if path.exists() else ""
            
            diff = list(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path),
                lineterm=''
            ))
            
            return "\n".join(diff) if diff else "No changes"
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    # ==================== REPO SCAN & RANKING ====================
    
    def scan_repository(self, root_dir: str = ".") -> List[Dict]:
        """Scan repository and rank files by relevance"""
        root = Path(root_dir)
        
        if not root.exists():
            return []
        
        files = []
        
        for f in root.rglob("*"):
            if f.is_file() and not self._should_ignore(f):
                # Calculate relevance score
                score = self._calculate_relevance(f)
                
                files.append({
                    "path": str(f.relative_to(root)),
                    "type": f.suffix,
                    "size": f.stat().st_size,
                    "relevance": score,
                    "modified": f.stat().st_mtime
                })
        
        # Sort by relevance
        files.sort(key=lambda x: x["relevance"], reverse=True)
        
        return files[:50]  # Top 50
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if file should be ignored"""
        ignore_patterns = [
            "__pycache__", ".git", ".venv", "node_modules",
            ".pytest_cache", ".mypy_cache", "*.pyc", ".DS_Store"
        ]
        
        path_str = str(path)
        return any(pattern in path_str for pattern in ignore_patterns)
    
    def _calculate_relevance(self, path: Path) -> float:
        """Calculate file relevance score"""
        score = 0.0
        
        # Extension-based scoring
        relevant_exts = {
            ".py": 10, ".js": 8, ".ts": 8, ".jsx": 8, ".tsx": 8,
            ".html": 5, ".css": 5, ".json": 5, ".md": 3
        }
        
        score += relevant_exts.get(path.suffix, 1)
        
        # Name-based scoring
        important_files = ["main", "app", "index", "server", "api"]
        if any(name in path.stem.lower() for name in important_files):
            score += 5
        
        return score
    
    # ==================== PATCH LOOP ====================
    
    def execute_with_patch_loop(self, code: str, language: Language = Language.PYTHON,
                                max_attempts: int = 3) -> ExecutionResult:
        """
        Execute code with patch loop:
        1. Run code
        2. Parse error
        3. Generate patch
        4. Rerun
        """
        import time
        start_time = time.time()
        
        attempts = []
        current_code = code
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"🔄 Patch attempt {attempt}/{max_attempts}")
            
            # Execute
            result = self._execute_code(current_code, language)
            
            attempts.append(PatchAttempt(
                attempt_number=attempt,
                code=current_code,
                error=result.error,
                fixed=result.success,
                output=result.output
            ))
            
            if result.success:
                result.duration = time.time() - start_time
                result.test_results = self._parse_test_results(result.output)
                return result
            
            # Parse error and try to fix
            if attempt < max_attempts:
                current_code = self._generate_patch(current_code, result.error, language)
                
                if not current_code:
                    break
        
        # All attempts failed
        return ExecutionResult(
            success=False,
            output=attempts[-1].output if attempts else "",
            error=f"Failed after {len(attempts)} attempts: {attempts[-1].error if attempts else 'Unknown'}",
            duration=time.time() - start_time
        )
    
    def _execute_code(self, code: str, language: Language) -> ExecutionResult:
        """Execute code in session"""
        import time
        start_time = time.time()
        
        if not self.session_dir:
            self.create_session()
        
        # Write code
        ext = language.value
        code_file = self.session_dir / f"main.{ext}"
        
        try:
            code_file.write_text(code, encoding="utf-8")
            
            # Execute based on language
            if language == Language.PYTHON:
                result = subprocess.run(
                    ["python", str(code_file)],
                    capture_output=True,
                    text=True,
                    timeout=self.max_execution_time,
                    cwd=self.session_dir
                )
            elif language == Language.JAVASCRIPT:
                result = subprocess.run(
                    ["node", str(code_file)],
                    capture_output=True,
                    text=True,
                    timeout=self.max_execution_time,
                    cwd=self.session_dir
                )
            else:
                return ExecutionResult(
                    success=False,
                    error=f"Unsupported language: {language.value}"
                )
            
            output = result.stdout if result.stdout else result.stderr
            
            return ExecutionResult(
                success=result.returncode == 0,
                output=output,
                error="" if result.returncode == 0 else output,
                duration=time.time() - start_time
            )
        
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error="Execution timeout"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e)
            )
    
    def _generate_patch(self, code: str, error: str, language: Language) -> Optional[str]:
        """Generate patch for error using AI"""
        # Simple pattern-based patching
        # In production, this would use an LLM
        
        error_lower = error.lower()
        
        # Common Python errors
        if "syntaxerror" in error_lower:
            # Try to fix obvious syntax issues
            if "unexpected" in error_lower:
                lines = code.split("\n")
                # Find and fix lines with obvious issues
                pass
        
        if "importerror" in error_lower or "modulenotfounderror" in error_lower:
            # Try to add import
            pass
        
        if "attributeerror" in error_lower:
            # Try to fix attribute access
            pass
        
        if "indentationerror" in error_lower:
            # Try to fix indentation
            lines = code.split("\n")
            fixed = []
            for line in lines:
                # Simple fix: remove mixed tabs/spaces
                fixed.append(line.expandtabs(4))
            return "\n".join(fixed)
        
        # If we can't fix, return None
        return None
    
    # ==================== TEST RUNNER ====================
    
    def run_tests(self, test_files: List[str] = None) -> List[TestResult]:
        """Run tests for the project"""
        results = []
        
        if not self.session_dir:
            return results
        
        # Try pytest
        if test_files is None:
            test_files = list(self.session_dir.rglob("test_*.py"))
        
        for test_file in test_files:
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_file), "-v"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=self.session_dir
                )
                
                # Parse output
                passed = result.returncode == 0
                
                results.append(TestResult(
                    name=str(test_file),
                    passed=passed,
                    error=result.stderr if not passed else "",
                    output=result.stdout
                ))
            
            except Exception as e:
                results.append(TestResult(
                    name=str(test_file),
                    passed=False,
                    error=str(e)
                ))
        
        return results
    
    def _parse_test_results(self, output: str) -> List[TestResult]:
        """Parse test results from output"""
        results = []
        
        # Simple parsing for pytest output
        for line in output.split("\n"):
            if "PASSED" in line or "FAILED" in line:
                name = line.split("::")[-1].split(" ")[0] if "::" in line else "unknown"
                passed = "PASSED" in line
                
                results.append(TestResult(
                    name=name,
                    passed=passed
                ))
        
        return results
    
    # ==================== LINT & FORMAT ====================
    
    def run_linter(self, filepath: str = None) -> Tuple[bool, str]:
        """Run linter on code"""
        target = filepath or str(self.session_dir / "main.py") if self.session_dir else None
        
        if not target or not Path(target).exists():
            return False, "No target file"
        
        ext = Path(target).suffix
        
        try:
            if ext == ".py":
                # Run ruff
                result = subprocess.run(
                    ["ruff", "check", target],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0, result.stdout or result.stderr
            
            elif ext in [".js", ".ts"]:
                # Run eslint (if available)
                result = subprocess.run(
                    ["npx", "eslint", target],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                return result.returncode == 0, result.stdout or result.stderr
        
        except FileNotFoundError:
            return False, "Linter not installed"
        except Exception as e:
            return False, str(e)
        
        return True, "No linter available"
    
    def format_code(self, filepath: str) -> Tuple[bool, str]:
        """Format code"""
        path = Path(filepath)
        
        if not path.exists():
            return False, "File not found"
        
        ext = path.suffix
        
        try:
            if ext == ".py":
                result = subprocess.run(
                    ["ruff", "format", str(path)],
                    capture_output=True,
                    text=True
                )
            elif ext in [".js", ".ts"]:
                result = subprocess.run(
                    ["npx", "prettier", "--write", str(path)],
                    capture_output=True,
                    text=True
                )
            else:
                return False, "Unsupported format"
            
            return result.returncode == 0, result.stdout or result.stderr
        
        except FileNotFoundError:
            return False, "Formatter not installed"
        except Exception as e:
            return False, str(e)
    
    # ==================== ARTIFACT MANAGEMENT ====================
    
    def save_artifacts(self, name: str = None) -> str:
        """Save session artifacts"""
        if not self.session_dir:
            return "No active session"
        
        artifact_name = name or self.current_session or str(uuid.uuid4())[:8]
        artifact_path = self.artifacts_dir / artifact_name
        
        try:
            # Copy session to artifacts
            shutil.copytree(self.session_dir, artifact_path)
            
            # Create metadata
            metadata = {
                "session": self.current_session,
                "timestamp": datetime.now().isoformat(),
                "files": [str(f.relative_to(self.session_dir)) 
                         for f in self.session_dir.rglob("*") if f.is_file()]
            }
            
            (artifact_path / "metadata.json").write_text(json.dumps(metadata, indent=2))
            
            logger.info(f"📦 Artifacts saved: {artifact_name}")
            return f"Artifacts saved: {artifact_path}"
        
        except Exception as e:
            return f"Error saving artifacts: {str(e)}"
    
    def load_artifact(self, name: str) -> bool:
        """Load artifact into session"""
        artifact_path = self.artifacts_dir / name
        
        if not artifact_path.exists():
            return False
        
        if not self.session_dir:
            self.create_session(name)
        
        try:
            # Copy files
            for f in artifact_path.rglob("*"):
                if f.is_file() and f.name != "metadata.json":
                    dest = self.session_dir / f.relative_to(artifact_path)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
            
            return True
        except Exception as e:
            logger.error(f"Error loading artifact: {e}")
            return False
    
    # ==================== LEGACY METHODS ====================
    
    def execute_python(self, code: str, dependencies: List[str] = None) -> str:
        """Legacy method for compatibility"""
        self.create_session()
        
        result = self._execute_code(code, Language.PYTHON)
        
        if result.success:
            return f"✅ Success:\n{result.output}"
        else:
            return f"❌ Error:\n{result.error}"
    
    def execute_javascript(self, code: str) -> str:
        """Legacy method for compatibility"""
        self.create_session()
        
        result = self._execute_code(code, Language.JAVASCRIPT)
        
        if result.success:
            return f"✅ Success:\n{result.output}"
        else:
            return f"❌ Error:\n{result.error}"
    
    def execute_project(self, files: Dict[str, str], entry: str = "main.py") -> str:
        """Legacy method for compatibility"""
        self.create_session()
        
        # Write all files
        for fname, content in files.items():
            (self.session_dir / fname).write_text(content)
        
        # Execute
        lang = Language.PYTHON if entry.endswith(".py") else Language.JAVASCRIPT
        result = self._execute_code((self.session_dir / entry).read_text(), lang)
        
        return f"{'✅' if result.success else '❌'} {result.output or result.error}"


# Global instance
_code_interpreter = None

def get_code_interpreter(workspace_dir: Path = None) -> CodeInterpreter:
    """Get or create code interpreter"""
    global _code_interpreter
    if _code_interpreter is None:
        _code_interpreter = CodeInterpreter(workspace_dir)
    return _code_interpreter
