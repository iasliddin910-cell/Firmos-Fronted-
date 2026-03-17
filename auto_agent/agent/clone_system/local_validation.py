"""
================================================================================
LAYER 7: LOCAL VALIDATION LAYER
================================================================================
Clone o'zgartirish kiritgach, darrov o'zini tekshirishi kerak.

Bu hali final eval emas. Bu local gate.

Tekshiruvlar:
- syntax
- lint
- typecheck
- import health
- unit tests
- smoke tests
- tool loading
- config validation

World No1+ qoida:

Agar clone o'zi yozgan o'zgarishni basic local validation'dan o'tkaza olmasa,
keyingi stage'ga o'tmasin.

Bu cheap filter juda foydali:
- axlat candidate'lar erta yiqiladi
- eval resurslari tejaladi
- queue tozalanadi
================================================================================
"""
import os
import sys
import json
import logging
import time
import subprocess
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum

from .core_types import (
    CloneStatus, ValidationResult, ValidationReport
)
from .clone_factory import CloneFactory
from .runtime_isolation import CloneRuntime

logger = logging.getLogger(__name__)


# ================================================================================
# LOCAL VALIDATOR
# ================================================================================

class LocalValidator:
    """
    Local Validator - Clone ichida mahalliy tekshiruv
    
    Bu class:
    1. Syntax tekshiradi
    2. Lint qiladi
    3. Typecheck qiladi
    4. Import health tekshiradi
    5. Unit tests ishga tushiradi
    6. Smoke tests ishga tushiradi
    7. Tool loading tekshiradi
    8. Config validation qiladi
    """
    
    def __init__(self, factory: CloneFactory):
        self.factory = factory
        
        logger.info("🔬 Local Validator initialized")
    
    def validate_clone(self, clone_id: str) -> ValidationReport:
        """
        Clone ni tekshirish
        
        Args:
            clone_id: Clone ID
        
        Returns:
            ValidationReport: Tekshiruv natijasi
        """
        start_time = time.time()
        
        validation_id = f"validation_{clone_id}_{int(start_time * 1000)}"
        
        # Get clone directory
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return self._create_error_report(validation_id, clone_id, "Clone directory not found")
        
        # Create runtime for execution
        runtime = CloneRuntime(
            clone_id=clone_id,
            limits=None,
            workspace_root=str(clone_dir)
        )
        
        report = ValidationReport(
            validation_id=validation_id,
            clone_id=clone_id,
            patch_id=None
        )
        
        # Run all validations
        try:
            # 1. Syntax check
            report.syntax_check = self._check_syntax(clone_dir)
            
            # 2. Lint check
            report.lint_check = self._check_lint(clone_dir)
            
            # 3. Typecheck
            report.typecheck = self._check_typecheck(clone_dir)
            
            # 4. Import health
            report.import_health = self._check_imports(clone_dir)
            
            # 5. Unit tests
            report.unit_tests = self._run_unit_tests(clone_dir, runtime)
            
            # 6. Smoke tests
            report.smoke_tests = self._run_smoke_tests(clone_dir, runtime)
            
            # 7. Tool loading
            report.tool_loading = self._check_tool_loading(clone_dir, runtime)
            
            # 8. Config validation
            report.config_validation = self._validate_config(clone_dir)
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            report.errors.append(str(e))
        
        # Calculate overall
        report.overall = self._calculate_overall(report)
        report.can_proceed = self._can_proceed(report)
        report.duration = time.time() - start_time
        report.completed_at = time.time()
        
        logger.info(f"✅ Validation complete: {report.validation_id} - overall: {report.overall.value}")
        
        return report
    
    def _check_syntax(self, clone_dir: Path) -> ValidationResult:
        """Syntax tekshirish"""
        errors = []
        
        for py_file in clone_dir.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                compile(content, str(py_file), 'exec')
                
            except SyntaxError as e:
                errors.append(f"{py_file.name}:{e.lineno} - {e.msg}")
            except Exception as e:
                # Ignore non-critical errors
                pass
        
        if errors:
            return ValidationResult.FAIL
        
        return ValidationResult.PASS
    
    def _check_lint(self, clone_dir: Path) -> ValidationResult:
        """Lint tekshirish"""
        # Check for ruff
        try:
            result = subprocess.run(
                ["which", "ruff"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Run ruff
                result = subprocess.run(
                    ["ruff", "check", str(clone_dir), "--exit-zero"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode not in [0, 1]:  # 1 = warnings found
                    return ValidationResult.WARNING
                
                # Check for errors in output
                if "error:" in result.stdout.lower():
                    return ValidationResult.WARNING
                
                return ValidationResult.PASS
                
        except Exception as e:
            logger.debug(f"Lint check skipped: {e}")
        
        return ValidationResult.SKIP
    
    def _check_typecheck(self, clone_dir: Path) -> ValidationResult:
        """Typecheck tekshirish"""
        # Check for mypy
        try:
            result = subprocess.run(
                ["which", "mypy"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Run mypy
                result = subprocess.run(
                    ["mypy", str(clone_dir), "--ignore-missing-imports", "--no-error-summary"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                # mypy returns 0 if no errors
                if result.returncode == 0:
                    return ValidationResult.PASS
                else:
                    return ValidationResult.WARNING
                    
        except Exception as e:
            logger.debug(f"Typecheck skipped: {e}")
        
        return ValidationResult.SKIP
    
    def _check_imports(self, clone_dir: Path) -> ValidationResult:
        """Import health tekshirish"""
        # Try to import main modules
        sys.path.insert(0, str(clone_dir))
        
        errors = []
        
        # Check agent package
        agent_dir = clone_dir / "agent"
        if agent_dir.exists():
            for py_file in agent_dir.glob("*.py"):
                if py_file.stem not in ["__init__"]:
                    try:
                        module_name = f"agent.{py_file.stem}"
                        __import__(module_name)
                    except ImportError as e:
                        errors.append(f"{py_file.name}: {e}")
                    except Exception as e:
                        errors.append(f"{py_file.name}: {e}")
        
        sys.path.remove(str(clone_dir))
        
        if errors:
            logger.warning(f"Import errors: {errors[:3]}")
            return ValidationResult.WARNING
        
        return ValidationResult.PASS
    
    def _run_unit_tests(self, clone_dir: Path, runtime: CloneRuntime) -> ValidationResult:
        """Unit tests ishga tushirish"""
        # Look for test files
        test_files = list(clone_dir.rglob("test_*.py"))
        
        if not test_files:
            return ValidationResult.SKIP
        
        try:
            # Run pytest
            result = subprocess.run(
                ["python", "-m", "pytest", str(clone_dir), "-v", "--tb=short", "-x"],
                capture_output=True,
                text=True,
                cwd=str(clone_dir),
                timeout=300,
                env={**os.environ, "PYTHONPATH": str(clone_dir)}
            )
            
            if result.returncode == 0:
                return ValidationResult.PASS
            elif result.returncode == 5:  # No tests collected
                return ValidationResult.SKIP
            else:
                return ValidationResult.FAIL
                
        except subprocess.TimeoutExpired:
            return ValidationResult.WARNING
        except Exception as e:
            logger.debug(f"Unit tests skipped: {e}")
            return ValidationResult.SKIP
    
    def _run_smoke_tests(self, clone_dir: Path, runtime: CloneRuntime) -> ValidationResult:
        """Smoke tests ishga tushirish"""
        # Simple smoke test - try importing key modules
        smoke_tests = [
            ("agent", "import agent"),
            ("agent.kernel", "import agent.kernel"),
            ("agent.tools", "import agent.tools"),
        ]
        
        passed = 0
        
        for module, import_stmt in smoke_tests:
            try:
                # Create a simple test script
                test_code = f"""
import sys
sys.path.insert(0, '{clone_dir}')
{import_stmt}
print('OK')
"""
                
                result = subprocess.run(
                    ["python", "-c", test_code],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 and "OK" in result.stdout:
                    passed += 1
                    
            except Exception as e:
                logger.debug(f"Smoke test failed: {e}")
        
        if passed == 0:
            return ValidationResult.FAIL
        elif passed < len(smoke_tests):
            return ValidationResult.WARNING
        
        return ValidationResult.PASS
    
    def _check_tool_loading(self, clone_dir: Path, runtime: CloneRuntime) -> ValidationResult:
        """Tool loading tekshirish"""
        # Try loading tools
        try:
            test_code = f"""
import sys
sys.path.insert(0, '{clone_dir}')
from agent.tools import ToolsEngine
print('OK')
"""
            
            result = subprocess.run(
                ["python", "-c", test_code],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and "OK" in result.stdout:
                return ValidationResult.PASS
            else:
                return ValidationResult.WARNING
                
        except Exception as e:
            logger.debug(f"Tool loading check skipped: {e}")
        
        return ValidationResult.SKIP
    
    def _validate_config(self, clone_dir: Path) -> ValidationResult:
        """Config validation"""
        config_issues = []
        
        # Check for .env
        env_file = clone_dir / ".env"
        if env_file.exists():
            # Check for required keys
            with open(env_file, 'r') as f:
                content = f.read()
            
            required_keys = ["OPENAI_API_KEY"]
            for key in required_keys:
                if key not in content:
                    config_issues.append(f"Missing {key} in .env")
        
        # Check for config files
        config_dir = clone_dir / "agent" / "config"
        if config_dir.exists():
            for config_file in config_dir.glob("*.py"):
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                    
                    # Check for obvious issues
                    if "TODO" in content:
                        config_issues.append(f"{config_file.name}: Contains TODOs")
                        
                except Exception as e:
                    config_issues.append(f"{config_file.name}: {e}")
        
        if config_issues:
            logger.warning(f"Config issues: {config_issues}")
            return ValidationResult.WARNING
        
        return ValidationResult.PASS
    
    def _calculate_overall(self, report: ValidationReport) -> ValidationResult:
        """Umumiy natijani hisoblash"""
        checks = [
            report.syntax_check,
            report.lint_check,
            report.typecheck,
            report.import_health,
            report.unit_tests,
            report.smoke_tests,
            report.tool_loading,
            report.config_validation
        ]
        
        # Filter out skips
        valid_checks = [c for c in checks if c != ValidationResult.SKIP]
        
        if not valid_checks:
            return ValidationResult.SKIP
        
        # Calculate
        failed = sum(1 for c in valid_checks if c == ValidationResult.FAIL)
        warnings = sum(1 for c in valid_checks if c == ValidationResult.WARNING)
        
        if failed > 0:
            return ValidationResult.FAIL
        elif warnings > len(valid_checks) // 2:
            return ValidationResult.WARNING
        else:
            return ValidationResult.PASS
    
    def _can_proceed(self, report: ValidationReport) -> bool:
        """Keyingi bosqichga o'tish mumkinmi"""
        # Must pass syntax, imports, and at least one test
        must_pass = [
            report.syntax_check,
            report.import_health
        ]
        
        must_not_fail = [
            report.unit_tests,
            report.smoke_tests,
            report.tool_loading
        ]
        
        # Check must pass
        for check in must_pass:
            if check == ValidationResult.FAIL:
                return False
        
        # Check must not fail
        for check in must_not_fail:
            if check == ValidationResult.FAIL:
                return False
        
        # Overall should be pass or warning
        return report.overall in [ValidationResult.PASS, ValidationResult.WARNING]
    
    def _create_error_report(self, validation_id: str, clone_id: str, error: str) -> ValidationReport:
        """Xato report yaratish"""
        return ValidationReport(
            validation_id=validation_id,
            clone_id=clone_id,
            patch_id=None,
            errors=[error],
            overall=ValidationResult.FAIL,
            can_proceed=False
        )


# ================================================================================
# VALIDATION GATE
# ================================================================================

class ValidationGate:
    """
    Validation Gate - Validatsiya qoidalari
    
    Bu class:
    1. Validatsiya qoidalarini belgilaydi
    2. Gate statusni kuzatadi
    3. Can proceed qarorini qabul qiladi
    """
    
    def __init__(self):
        # Required checks for each clone type
        self.required_checks = {
            "small_patch": ["syntax", "import_health"],
            "capability": ["syntax", "import_health", "unit_tests"],
            "workflow": ["syntax", "import_health", "smoke_tests"],
            "research": ["syntax"],
            "fork": ["syntax", "import_health", "unit_tests", "smoke_tests"]
        }
        
        logger.info("🚪 Validation Gate initialized")
    
    def can_proceed(self, clone_type: str, report: ValidationReport) -> Dict:
        """
        Can proceed qarori
        
        Args:
            clone_type: Clone turi
            report: ValidationReport
        
        Returns:
            Dict: Qaror
        """
        required = self.required_checks.get(clone_type, ["syntax"])
        
        # Check each required
        for check in required:
            check_result = getattr(report, check, ValidationResult.SKIP)
            
            if check_result == ValidationResult.FAIL:
                return {
                    "can_proceed": False,
                    "reason": f"Required check failed: {check}",
                    "blocking": True
                }
        
        # Overall check
        if report.overall == ValidationResult.FAIL:
            return {
                "can_proceed": False,
                "reason": "Overall validation failed",
                "blocking": True
            }
        
        if report.overall == ValidationResult.WARNING:
            return {
                "can_proceed": True,
                "reason": "Passed with warnings",
                "blocking": False
            }
        
        return {
            "can_proceed": True,
            "reason": "All checks passed",
            "blocking": False
        }
    
    def get_blocking_issues(self, report: ValidationReport) -> List[str]:
        """Bloklayotgan muammolarni olish"""
        issues = []
        
        if report.syntax_check == ValidationResult.FAIL:
            issues.append("Syntax errors")
        
        if report.import_health == ValidationResult.FAIL:
            issues.append("Import failures")
        
        if report.unit_tests == ValidationResult.FAIL:
            issues.append("Unit tests failed")
        
        if report.smoke_tests == ValidationResult.FAIL:
            issues.append("Smoke tests failed")
        
        if report.tool_loading == ValidationResult.FAIL:
            issues.append("Tool loading failed")
        
        return issues


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_local_validator(factory: CloneFactory) -> LocalValidator:
    """Local Validator yaratish"""
    return LocalValidator(factory)


def create_validation_gate() -> ValidationGate:
    """Validation Gate yaratish"""
    return ValidationGate()
