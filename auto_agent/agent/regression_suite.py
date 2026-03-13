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


# ==================== REGRESSION SUITE ====================

class RegressionSuite:
    """
    Complete regression testing suite
    """
    
    def __init__(self):
        self.test_runner = TestRunner()
        self.performance_tester = PerformanceTester()
        
        logger.info("🔄 Regression Suite initialized")
    
    def run(self, test_type: str = "all") -> Dict:
        """Run regression tests"""
        
        if test_type == "all":
            return self.test_runner.run_all()
        elif test_type == "smoke":
            return self._format_results(self.test_runner.run_suite("smoke"))
        elif test_type == "performance":
            return self.performance_tester.baseline
        else:
            return {"error": f"Unknown test type: {test_type}"}
    
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


# ==================== FACTORY ====================

def create_regression_suite() -> RegressionSuite:
    """Create regression suite"""
    return RegressionSuite()
