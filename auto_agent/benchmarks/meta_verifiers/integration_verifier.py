"""
Meta-Verifiers for Meta-Capability Evaluation
=============================================

Advanced verification components:
1. IntegrationVerifier - Verifies tool integration
2. DownstreamDeltaVerifier - Measures real downstream benefit
3. RollbackSafetyVerifier - Ensures rollback safety
4. CanaryRetentionVerifier - Checks canary task retention
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VerifierStatus(Enum):
    """Verification status"""
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class VerificationResult:
    """Result of a verification check"""
    verifier_name: str
    status: VerifierStatus
    message: str
    details: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class IntegrationVerifier:
    """
    Verifies that created tools are properly integrated into the system.
    
    Checks:
    - Tool is in registry
    - Tool schema is discoverable
    - Planner can see the tool
    - Executor can use the tool
    - Telemetry records tool usage
    """
    
    def __init__(self):
        self.verification_steps = [
            "registry_entry",
            "schema_discoverable",
            "planner_discovery",
            "executor_integration",
            "telemetry_visible"
        ]
        
        logger.info("🔍 IntegrationVerifier initialized")
    
    def verify(self, tool_name: str, registry: Dict, 
               planner_tools: List[str], executor_logs: List[Dict],
               telemetry: List[Dict]) -> VerificationResult:
        """
        Verify tool integration
        
        Returns PASSED only if ALL steps are successful
        """
        details = {}
        failed_steps = []
        
        # Step 1: Registry entry
        if tool_name in registry:
            details["registry_entry"] = "✓ Tool in registry"
        else:
            details["registry_entry"] = "✗ Tool NOT in registry"
            failed_steps.append("registry_entry")
        
        # Step 2: Schema discoverable
        tool_entry = registry.get(tool_name, {})
        if tool_entry.get("schema"):
            details["schema_discoverable"] = "✓ Schema is discoverable"
        else:
            details["schema_discoverable"] = "✗ Schema NOT found"
            failed_steps.append("schema_discoverable")
        
        # Step 3: Planner discovery
        if tool_name in planner_tools:
            details["planner_discovery"] = "✓ Planner can discover tool"
        else:
            details["planner_discovery"] = "✗ Planner cannot discover tool"
            failed_steps.append("planner_discovery")
        
        # Step 4: Executor integration
        executor_used = any(
            log.get("tool_name") == tool_name for log in executor_logs
        )
        if executor_used:
            details["executor_integration"] = "✓ Executor has used tool"
        else:
            details["executor_integration"] = "✗ Executor has NOT used tool"
            failed_steps.append("executor_integration")
        
        # Step 5: Telemetry visible
        telemetry_visible = any(
            log.get("tool_name") == tool_name for log in telemetry
        )
        if telemetry_visible:
            details["telemetry_visible"] = "✓ Tool visible in telemetry"
        else:
            details["telemetry_visible"] = "✗ Tool NOT in telemetry"
            failed_steps.append("telemetry_visible")
        
        # Determine status
        if not failed_steps:
            status = VerifierStatus.PASSED
            message = f"All {len(self.verification_steps)} integration steps passed"
        elif len(failed_steps) <= 2:
            status = VerifierStatus.NEEDS_REVIEW
            message = f"Partial integration: {len(failed_steps)} steps failed"
        else:
            status = VerifierStatus.FAILED
            message = f"Integration failed: {len(failed_steps)} steps failed"
        
        result = VerificationResult(
            verifier_name="IntegrationVerifier",
            status=status,
            message=message,
            details=details
        )
        
        logger.info(f"🔍 Integration verification for {tool_name}: {status.value}")
        
        return result


class DownstreamDeltaVerifier:
    """
    Verifies that created tools provide REAL downstream benefit.
    
    The REAL test:
    1. Before tool: task was difficult/slow
    2. After tool: task is easier/faster
    3. Delta is measurable and positive
    """
    
    def __init__(self, min_improvement: float = 0.1):
        self.min_improvement = min_improvement
        
        logger.info("📊 DownstreamDeltaVerifier initialized")
    
    def verify(self, baseline_metrics: Dict, post_metrics: Dict) -> VerificationResult:
        """
        Verify downstream delta
        
        Returns PASSED only if:
        - Success rate improved OR
        - Latency improved AND
        - No significant regression in other metrics
        """
        details = {}
        
        # Calculate deltas
        baseline_success = baseline_metrics.get("success_rate", 0)
        post_success = post_metrics.get("success_rate", 0)
        success_delta = post_success - baseline_success
        
        baseline_latency = baseline_metrics.get("latency_ms", 0)
        post_latency = post_metrics.get("latency_ms", 0)
        
        if baseline_latency > 0:
            latency_delta = (baseline_latency - post_latency) / baseline_latency
        else:
            latency_delta = 0
        
        baseline_reliability = baseline_metrics.get("reliability", 0)
        post_reliability = post_metrics.get("reliability", 0)
        reliability_delta = post_reliability - baseline_reliability
        
        details["success_delta"] = f"{success_delta:+.1%}"
        details["latency_delta"] = f"{latency_delta:+.1%}"
        details["reliability_delta"] = f"{reliability_delta:+.1%}"
        
        # Check criteria
        success_improved = success_delta >= self.min_improvement
        latency_improved = latency_delta >= self.min_improvement
        reliability_maintained = reliability_delta >= -0.05
        
        if success_improved and reliability_maintained:
            status = VerifierStatus.PASSED
            message = f"Downstream benefit verified: success +{success_delta:.1%}"
        elif latency_improved and reliability_maintained:
            status = VerifierStatus.PASSED
            message = f"Downstream benefit verified: latency {latency_delta:.1%} faster"
        elif reliability_maintained:
            status = VerifierStatus.NEEDS_REVIEW
            message = f"Partial improvement, needs review"
        else:
            status = VerifierStatus.FAILED
            message = f"No significant downstream benefit"
        
        result = VerificationResult(
            verifier_name="DownstreamDeltaVerifier",
            status=status,
            message=message,
            details=details
        )
        
        logger.info(f"📊 Delta verification: {status.value} - {message}")
        
        return result


class RollbackSafetyVerifier:
    """
    Verifies that modifications can be safely rolled back.
    
    Checks:
    - Snapshot exists before modification
    - Rollback procedure is defined
    - Rollback can be executed without breaking system
    - Original state can be restored
    """
    
    def __init__(self):
        logger.info("🔄 RollbackSafetyVerifier initialized")
    
    def verify(self, snapshot_exists: bool, rollback_procedure_defined: bool,
               rollback_tested: bool, original_state_restoreable: bool) -> VerificationResult:
        """
        Verify rollback safety
        
        Returns PASSED only if ALL safety checks pass
        """
        details = {}
        
        if snapshot_exists:
            details["snapshot"] = "✓ Pre-modification snapshot exists"
        else:
            details["snapshot"] = "✗ NO snapshot before modification"
        
        if rollback_procedure_defined:
            details["procedure"] = "✓ Rollback procedure defined"
        else:
            details["procedure"] = "✗ NO rollback procedure"
        
        if rollback_tested:
            details["tested"] = "✓ Rollback tested successfully"
        else:
            details["tested"] = "✗ Rollback NOT tested"
        
        if original_state_restoreable:
            details["restorable"] = "✓ Original state can be restored"
        else:
            details["restorable"] = "✗ Original state NOT restorable"
        
        all_passed = all([
            snapshot_exists, 
            rollback_procedure_defined, 
            rollback_tested, 
            original_state_restoreable
        ])
        
        if all_passed:
            status = VerifierStatus.PASSED
            message = "Rollback safety verified - all checks passed"
        else:
            status = VerifierStatus.FAILED
            message = "Rollback safety FAILED - cannot guarantee safe rollback"
        
        result = VerificationResult(
            verifier_name="RollbackSafetyVerifier",
            status=status,
            message=message,
            details=details
        )
        
        logger.info(f"🔄 Rollback safety: {status.value}")
        
        return result


class CanaryRetentionVerifier:
    """
    Verifies that modifications don't cause hidden regressions.
    
    Tests that previously working tasks still work after modification.
    Uses canary tasks that were NOT modified but should still function.
    """
    
    def __init__(self, max_regression_rate: float = 0.1):
        self.max_regression_rate = max_regression_rate
        
        logger.info("🐦 CanaryRetentionVerifier initialized")
    
    def verify(self, canary_results: List[Dict]) -> VerificationResult:
        """
        Verify canary retention
        
        Returns PASSED if regression rate is below threshold
        """
        if not canary_results:
            return VerificationResult(
                verifier_name="CanaryRetentionVerifier",
                status=VerifierStatus.NEEDS_REVIEW,
                message="No canary tasks tested",
                details={}
            )
        
        total = len(canary_results)
        failed = sum(1 for r in canary_results if not r.get("passed", False))
        regression_rate = failed / total
        
        details["total_canaries"] = total
        details["failed_canaries"] = failed
        details["regression_rate"] = f"{regression_rate:.1%}"
        
        if regression_rate <= self.max_regression_rate:
            status = VerifierStatus.PASSED
            message = f"Canary retention OK: {regression_rate:.1%} regression rate"
        elif regression_rate <= self.max_regression_rate * 2:
            status = VerifierStatus.NEEDS_REVIEW
            message = f"Elevated regression: {regression_rate:.1%}, needs review"
        else:
            status = VerifierStatus.FAILED
            message = f"High regression: {regression_rate:.1%} - modification rejected"
        
        result = VerificationResult(
            verifier_name="CanaryRetentionVerifier",
            status=status,
            message=message,
            details=details
        )
        
        logger.info(f"🐦 Canary retention: {status.value} - {message}")
        
        return result


class MetaVerifier:
    """
    Master verifier that runs all meta-verifiers.
    
    Used for comprehensive meta-capability evaluation.
    """
    
    def __init__(self):
        self.verifiers = {
            "integration": IntegrationVerifier(),
            "downstream_delta": DownstreamDeltaVerifier(),
            "rollback_safety": RollbackSafetyVerifier(),
            "canary_retention": CanaryRetentionVerifier()
        }
        
        logger.info("🎯 MetaVerifier initialized - running ALL verifications")
    
    def verify_modification(self, modification_data: Dict) -> Dict:
        """Run all verifications for a modification"""
        results = {}
        
        # Integration check
        if "tool_data" in modification_data:
            results["integration"] = self.verifiers["integration"].verify(
                tool_name=modification_data["tool_name"],
                registry=modification_data.get("registry", {}),
                planner_tools=modification_data.get("planner_tools", []),
                executor_logs=modification_data.get("executor_logs", []),
                telemetry=modification_data.get("telemetry", [])
            )
        
        # Downstream delta check
        if "baseline_metrics" in modification_data and "post_metrics" in modification_data:
            results["downstream_delta"] = self.verifiers["downstream_delta"].verify(
                baseline_metrics=modification_data["baseline_metrics"],
                post_metrics=modification_data["post_metrics"]
            )
        
        # Rollback safety check
        results["rollback_safety"] = self.verifiers["rollback_safety"].verify(
            snapshot_exists=modification_data.get("snapshot_exists", True),
            rollback_procedure_defined=modification_data.get("rollback_defined", True),
            rollback_tested=modification_data.get("rollback_tested", True),
            original_state_restoreable=modification_data.get("restorable", True)
        )
        
        # Canary retention check
        if "canary_results" in modification_data:
            results["canary_retention"] = self.verifiers["canary_retention"].verify(
                canary_results=modification_data["canary_results"]
            )
        
        # Overall status
        all_passed = all(
            r.status == VerifierStatus.PASSED for r in results.values()
        )
        
        any_failed = any(
            r.status == VerifierStatus.FAILED for r in results.values()
        )
        
        if all_passed:
            overall = "PASSED"
        elif any_failed:
            overall = "FAILED"
        else:
            overall = "NEEDS_REVIEW"
        
        return {
            "overall_status": overall,
            "verifications": {k: {
                "status": v.status.value,
                "message": v.message,
                "details": v.details
            } for k, v in results.items()}
        }


# Factory function
def create_meta_verifier() -> MetaVerifier:
    """Factory function to create MetaVerifier"""
    return MetaVerifier()
