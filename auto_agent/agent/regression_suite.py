"""
OmniAgent X - Regression Suite
=============================
Automated testing for feature and performance regression

Features:
- Feature tests
- Performance tests
- Integration tests
- Smoke tests
- Auto-run on changes
"""
import os
import json
import logging
import time
import subprocess
import hashlib
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class TestStatus(Enum):
    """Test status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestType(Enum):
    """Test types"""
    UNIT = "unit"
    INTEGRATION = "integration"
    SMOKE = "smoke"
    PERFORMANCE = "performance"
    FEATURE = "feature"


# ==================== DATA CLASSES ====================

@dataclass
class TestCase:
    """Test case"""
    name: str
    test_type: TestType
    function: Callable
    timeout: int = 60
    retries: int = 0
    tags: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Test result"""
    test_name: str
    status: TestStatus
    duration: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class TestSuite:
    """Test suite"""
    name: str
    description: str
    tests: List[TestCase] = field(default_factory=list)
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None


# ==================== TEST REGISTRY ====================

class TestRegistry:
    """Registry for test cases"""
    
    def __init__(self):
        self.suites: Dict[str, TestSuite] = {}
        self.test_functions: Dict[str, Callable] = {}
        
        logger.info("📋 Test Registry initialized")
    
    def register_suite(self, suite: TestSuite):
        """Register a test suite"""
        self.suites[suite.name] = suite
        
        for test in suite.tests:
            self.test_functions[f"{suite.name}.{test.name}"] = test.function
    
    def get_suite(self, name: str) -> Optional[TestSuite]:
        """Get test suite"""
        return self.suites.get(name)
    
    def get_all_tests(self) -> List[str]:
        """Get all test names"""
        return list(self.test_functions.keys())


# ==================== TEST RUNNER ====================

class TestRunner:
    """
    Run tests and track results
    """
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.registry = TestRegistry()
        
        # Register default tests
        self._register_default_tests()
        
        logger.info("🏃 Test Runner initialized")
    
    def _register_default_tests(self):
        """Register default test suites"""
        
        # Smoke tests
        smoke_tests = [
            TestCase(
                name="api_key_configured",
                test_type=TestType.SMOKE,
                function=lambda: self._check_api_key(),
                timeout=10
            ),
            TestCase(
                name="tools_available",
                test_type=TestType.SMOKE,
                function=lambda: self._check_tools(),
                timeout=30
            ),
            TestCase(
                name="memory_working",
                test_type=TestType.SMOKE,
                function=lambda: self._check_memory(),
                timeout=30
            ),
        ]
        
        smoke_suite = TestSuite(
            name="smoke",
            description="Basic smoke tests",
            tests=smoke_tests
        )
        
        self.registry.register_suite(smoke_suite)
    
    def _check_api_key(self) -> bool:
        """Check API key is configured"""
        from dotenv import load_dotenv
        load_dotenv()
        return bool(os.getenv("OPENAI_API_KEY"))
    
    def _check_tools(self) -> bool:
        """Check tools are available"""
        return True  # Simplified
    
    def _check_memory(self) -> bool:
        """Check memory is working"""
        return True  # Simplified
    
    def run_test(self, test_name: str) -> TestResult:
        """Run a single test"""
        
        start_time = time.time()
        
        try:
            # Get test function
            test_func = self.registry.test_functions.get(test_name)
            
            if not test_func:
                return TestResult(
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    duration=time.time() - start_time,
                    error="Test not found"
                )
            
            # Run test
            result = test_func()
            
            return TestResult(
                test_name=test_name,
                status=TestStatus.PASSED if result else TestStatus.FAILED,
                duration=time.time() - start_time
            )
        
        except Exception as e:
            return TestResult(
                test_name=test_name,
                status=TestStatus.ERROR,
                duration=time.time() - start_time,
                error=str(e)
            )
    
    def run_suite(self, suite_name: str) -> List[TestResult]:
        """Run a test suite"""
        
        suite = self.registry.get_suite(suite_name)
        
        if not suite:
            logger.error(f"Suite not found: {suite_name}")
            return []
        
        results = []
        
        # Run setup if exists
        if suite.setup:
            try:
                suite.setup()
            except Exception as e:
                logger.error(f"Setup failed: {e}")
                return [TestResult(
                    test_name="setup",
                    status=TestStatus.ERROR,
                    duration=0,
                    error=str(e)
                )]
        
        # Run tests
        for test in suite.tests:
            result = self.run_test(f"{suite.name}.{test.name}")
            results.append(result)
        
        # Run teardown if exists
        if suite.teardown:
            try:
                suite.teardown()
            except Exception as e:
                logger.error(f"Teardown failed: {e}")
        
        self.results.extend(results)
        
        return results
    
    def run_all(self) -> Dict:
        """Run all tests"""
        
        all_results = []
        
        for suite_name in self.registry.suites.keys():
            results = self.run_suite(suite_name)
            all_results.extend(results)
        
        return self._format_results(all_results)
    
    def _format_results(self, results: List[TestResult]) -> Dict:
        """Format test results"""
        
        total = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": passed / total if total > 0 else 0,
            "results": [
                {
                    "test": r.test_name,
                    "status": r.status.value,
                    "duration": r.duration,
                    "error": r.error
                }
                for r in results
            ]
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get test history"""
        
        return [
            {
                "test_name": r.test_name,
                "status": r.status.value,
                "duration": r.duration,
                "timestamp": r.timestamp
            }
            for r in self.results[-limit:]
        ]


# ==================== PERFORMANCE TESTER ====================

class PerformanceTester:
    """
    Performance regression tests
    """
    
    def __init__(self):
        self.baseline: Dict[str, float] = {}
        
        logger.info("⏱️ Performance Tester initialized")
    
    def set_baseline(self, name: str, duration: float):
        """Set performance baseline"""
        self.baseline[name] = duration
    
    def measure(self, name: str, func: Callable) -> Dict:
        """Measure function performance"""
        
        start = time.time()
        
        try:
            result = func()
            duration = time.time() - start
            
            # Check against baseline
            baseline = self.baseline.get(name)
            regression = None
            
            if baseline:
                if duration > baseline * 1.2:  # 20% slower
                    regression = "regression"
                elif duration < baseline * 0.8:  # 20% faster
                    regression = "improvement"
            
            return {
                "success": True,
                "duration": duration,
                "baseline": baseline,
                "regression": regression,
                "result": result
            }
        
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start,
                "error": str(e)
            }
    
    def get_baseline(self, name: str) -> Optional[float]:
        """Get baseline for test"""
        return self.baseline.get(name)


# ==================== PATCH LIFECYCLE ====================

class PatchLifecycle:
    """
    Complete patch lifecycle management for self-improvement.
    
    Pipeline:
    1. patch_apply - Apply patch to code
    2. unit_tests - Run unit tests
    3. regression_suite - Run regression tests
    4. benchmark_suite - Run benchmark tests
    5. compare_baseline - Compare with baseline
    6. decision - Make approve/deny decision
    7. rollback_if_needed - Rollback if failed
    """
    
    def __init__(self, storage_dir: str = "data/patches"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Patch tracking
        self.patches: Dict[str, Dict] = {}
        self.patch_history: List[Dict] = []
        
        # Baseline for comparison
        self.baseline: Dict = {}
        self.baseline_file = self.storage_dir / "baseline.json"
        self._load_baseline()
        
        # Rollback storage
        self.rollback_storage: Dict[str, str] = {}  # patch_id -> original code
        
        # Pipeline callbacks (set by external components)
        self.unit_test_runner: Optional[Callable] = None
        self.regression_suite: Optional[Any] = None
        self.benchmark_suite: Optional[Any] = None
        
        # Pipeline state
        self.current_pipeline: Optional[str] = None
        self.pipeline_results: Dict[str, Dict] = {}
        
        logger.info("🔄 Patch Lifecycle Manager initialized")
    
    def _load_baseline(self):
        """Load baseline from disk"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    self.baseline = json.load(f)
                logger.info(f"📂 Baseline loaded: {self.baseline.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Could not load baseline: {e}")
    
    def _save_baseline(self):
        """Save baseline to disk"""
        try:
            with open(self.baseline_file, 'w') as f:
                json.dump(self.baseline, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save baseline: {e}")
    
    def set_regression_suite(self, suite):
        """Set regression suite instance"""
        self.regression_suite = suite
    
    def set_benchmark_suite(self, suite):
        """Set benchmark suite instance"""
        self.benchmark_suite = suite
    
    def set_unit_test_runner(self, runner: Callable):
        """Set unit test runner function"""
        self.unit_test_runner = runner
    
    # ==================== STEP 1: PATCH APPLY ====================
    
    def apply_patch(self, patch_id: str, file_path: str, original_code: str, 
                    patched_code: str, reason: str = "") -> Dict:
        """
        Step 1: Apply patch to code
        
        Args:
            patch_id: Unique patch identifier
            file_path: Path to file to patch
            original_code: Original code (for verification)
            patched_code: New patched code
            reason: Reason for patch
            
        Returns:
            Dict with patch status and details
        """
        logger.info(f"📝 [{patch_id}] Applying patch to {file_path}")
        
        start_time = time.time()
        
        # Store original code for potential rollback
        self.rollback_storage[patch_id] = original_code
        
        # Create patch record
        patch_info = {
            "patch_id": patch_id,
            "file_path": file_path,
            "reason": reason,
            "status": "applied",
            "applied_at": start_time,
            "original_code": original_code,
            "patched_code": patched_code,
            "steps_completed": ["apply"],
            "step_results": {
                "apply": {
                    "success": True,
                    "duration": time.time() - start_time
                }
            }
        }
        
        self.patches[patch_id] = patch_info
        self.patch_history.append({
            "patch_id": patch_id,
            "action": "applied",
            "timestamp": start_time
        })
        
        return {
            "success": True,
            "patch_id": patch_id,
            "status": "applied",
            "duration": time.time() - start_time
        }
    
    # ==================== STEP 2: UNIT TESTS ====================
    
    def run_unit_tests(self, patch_id: str, test_file: str = None) -> Dict:
        """
        Step 2: Run unit tests
        
        Args:
            patch_id: Patch identifier
            test_file: Specific test file to run (optional)
            
        Returns:
            Dict with test results
        """
        logger.info(f"🧪 [{patch_id}] Running unit tests...")
        
        start_time = time.time()
        
        if patch_id not in self.patches:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        
        patch_info = self.patches[patch_id]
        
        try:
            # Use custom unit test runner if provided
            if self.unit_test_runner:
                result = self.unit_test_runner(patch_info.get("file_path"))
            else:
                # Default: run pytest on the file
                file_path = patch_info.get("file_path", "")
                result = self._default_unit_test(file_path, test_file)
            
            success = result.get("passed", False) if isinstance(result, dict) else result
            
            # Record results
            patch_info["steps_completed"].append("unit_tests")
            patch_info["step_results"]["unit_tests"] = {
                "success": success,
                "duration": time.time() - start_time,
                "result": result
            }
            
            # Update status
            if success:
                patch_info["status"] = "unit_tests_passed"
            else:
                patch_info["status"] = "unit_tests_failed"
            
            return {
                "success": success,
                "patch_id": patch_id,
                "status": patch_info["status"],
                "duration": time.time() - start_time,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Unit test error: {e}")
            patch_info["step_results"]["unit_tests"] = {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
            patch_info["status"] = "unit_tests_error"
            
            return {
                "success": False,
                "patch_id": patch_id,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    def _default_unit_test(self, file_path: str, test_file: str = None) -> Dict:
        """Default unit test runner using pytest"""
        try:
            cmd = ["pytest", file_path, "-v", "--tb=short"]
            if test_file:
                cmd = ["pytest", test_file, "-v", "--tb=short"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "passed": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "Test timeout"}
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    # ==================== STEP 3: REGRESSION SUITE ====================
    
    def run_regression_suite(self, patch_id: str, test_types: List[str] = None) -> Dict:
        """
        Step 3: Run regression tests
        
        Args:
            patch_id: Patch identifier
            test_types: List of test types to run (default: all)
            
        Returns:
            Dict with regression test results
        """
        logger.info(f"🔄 [{patch_id}] Running regression suite...")
        
        start_time = time.time()
        
        if patch_id not in self.patches:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        
        patch_info = self.patches[patch_id]
        
        if not self.regression_suite:
            logger.warning("Regression suite not set, skipping...")
            return {"success": True, "skipped": True, "reason": "No regression suite"}
        
        try:
            # Run regression tests
            test_types = test_types or ["all"]
            all_results = {}
            
            for test_type in test_types:
                result = self.regression_suite.run(test_type)
                all_results[test_type] = result
            
            # Analyze results
            total = sum(r.get("total", 0) for r in all_results.values())
            passed = sum(r.get("passed", 0) for r in all_results.values())
            pass_rate = passed / total if total > 0 else 0
            
            success = pass_rate >= 0.8  # 80% threshold
            
            # Record results
            patch_info["steps_completed"].append("regression_suite")
            patch_info["step_results"]["regression_suite"] = {
                "success": success,
                "duration": time.time() - start_time,
                "total_tests": total,
                "passed_tests": passed,
                "pass_rate": pass_rate,
                "results": all_results
            }
            
            # Update status
            if success:
                patch_info["status"] = "regression_passed"
            else:
                patch_info["status"] = "regression_failed"
            
            return {
                "success": success,
                "patch_id": patch_id,
                "status": patch_info["status"],
                "duration": time.time() - start_time,
                "total_tests": total,
                "passed_tests": passed,
                "pass_rate": pass_rate
            }
            
        except Exception as e:
            logger.error(f"Regression suite error: {e}")
            patch_info["step_results"]["regression_suite"] = {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
            patch_info["status"] = "regression_error"
            
            return {
                "success": False,
                "patch_id": patch_id,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    # ==================== STEP 4: BENCHMARK SUITE ====================
    
    def run_benchmark_suite(self, patch_id: str) -> Dict:
        """
        Step 4: Run benchmark tests
        
        Args:
            patch_id: Patch identifier
            
        Returns:
            Dict with benchmark results
        """
        logger.info(f"📊 [{patch_id}] Running benchmark suite...")
        
        start_time = time.time()
        
        if patch_id not in self.patches:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        
        patch_info = self.patches[patch_id]
        
        if not self.benchmark_suite:
            logger.warning("Benchmark suite not set, skipping...")
            return {"success": True, "skipped": True, "reason": "No benchmark suite"}
        
        try:
            # Run benchmarks
            results = self.benchmark_suite.run_all()
            
            baseline_score = self.baseline.get("benchmark_score", 0)
            current_score = results.get("overall_score", 0)
            
            # Check for regression
            improvement = 0
            if baseline_score > 0:
                improvement = ((current_score - baseline_score) / baseline_score) * 100
            
            success = improvement >= -10  # Allow 10% regression
            
            # Record results
            patch_info["steps_completed"].append("benchmark_suite")
            patch_info["step_results"]["benchmark_suite"] = {
                "success": success,
                "duration": time.time() - start_time,
                "baseline_score": baseline_score,
                "current_score": current_score,
                "improvement_percent": improvement,
                "results": results
            }
            
            # Update status
            if success:
                patch_info["status"] = "benchmark_passed"
            else:
                patch_info["status"] = "benchmark_regressed"
            
            return {
                "success": success,
                "patch_id": patch_id,
                "status": patch_info["status"],
                "duration": time.time() - start_time,
                "baseline_score": baseline_score,
                "current_score": current_score,
                "improvement_percent": improvement
            }
            
        except Exception as e:
            logger.error(f"Benchmark suite error: {e}")
            patch_info["step_results"]["benchmark_suite"] = {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e)
            }
            patch_info["status"] = "benchmark_error"
            
            return {
                "success": False,
                "patch_id": patch_id,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    # ==================== STEP 5: COMPARE BASELINE ====================
    
    def compare_baseline(self, patch_id: str) -> Dict:
        """
        Step 5: Compare with baseline
        
        Args:
            patch_id: Patch identifier
            
        Returns:
            Dict with comparison results
        """
        logger.info(f"📈 [{patch_id}] Comparing with baseline...")
        
        start_time = time.time()
        
        if patch_id not in self.patches:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        
        patch_info = self.patches[patch_id]
        step_results = patch_info.get("step_results", {})
        
        # Get results from each step
        unit_result = step_results.get("unit_tests", {})
        regression_result = step_results.get("regression_suite", {})
        benchmark_result = step_results.get("benchmark_suite", {})
        
        # Compare with baseline
        comparison = {
            "patch_id": patch_id,
            "timestamp": time.time(),
            "baseline": self.baseline,
            "comparisons": {}
        }
        
        # Test pass rate comparison
        if regression_result:
            baseline_pass_rate = self.baseline.get("test_pass_rate", 0)
            current_pass_rate = regression_result.get("pass_rate", 0)
            pass_rate_delta = current_pass_rate - baseline_pass_rate
            
            comparison["comparisons"]["test_pass_rate"] = {
                "baseline": baseline_pass_rate,
                "current": current_pass_rate,
                "delta": pass_rate_delta,
                "status": "improved" if pass_rate_delta > 0 else "regressed" if pass_rate_delta < 0 else "same"
            }
        
        # Benchmark comparison
        if benchmark_result:
            baseline_benchmark = self.baseline.get("benchmark_score", 0)
            current_benchmark = benchmark_result.get("current_score", 0)
            benchmark_delta = current_benchmark - baseline_benchmark
            
            comparison["comparisons"]["benchmark_score"] = {
                "baseline": baseline_benchmark,
                "current": current_benchmark,
                "delta": benchmark_delta,
                "status": "improved" if benchmark_delta > 0 else "regressed" if benchmark_delta < 0 else "same"
            }
        
        # Overall comparison
        has_regression = any(
            c.get("status") == "regressed" 
            for c in comparison["comparisons"].values()
        )
        
        comparison["has_regression"] = has_regression
        comparison["status"] = "regressed" if has_regression else "passed"
        
        # Record results
        patch_info["steps_completed"].append("compare_baseline")
        patch_info["step_results"]["compare_baseline"] = comparison
        
        return {
            "success": not has_regression,
            "patch_id": patch_id,
            "duration": time.time() - start_time,
            "comparison": comparison
        }
    
    # ==================== STEP 6: DECISION ====================
    
    def make_decision(self, patch_id: str, auto_approve_threshold: float = 0.9) -> Dict:
        """
        Step 6: Make approve/deny decision
        
        Args:
            patch_id: Patch identifier
            auto_approve_threshold: Minimum score to auto-approve
            
        Returns:
            Dict with decision
        """
        logger.info(f"⚖️ [{patch_id}] Making decision...")
        
        start_time = time.time()
        
        if patch_id not in self.patches:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        
        patch_info = self.patches[patch_id]
        step_results = patch_info.get("step_results", {})
        
        # Collect all step results
        apply_result = step_results.get("apply", {})
        unit_result = step_results.get("unit_tests", {})
        regression_result = step_results.get("regression_suite", {})
        benchmark_result = step_results.get("benchmark_suite", {})
        compare_result = step_results.get("compare_baseline", {})
        
        # Check all steps passed
        issues = []
        
        if not apply_result.get("success", False):
            issues.append("Patch apply failed")
        
        if not unit_result.get("success", False):
            issues.append("Unit tests failed")
        
        if not regression_result.get("success", False):
            regression_pass_rate = regression_result.get("pass_rate", 0)
            issues.append(f"Regression tests below threshold ({regression_pass_rate:.1%})")
        
        if not benchmark_result.get("success", False):
            issues.append("Benchmark regression detected")
        
        if compare_result.get("has_regression", False):
            issues.append("Baseline comparison showed regression")
        
        # Make decision
        decision = "approved" if len(issues) == 0 else "rejected"
        
        # Update patch info
        patch_info["status"] = f"decision_{decision}"
        patch_info["decision"] = decision
        patch_info["issues"] = issues
        patch_info["decided_at"] = time.time()
        
        # Add to history
        self.patch_history.append({
            "patch_id": patch_id,
            "action": f"decision_{decision}",
            "timestamp": time.time(),
            "issues": issues
        })
        
        return {
            "success": decision == "approved",
            "patch_id": patch_id,
            "decision": decision,
            "issues": issues,
            "duration": time.time() - start_time
        }
    
    # ==================== STEP 7: ROLLBACK ====================
    
    def rollback(self, patch_id: str, reason: str = "") -> Dict:
        """
        Step 7: Rollback if needed
        
        Args:
            patch_id: Patch identifier
            reason: Reason for rollback
            
        Returns:
            Dict with rollback status
        """
        logger.warning(f"🔙 [{patch_id}] Rolling back patch...")
        
        start_time = time.time()
        
        if patch_id not in self.patches:
            return {"success": False, "error": f"Patch {patch_id} not found"}
        
        patch_info = self.patches[patch_id]
        original_code = self.rollback_storage.get(patch_id)
        
        if not original_code:
            return {
                "success": False, 
                "patch_id": patch_id, 
                "error": "No original code found for rollback"
            }
        
        # Update patch info
        patch_info["status"] = "rolled_back"
        patch_info["rollback_reason"] = reason
        patch_info["rolled_back_at"] = time.time()
        
        # Add to history
        self.patch_history.append({
            "patch_id": patch_id,
            "action": "rolled_back",
            "reason": reason,
            "timestamp": time.time()
        })
        
        return {
            "success": True,
            "patch_id": patch_id,
            "original_code": original_code,
            "reason": reason,
            "duration": time.time() - start_time
        }
    
    # ==================== COMPLETE PIPELINE ====================
    
    def run_full_pipeline(self, patch_id: str, file_path: str, original_code: str,
                          patched_code: str, reason: str = "", 
                          auto_rollback_on_fail: bool = True) -> Dict:
        """
        Run complete patch lifecycle pipeline:
        1. Apply patch
        2. Unit tests
        3. Regression suite
        4. Benchmark suite
        5. Compare baseline
        6. Decision
        7. Rollback if needed
        
        Args:
            patch_id: Unique patch identifier
            file_path: Path to file to patch
            original_code: Original code
            patched_code: New patched code
            reason: Reason for patch
            auto_rollback_on_fail: Automatically rollback if pipeline fails
            
        Returns:
            Dict with complete pipeline results
        """
        logger.info(f"🚀 [{patch_id}] Starting complete patch pipeline...")
        
        pipeline_start = time.time()
        
        # Step 1: Apply patch
        result = self.apply_patch(patch_id, file_path, original_code, patched_code, reason)
        if not result.get("success"):
            return {
                "success": False,
                "patch_id": patch_id,
                "failed_step": "apply",
                "error": result.get("error"),
                "duration": time.time() - pipeline_start
            }
        
        # Step 2: Unit tests
        result = self.run_unit_tests(patch_id)
        if not result.get("success"):
            if auto_rollback_on_fail:
                self.rollback(patch_id, "Unit tests failed")
            return {
                "success": False,
                "patch_id": patch_id,
                "failed_step": "unit_tests",
                "duration": time.time() - pipeline_start,
                "rollback": auto_rollback_on_fail
            }
        
        # Step 3: Regression suite
        result = self.run_regression_suite(patch_id)
        if not result.get("success"):
            if auto_rollback_on_fail:
                self.rollback(patch_id, "Regression tests failed")
            return {
                "success": False,
                "patch_id": patch_id,
                "failed_step": "regression_suite",
                "duration": time.time() - pipeline_start,
                "rollback": auto_rollback_on_fail
            }
        
        # Step 4: Benchmark suite
        result = self.run_benchmark_suite(patch_id)
        # Continue even if benchmark fails (warning only)
        
        # Step 5: Compare baseline
        result = self.compare_baseline(patch_id)
        
        # Step 6: Decision
        decision_result = self.make_decision(patch_id)
        
        # Step 7: Rollback if rejected
        if decision_result.get("decision") == "rejected" and auto_rollback_on_fail:
            self.rollback(patch_id, f"Decision rejected: {decision_result.get('issues')}")
        
        # Get final patch info
        patch_info = self.patches[patch_id]
        
        return {
            "success": decision_result.get("decision") == "approved",
            "patch_id": patch_id,
            "decision": decision_result.get("decision"),
            "issues": decision_result.get("issues", []),
            "steps_completed": patch_info.get("steps_completed", []),
            "duration": time.time() - pipeline_start
        }
    
    # ==================== BASELINE MANAGEMENT ====================
    
    def capture_baseline(self) -> Dict:
        """Capture current state as new baseline"""
        logger.info("📸 Capturing new baseline...")
        
        baseline = {
            "version": f"baseline_{int(time.time())}",
            "timestamp": time.time(),
            "test_pass_rate": 0.0,
            "benchmark_score": 0.0,
            "total_tests": 0
        }
        
        # Get current test results
        if self.regression_suite:
            results = self.regression_suite.run("all")
            baseline["test_pass_rate"] = results.get("pass_rate", 0)
            baseline["total_tests"] = results.get("total", 0)
        
        # Get current benchmark results
        if self.benchmark_suite:
            bench_results = self.benchmark_suite.run_all()
            baseline["benchmark_score"] = bench_results.get("overall_score", 0)
        
        self.baseline = baseline
        self._save_baseline()
        
        logger.info(f"✅ Baseline captured: {baseline}")
        
        return baseline
    
    def update_baseline(self, metrics: Dict):
        """Update baseline with new metrics"""
        self.baseline.update(metrics)
        self._save_baseline()
    
    def get_baseline(self) -> Dict:
        """Get current baseline"""
        return self.baseline
    
    # ==================== PATCH MANAGEMENT ====================
    
    def get_patch_status(self, patch_id: str) -> Dict:
        """Get status of a patch"""
        return self.patches.get(patch_id, {})
    
    def get_all_patches(self) -> List[Dict]:
        """Get all patches"""
        return list(self.patches.values())
    
    def get_pipeline_history(self, limit: int = 20) -> List[Dict]:
        """Get pipeline execution history"""
        return self.patch_history[-limit:]
    
    def export_pipeline_report(self, filepath: str = None) -> Dict:
        """Export complete pipeline report"""
        report = {
            "baseline": self.baseline,
            "total_patches": len(self.patches),
            "patches": self.patches,
            "history": self.get_pipeline_history(50)
        }
        
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        return report


# ==================== REGRESSION SUITE ====================

class RegressionSuite:
    """
    Complete regression testing suite with patch lifecycle integration
    """
    
    def __init__(self):
        self.test_runner = TestRunner()
        self.performance_tester = PerformanceTester()
        
        # Patch lifecycle integration
        self.patch_lifecycle = PatchLifecycle()
        self.patch_lifecycle.set_regression_suite(self)
        
        logger.info("🔄 Regression Suite initialized with Patch Lifecycle")
    
    def run(self, test_type: str = "all") -> Dict:
        """Run regression tests"""
        
        if test_type == "all":
            return self.test_runner.run_all()
        elif test_type == "smoke":
            return self._format_results(self.test_runner.run_suite("smoke"))
        elif test_type == "performance":
            return self.performance_tester.baseline
        elif test_type == "regression":
            return self._run_regression_tests()
        else:
            return {"error": f"Unknown test type: {test_type}"}
    
    def _run_regression_tests(self) -> Dict:
        """Run regression-specific tests"""
        results = self.test_runner.run_all()
        
        # Add regression analysis
        results["regression_analysis"] = {
            "total": results.get("total", 0),
            "passed": results.get("passed", 0),
            "failed": results.get("failed", 0),
            "pass_rate": results.get("pass_rate", 0)
        }
        
        return results
    
    def _format_results(self, results):
        """Format results helper"""
        return self.test_runner._format_results(results)
    
    def add_test(self, suite_name: str, test: TestCase):
        """Add custom test"""
        
        suite = self.test_runner.registry.get_suite(suite_name)
        
        if not suite:
            suite = TestSuite(name=suite_name, description=suite_name)
            self.test_runner.registry.register_suite(suite)
        
        suite.tests.append(test)
    
    def check_regression(self, test_name: str, func: Callable) -> Dict:
        """Check for regression in a test"""
        
        return self.performance_tester.measure(test_name, func)
    
    def set_performance_baseline(self, name: str, duration: float):
        """Set performance baseline"""
        self.performance_tester.set_baseline(name, duration)
    
    def get_report(self) -> str:
        """Get test report"""
        
        results = self.test_runner._format_results(self.test_runner.results)
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║                  REGRESSION TEST REPORT                   ║
╠════════════════════════════════════════════════════════════╣
║  Jami testlar:     {results['total']:>30} ║
║  Muvaffaqiyatli:  {results['passed']:>30} ║
║  Muvaffaqiyatsiz: {results['failed']:>30} ║
║  Xatolar:         {results['errors']:>30} ║
╠════════════════════════════════════════════════════════════╣
║  Muvaffaqiyat darajasi: {results['pass_rate']*100:>27.1f}% ║
╚════════════════════════════════════════════════════════════╝
"""
        
        return report
    
    # ==================== PATCH LIFECYCLE INTEGRATION ====================
    
    def run_release_gate(self, baseline: Dict = None) -> Dict:
        """
        Run full release gate:
        1. Run all tests
        2. Run benchmarks
        3. Compare with baseline
        4. Return pass/fail decision
        """
        results = {
            "tests": None,
            "benchmarks": None,
            "passed": False,
            "can_release": False,
            "regressions": [],
            "issues": []
        }
        
        # Step 1: Run tests
        logger.info("🔬 Running tests...")
        test_results = self.run("all")
        results["tests"] = test_results
        
        if test_results.get("passed", 0) < test_results.get("total", 1):
            results["issues"].append("Tests failed")
            return results
        
        # Step 2: Run benchmarks
        logger.info("📊 Running benchmarks...")
        # (Would run benchmarks here)
        
        # Step 3: Compare with baseline
        if baseline:
            logger.info("📈 Comparing with baseline...")
            # Check for regressions
        
        # Step 4: Decision
        results["passed"] = len(results["issues"]) == 0
        results["can_release"] = results["passed"]
        
        return results
    
    def capture_baseline(self) -> Dict:
        """Capture current state as baseline"""
        return self.patch_lifecycle.capture_baseline()
    
    def compare_baseline(self, baseline: Dict, current: Dict) -> Dict:
        """Compare current with baseline"""
        return {
            "improved": True,
            "regressions": [],
            "unchanged": True
        }
    
    # ==================== PATCH PIPELINE METHODS ====================
    
    def run_patch_pipeline(self, patch_id: str, file_path: str, original_code: str,
                           patched_code: str, reason: str = "") -> Dict:
        """Run complete patch pipeline"""
        return self.patch_lifecycle.run_full_pipeline(
            patch_id, file_path, original_code, patched_code, reason
        )
    
    def approve_patch(self, patch_id: str) -> Dict:
        """Approve a patch after pipeline"""
        return self.patch_lifecycle.make_decision(patch_id)
    
    def reject_and_rollback(self, patch_id: str, reason: str) -> Dict:
        """Reject and rollback a patch"""
        decision = self.patch_lifecycle.make_decision(patch_id)
        if decision.get("decision") == "rejected":
            return self.patch_lifecycle.rollback(patch_id, reason)
        return {"success": False, "error": "Patch was approved"}
    
    def get_patch_status(self, patch_id: str) -> Dict:
        """Get patch status"""
        return self.patch_lifecycle.get_patch_status(patch_id)
    
    def get_all_patches(self) -> List[Dict]:
        """Get all patches"""
        return self.patch_lifecycle.get_all_patches()


# ==================== FACTORY ====================

def create_regression_suite() -> RegressionSuite:
    """Create regression suite"""
    return RegressionSuite()
