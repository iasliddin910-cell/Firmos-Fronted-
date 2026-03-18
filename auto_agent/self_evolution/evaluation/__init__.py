"""
Evaluation Layer - Clone Evaluation and Benchmarking
====================================================
Bu qatlam clone larni baholaydi va benchmarkdan o'tkazadi.

Ichida:
- replay runner
- benchmark runner
- side-by-side comparison
- trust score engine
"""

import uuid
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import json

from ..data_contracts import (
    EvaluationBundle, CloneRun
)

logger = logging.getLogger(__name__)


class ReplayRunner:
    """
    Replay Runner - Oldingi amallarni qayta ishga tushirish
    Clone ni sinab ko'rish uchun oldingi amallarni takrorlaydi
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.replay_results: dict[str, dict] = {}
        logger.info("🔄 ReplayRunner initialized")
    
    def run_replay(
        self,
        clone_id: str,
        test_cases: list[dict]
    ) -> dict:
        """
        Replay ishga tushirish
        
        Args:
            clone_id: Clone ID
            test_cases: Test holatlari ro'yxati
        
        Returns:
            Replay natijalari
        """
        results = {
            "clone_id": clone_id,
            "run_at": datetime.now().isoformat(),
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "test_results": []
        }
        
        for test in test_cases:
            test_result = {
                "test_name": test.get("name", "unnamed"),
                "passed": True,
                "output": "",
                "error": None,
                "duration": 0.0
            }
            
            # Placeholder - realda bu test ishga tushiriladi
            # Hozircha default qiluvchi natija
            test_result["passed"] = test.get("expected_pass", True)
            
            if test_result["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            results["test_results"].append(test_result)
        
        self.replay_results[clone_id] = results
        
        logger.info(f"🔄 Replay completed for {clone_id}: {results['passed']}/{results['total_tests']} passed")
        
        return results
    
    def get_replay_result(self, clone_id: str) -> Optional[dict]:
        """Replay natijani olish"""
        return self.replay_results.get(clone_id)


class BenchmarkRunner:
    """
    Benchmark Runner - Benchmark ishga tushirish
    Clone ni turli benchmarklardan o'tkazadi
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.benchmark_results: dict[str, dict] = {}
        self.benchmark_suite = self._load_benchmark_suite()
        logger.info("📊 BenchmarkRunner initialized")
    
    def _load_benchmark_suite(self) -> dict:
        """Benchmark suite ni yuklash"""
        return {
            "syntax_check": {
                "name": "Syntax Check",
                "weight": 0.1,
                "threshold": 0.8
            },
            "import_check": {
                "name": "Import Check",
                "weight": 0.1,
                "threshold": 0.8
            },
            "functionality": {
                "name": "Functionality",
                "weight": 0.4,
                "threshold": 0.7
            },
            "performance": {
                "name": "Performance",
                "weight": 0.2,
                "threshold": 0.6
            },
            "regression": {
                "name": "Regression Check",
                "weight": 0.2,
                "threshold": 0.9
            }
        }
    
    def run_benchmarks(
        self,
        clone_id: str,
        custom_benchmarks: Optional[list[dict]] = None
    ) -> dict:
        """
        Benchmarklarni ishga tushirish
        """
        results = {
            "clone_id": clone_id,
            "run_at": datetime.now().isoformat(),
            "benchmarks": {},
            "overall_score": 0.0,
            "passed": False
        }
        
        benchmarks_to_run = custom_benchmarks or list(self.benchmark_suite.keys())
        
        total_weight = 0.0
        weighted_score = 0.0
        
        for bench_key in benchmarks_to_run:
            bench_info = self.benchmark_suite.get(bench_key, {})
            
            # Placeholder - real benchmark ishga tushiriladi
            # Hozircha random ball
            import random
            score = random.uniform(0.7, 1.0)
            
            bench_result = {
                "name": bench_info.get("name", bench_key),
                "score": score,
                "weight": bench_info.get("weight", 0.2),
                "threshold": bench_info.get("threshold", 0.7),
                "passed": score >= bench_info.get("threshold", 0.7)
            }
            
            results["benchmarks"][bench_key] = bench_result
            
            weighted_score += score * bench_result["weight"]
            total_weight += bench_result["weight"]
        
        # Overall score
        results["overall_score"] = weighted_score / total_weight if total_weight > 0 else 0
        
        # Pass check
        results["passed"] = all(
            b["passed"] for b in results["benchmarks"].values()
        )
        
        self.benchmark_results[clone_id] = results
        
        logger.info(f"📊 Benchmarks for {clone_id}: score={results['overall_score']:.2f}, passed={results['passed']}")
        
        return results
    
    def get_benchmark_result(self, clone_id: str) -> Optional[dict]:
        """Benchmark natijani olish"""
        return self.benchmark_results.get(clone_id)


class SideBySideComparator:
    """
    Side-by-Side Comparator - Asl va clone ni solishtirish
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.comparisons: dict[str, dict] = {}
        logger.info("⚖️ SideBySideComparator initialized")
    
    def compare(
        self,
        original_path: str,
        clone_path: str,
        focus_areas: Optional[list[str]] = None
    ) -> dict:
        """
        Original va clone ni solishtirish
        """
        comparison = {
            "original_path": original_path,
            "clone_path": clone_path,
            "compared_at": datetime.now().isoformat(),
            "deltas": {},
            "similarity_score": 0.0
        }
        
        # Focus areas bo'yicha solishtirish
        focus_areas = focus_areas or ["code", "config", "tools"]
        
        total_similarity = 0.0
        area_count = 0
        
        for area in focus_areas:
            # Placeholder - realda bu files ni solishtiradi
            import random
            similarity = random.uniform(0.6, 0.95)
            
            comparison["deltas"][area] = {
                "similarity": similarity,
                "changes_count": int((1 - similarity) * 100),
                "added": int((1 - similarity) * 50),
                "removed": int((1 - similarity) * 30),
                "modified": int((1 - similarity) * 20)
            }
            
            total_similarity += similarity
            area_count += 1
        
        comparison["similarity_score"] = total_similarity / area_count if area_count > 0 else 0
        
        self.comparisons[f"{original_path}_{clone_path}"] = comparison
        
        logger.info(f"⚖️ Comparison: similarity={comparison['similarity_score']:.2f}")
        
        return comparison


class TrustScoreEngine:
    """
    Trust Score Engine - Ishonchlilik balli
    Clone ga ishonchlilik balli beradi
    """
    
    def __init__(self):
        self.trust_factors = {
            "validation_score": 0.25,
            "benchmark_score": 0.25,
            "regression_score": 0.20,
            "complexity_score": 0.15,
            "history_score": 0.15
        }
        logger.info("⭐ TrustScoreEngine initialized")
    
    def calculate_trust_score(
        self,
        validation_result: dict,
        benchmark_result: dict,
        regression_result: Optional[dict] = None,
        complexity: Optional[float] = None,
        history: Optional[dict] = None
    ) -> float:
        """
        Trust score hisoblash
        
        Returns:
            0.0 dan 1.0 gacha ishonchlilik balli
        """
        scores = {}
        
        # 1. Validation score
        validation_pass_rate = validation_result.get("pass_rate", 0.0)
        scores["validation_score"] = validation_pass_rate
        
        # 2. Benchmark score
        benchmark_score = benchmark_result.get("overall_score", 0.0)
        scores["benchmark_score"] = benchmark_score
        
        # 3. Regression score (agar mavjud bo'lsa)
        if regression_result:
            regression_pass_rate = regression_result.get("passed_tests", 0) / max(regression_result.get("total_tests", 1), 1)
            scores["regression_score"] = regression_pass_rate
        else:
            scores["regression_score"] = 0.8  # Default
        
        # 4. Complexity score (past complexity = yuqori trust)
        if complexity is not None:
            scores["complexity_score"] = 1.0 - complexity
        else:
            scores["complexity_score"] = 0.7
        
        # 5. History score (oldingi muvaffaqiyatlar)
        if history:
            success_rate = history.get("success_rate", 0.5)
            scores["history_score"] = success_rate
        else:
            scores["history_score"] = 0.5
        
        # Weighted average
        trust_score = sum(
            scores[key] * self.trust_factors[key]
            for key in self.trust_factors
        )
        
        # 0.0 dan 1.0 gacha cheklash
        trust_score = max(0.0, min(1.0, trust_score))
        
        logger.info(f"⭐ Trust score calculated: {trust_score:.3f}")
        
        return trust_score
    
    def get_trust_level(self, trust_score: float) -> str:
        """
        Trust level ni aniqlash
        
        Returns:
            "low", "medium", "high", "very_high"
        """
        if trust_score >= 0.85:
            return "very_high"
        elif trust_score >= 0.70:
            return "high"
        elif trust_score >= 0.50:
            return "medium"
        else:
            return "low"


class EvaluationLayer:
    """
    Evaluation Layer - To'liq evaluation tizimi
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        
        self.replay_runner = ReplayRunner(workspace_path)
        self.benchmark_runner = BenchmarkRunner(workspace_path)
        self.comparator = SideBySideComparator(workspace_path)
        self.trust_engine = TrustScoreEngine()
        
        logger.info("📈 EvaluationLayer initialized")
    
    def evaluate_clone(
        self,
        clone: CloneRun,
        test_cases: Optional[list[dict]] = None,
        custom_benchmarks: Optional[list[dict]] = None,
        baseline_scores: Optional[dict] = None
    ) -> EvaluationBundle:
        """
        Clone ni to'liq baholash
        
        Args:
            clone: CloneRun obyekti
            test_cases: Test holatlari
            custom_benchmarks: Custom benchmarklar
            baseline_scores: Baseline ballar
        
        Returns:
            EvaluationBundle
        """
        eval_id = f"eval_{str(uuid.uuid4())[:12]}"
        
        # 1. Replay
        replay_results = {}
        if test_cases:
            replay_results = self.replay_runner.run_replay(
                clone.clone_id,
                test_cases
            )
        
        # 2. Benchmarks
        benchmark_results = self.benchmark_runner.run_benchmarks(
            clone.clone_id,
            custom_benchmarks
        )
        
        # 3. Side-by-side comparison (agar kerak bo'lsa)
        behavior_deltas = {}
        if baseline_scores:
            comparison = self.comparator.compare(
                "main",
                clone.clone_id
            )
            behavior_deltas = comparison.get("deltas", {})
        
        # 4. Trust score
        validation_result = clone.validation_status or {"pass_rate": 0.0}
        trust_score = self.trust_engine.calculate_trust_score(
            validation_result=validation_result,
            benchmark_result=benchmark_results,
            regression_result=replay_results
        )
        
        # 5. Regressions
        regressions = []
        if replay_results:
            failed_tests = [
                t["test_name"] for t in replay_results.get("test_results", [])
                if not t["passed"]
            ]
            regressions = failed_tests
        
        # Evaluation bundle yaratish
        bundle = EvaluationBundle(
            id=eval_id,
            candidate_id=clone.candidate_id,
            clone_id=clone.clone_id,
            benchmark_results=benchmark_results,
            replay_results=replay_results,
            behavior_deltas=behavior_deltas,
            regressions=regressions,
            trust_score=trust_score,
            overall_score=benchmark_results.get("overall_score", 0.0)
        )
        
        logger.info(f"📈 Evaluation completed for {clone.clone_id}: trust={trust_score:.3f}")
        
        return bundle
    
    def get_stats(self) -> dict:
        """Evaluation statistikasi"""
        return {
            "replay_results": len(self.replay_runner.replay_results),
            "benchmark_results": len(self.benchmark_runner.benchmark_results),
            "comparisons": len(self.comparator.comparisons)
        }


def create_evaluation_layer(workspace_path: str) -> EvaluationLayer:
    """
    Evaluation Layer yaratish
    """
    return EvaluationLayer(workspace_path)
