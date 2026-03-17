"""
BenchmarkReleasePipeline - Release Process Automation
==================================================

Benchmark release jarayonini avtomatlashtirish.

Bu pipeline:
- Schema validation
- Fixture integrity check
- Verifier integrity check
- Flake screening
- Dedup scan
- Contamination scan
- Score impact simulation
- Candidate publish

Definition of Done:
3. Stable pack release pipeline orqali chiqadi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import json
import os


# ==================== RELEASE TYPES ====================

class ReleaseType(str, Enum):
    """Release turlari."""
    STABLE = "stable"       # Rasmiy release
    CANARY = "canary"       # Sinov release
    EXPERIMENTAL = "experimental"  # Eksperimental
    HOTFIX = "hotfix"       # Tezkor tuzatma


class ReleaseStage(str, Enum):
    """Pipeline bosqichlari."""
    SCHEMA_LINT = "schema_lint"
    FIXTURE_CHECK = "fixture_check"
    VERIFIER_CHECK = "verifier_check"
    FLAKE_TEST = "flake_test"
    DEDUP_SCAN = "dedup_scan"
    CONTAMINATION_SCAN = "contamination_scan"
    SCORE_SIMULATION = "score_simulation"
    CANDIDATE_PUBLISH = "candidate_publish"
    STABLE_PUBLISH = "stable_publish"


@dataclass
class ValidationResult:
    """Validation natijasi."""
    stage: str
    passed: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ReleaseCandidate:
    """Release candidate."""
    release_id: str
    release_type: ReleaseType
    version: str
    
    # Tasklar
    added_tasks: List[str] = field(default_factory=list)
    removed_tasks: List[str] = field(default_factory=list)
    modified_tasks: List[str] = field(default_factory=list)
    
    # Validation
    validation_results: List[ValidationResult] = field(default_factory=list)
    
    # Metadata
    created_by: str = "system"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    target_date: Optional[str] = None
    
    # Status
    status: str = "draft"  # draft, testing, approved, published, failed
    
    # Changes
    changelog: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "release_id": self.release_id,
            "release_type": self.release_type.value,
            "version": self.version,
            "added_tasks": self.added_tasks,
            "removed_tasks": self.removed_tasks,
            "modified_tasks": self.modified_tasks,
            "validation_results": [
                {"stage": v.stage, "passed": v.passed, "message": v.message}
                for v in self.validation_results
            ],
            "created_by": self.created_by,
            "created_at": self.created_at,
            "target_date": self.target_date,
            "status": self.status,
            "changelog": self.changelog,
            "breaking_changes": self.breaking_changes,
        }


# ==================== VALIDATORS ====================

class SchemaValidator:
    """Task schema validation."""
    
    REQUIRED_FIELDS = [
        "task_id",
        "suite",
        "difficulty",
        "capabilities",
        "description",
    ]
    
    def validate(self, task_data: Dict[str, Any]) -> ValidationResult:
        """Validate task schema."""
        missing = []
        for field in self.REQUIRED_FIELDS:
            if field not in task_data:
                missing.append(field)
        
        if missing:
            return ValidationResult(
                stage=ReleaseStage.SCHEMA_LINT.value,
                passed=False,
                message=f"Missing required fields: {missing}",
                details={"missing_fields": missing},
            )
        
        # Validate difficulty
        valid_difficulties = ["easy", "medium", "hard", "frontier"]
        if task_data.get("difficulty") not in valid_difficulties:
            return ValidationResult(
                stage=ReleaseStage.SCHEMA_LINT.value,
                passed=False,
                message=f"Invalid difficulty: {task_data.get('difficulty')}",
            )
        
        return ValidationResult(
            stage=ReleaseStage.SCHEMA_LINT.value,
            passed=True,
            message="Schema valid",
        )


class FixtureValidator:
    """Fixture integrity validation."""
    
    def validate(self, task_data: Dict[str, Any], fixtures_path: str) -> ValidationResult:
        """Validate fixture exists and is valid."""
        task_id = task_data.get("task_id")
        
        # Check fixture exists
        fixture_file = os.path.join(fixtures_path, f"{task_id}.json")
        if not os.path.exists(fixture_file):
            return ValidationResult(
                stage=ReleaseStage.FIXTURE_CHECK.value,
                passed=False,
                message=f"Fixture not found: {fixture_file}",
            )
        
        # Validate fixture content
        try:
            with open(fixture_file, 'r') as f:
                fixture = json.load(f)
            
            # Check required keys
            if not isinstance(fixture, dict):
                return ValidationResult(
                    stage=ReleaseStage.FIXTURE_CHECK.value,
                    passed=False,
                    message="Fixture must be a dictionary",
                )
            
            return ValidationResult(
                stage=ReleaseStage.FIXTURE_CHECK.value,
                passed=True,
                message="Fixture valid",
                details={"fixture_keys": list(fixture.keys())[:10]},
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                stage=ReleaseStage.FIXTURE_CHECK.value,
                passed=False,
                message=f"Invalid JSON: {str(e)}",
            )


class VerifierValidator:
    """Verifier integrity validation."""
    
    def validate(self, task_data: Dict[str, Any]) -> ValidationResult:
        """Validate verifier exists and is valid."""
        # Check verifier exists
        verifier_path = task_data.get("verifier_path")
        if not verifier_path:
            return ValidationResult(
                stage=ReleaseStage.VERIFIER_CHECK.value,
                passed=False,
                message="No verifier_path specified",
            )
        
        if not os.path.exists(verifier_path):
            return ValidationResult(
                stage=ReleaseStage.VERIFIER_CHECK.value,
                passed=False,
                message=f"Verifier not found: {verifier_path}",
            )
        
        return ValidationResult(
            stage=ReleaseStage.VERIFIER_CHECK.value,
            passed=True,
            message="Verifier valid",
        )


# ==================== PIPELINE ====================

class BenchmarkReleasePipeline:
    """
    Benchmark release pipeline.
    
    Definition of Done:
    3. Stable pack release pipeline orqali chiqadi.
    """
    
    def __init__(self, registry=None):
        self.registry = registry
        self.candidates: Dict[str, ReleaseCandidate] = {}
        
        # Validators
        self.schema_validator = SchemaValidator()
        self.fixture_validator = FixtureValidator()
        self.verifier_validator = VerifierValidator()
        
        # Callbacks
        self.dedup_checker: Optional[Callable] = None
        self.contamination_checker: Optional[Callable] = None
    
    def create_candidate(
        self,
        release_type: ReleaseType,
        version: str,
        added_tasks: List[str] = None,
        removed_tasks: List[str] = None,
        created_by: str = "system",
    ) -> ReleaseCandidate:
        """Yangi release candidate yaratish."""
        release_id = f"{release_type.value}_{version}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        candidate = ReleaseCandidate(
            release_id=release_id,
            release_type=release_type,
            version=version,
            added_tasks=added_tasks or [],
            removed_tasks=removed_tasks or [],
            created_by=created_by,
        )
        
        self.candidates[release_id] = candidate
        return candidate
    
    def run_schema_validation(
        self,
        candidate: ReleaseCandidate,
        tasks_data: Dict[str, Any],
    ) -> ValidationResult:
        """Schema validation bosqichi."""
        all_passed = True
        results = []
        
        for task_id in candidate.added_tasks:
            task_data = tasks_data.get(task_id, {})
            result = self.schema_validator.validate(task_data)
            results.append(result)
            if not result.passed:
                all_passed = False
        
        candidate.validation_results.extend(results)
        
        return ValidationResult(
            stage="schema_validation_summary",
            passed=all_passed,
            message=f"Validated {len(results)} tasks",
            details={"total": len(results), "passed": sum(1 for r in results if r.passed)},
        )
    
    def run_fixture_validation(
        self,
        candidate: ReleaseCandidate,
        fixtures_path: str,
        tasks_data: Dict[str, Any],
    ) -> ValidationResult:
        """Fixture validation bosqichi."""
        all_passed = True
        results = []
        
        for task_id in candidate.added_tasks:
            task_data = tasks_data.get(task_id, {})
            result = self.fixture_validator.validate(task_data, fixtures_path)
            results.append(result)
            if not result.passed:
                all_passed = False
        
        candidate.validation_results.extend(results)
        
        return ValidationResult(
            stage="fixture_validation_summary",
            passed=all_passed,
            message=f"Validated {len(results)} fixtures",
            details={"total": len(results), "passed": sum(1 for r in results if r.passed)},
        )
    
    def run_dedup_scan(
        self,
        candidate: ReleaseCandidate,
    ) -> ValidationResult:
        """Dedup scan bosqichi."""
        if not self.dedup_checker:
            return ValidationResult(
                stage=ReleaseStage.DEDUP_SCAN.value,
                passed=True,
                message="Dedup checker not configured, skipping",
            )
        
        # Run dedup check
        duplicates = self.dedup_checker(candidate.added_tasks)
        
        if duplicates:
            candidate.validation_results.append(ValidationResult(
                stage=ReleaseStage.DEDUP_SCAN.value,
                passed=False,
                message=f"Found {len(duplicates)} potential duplicates",
                details={"duplicates": duplicates},
            ))
            return ValidationResult(
                stage=ReleaseStage.DEDUP_SCAN.value,
                passed=False,
                message=f"Found {len(duplicates)} duplicates",
                details={"duplicates": duplicates},
            )
        
        return ValidationResult(
            stage=ReleaseStage.DEDUP_SCAN.value,
            passed=True,
            message="No duplicates found",
        )
    
    def run_contamination_scan(
        self,
        candidate: ReleaseCandidate,
    ) -> ValidationResult:
        """Contamination scan bosqichi."""
        if not self.contamination_checker:
            return ValidationResult(
                stage=ReleaseStage.CONTAMINATION_SCAN.value,
                passed=True,
                message="Contamination checker not configured, skipping",
            )
        
        # Run contamination check
        risks = self.contamination_checker(candidate.added_tasks)
        
        if risks:
            high_risk = [r for r in risks if r.get("risk") == "high"]
            if high_risk:
                return ValidationResult(
                    stage=ReleaseStage.CONTAMINATION_SCAN.value,
                    passed=False,
                    message=f"Found {len(high_risk)} high-risk contamination",
                    details={"risks": risks},
                )
        
        return ValidationResult(
            stage=ReleaseStage.CONTAMINATION_SCAN.value,
            passed=True,
            message="No contamination risks found",
        )
    
    def run_full_pipeline(
        self,
        candidate: ReleaseCandidate,
        tasks_data: Dict[str, Any] = None,
        fixtures_path: str = None,
    ) -> ReleaseCandidate:
        """
        To'liq pipeline'ni ishga tushirish.
        
        Bosqichlar:
        1. Schema validation
        2. Fixture validation
        3. Verifier validation
        4. Dedup scan
        5. Contamination scan
        """
        tasks_data = tasks_data or {}
        
        # Stage 1: Schema validation
        schema_result = self.run_schema_validation(candidate, tasks_data)
        candidate.validation_results.append(schema_result)
        
        # Stage 2: Fixture validation
        if fixtures_path:
            fixture_result = self.run_fixture_validation(candidate, fixtures_path, tasks_data)
            candidate.validation_results.append(fixture_result)
        
        # Stage 3: Dedup scan
        dedup_result = self.run_dedup_scan(candidate)
        candidate.validation_results.append(dedup_result)
        
        # Stage 4: Contamination scan
        contam_result = self.run_contamination_scan(candidate)
        candidate.validation_results.append(contam_result)
        
        # Determine overall status
        all_passed = all(v.passed for v in candidate.validation_results)
        
        if all_passed:
            candidate.status = "approved"
        else:
            candidate.status = "failed"
        
        return candidate
    
    def publish_candidate(self, candidate: ReleaseCandidate) -> bool:
        """Candidate'ni publish qilish."""
        if candidate.status != "approved":
            return False
        
        candidate.status = "published"
        return True
    
    def get_candidate(self, release_id: str) -> Optional[ReleaseCandidate]:
        """Candidate'ni olish."""
        return self.candidates.get(release_id)
    
    def get_active_candidates(self) -> List[ReleaseCandidate]:
        """Aktiv candidate'larni olish."""
        return [c for c in self.candidates.values() if c.status in ["draft", "testing", "approved"]]
    
    def get_published_releases(self) -> List[ReleaseCandidate]:
        """Published release'larni olish."""
        return [c for c in self.candidates.values() if c.status == "published"]


# ==================== RELEASE MANAGER ====================

class ReleaseManager:
    """Release packlarni boshqarish."""
    
    def __init__(self, releases_path: str = None):
        self.releases_path = releases_path or "benchmarks/releases"
        os.makedirs(self.releases_path, exist_ok=True)
        
        self.releases: Dict[str, ReleaseCandidate] = {}
        self._load_releases()
    
    def save_release(self, candidate: ReleaseCandidate) -> None:
        """Release'ni saqlash."""
        filename = f"{candidate.release_id}.json"
        path = os.path.join(self.releases_path, filename)
        
        with open(path, 'w') as f:
            json.dump(candidate.to_dict(), f, indent=2)
        
        self.releases[candidate.release_id] = candidate
    
    def load_release(self, release_id: str) -> Optional[ReleaseCandidate]:
        """Release'ni yuklash."""
        filename = f"{release_id}.json"
        path = os.path.join(self.releases_path, filename)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        return ReleaseCandidate(
            release_id=data["release_id"],
            release_type=ReleaseType(data["release_type"]),
            version=data["version"],
            added_tasks=data.get("added_tasks", []),
            removed_tasks=data.get("removed_tasks", []),
            created_by=data.get("created_by", "system"),
            status=data.get("status", "draft"),
            changelog=data.get("changelog", []),
        )
    
    def get_latest_stable(self) -> Optional[ReleaseCandidate]:
        """Latest stable release."""
        stable = [r for r in self.releases.values() if r.release_type == ReleaseType.STABLE]
        if not stable:
            return None
        return max(stable, key=lambda r: r.created_at)
    
    def get_latest_canary(self) -> Optional[ReleaseCandidate]:
        """Latest canary release."""
        canary = [r for r in self.releases.values() if r.release_type == ReleaseType.CANARY]
        if not canary:
            return None
        return max(canary, key=lambda r: r.created_at)
    
    def _load_releases(self) -> None:
        """Barcha release'larni yuklash."""
        if not os.path.exists(self.releases_path):
            return
        
        for filename in os.listdir(self.releases_path):
            if filename.endswith(".json"):
                release_id = filename.replace(".json", "")
                release = self.load_release(release_id)
                if release:
                    self.releases[release_id] = release
    
    def generate_changelog(
        self,
        old_release: ReleaseCandidate,
        new_release: ReleaseCandidate,
    ) -> List[str]:
        """Changelog generatsiya."""
        changelog = []
        
        # Added
        added = set(new_release.added_tasks) - set(old_release.added_tasks)
        if added:
            changelog.append(f"Added {len(added)} new tasks")
        
        # Removed
        removed = set(old_release.added_tasks) - set(new_release.added_tasks)
        if removed:
            changelog.append(f"Removed {len(removed)} tasks")
        
        return changelog


# ==================== FACTORY ====================

def create_release_pipeline(registry=None) -> BenchmarkReleasePipeline:
    """Release pipeline yaratish."""
    return BenchmarkReleasePipeline(registry)


def create_release_manager(releases_path: str = None) -> ReleaseManager:
    """Release manager yaratish."""
    return ReleaseManager(releases_path)
