"""
================================================================================
LAYER 8: CLONE ARTIFACT STORE
================================================================================
Har clone nima qilganini saqlashi kerak.

Saqlanadigan narsalar:
- patch diff
- changed files
- logs
- test results
- benchmark additions
- screenshots
- traces
- generated docs
- tool manifests
- errors
- metrics

Nega kerak:

Keyin report system va approval system aynan shu artifacts bilan ishlaydi.

Clone natijasi ephemeral bo'lsa:
- isbot yo'q
- debug qiyin
- compare qiyin
- rollback reja noaniq
================================================================================
"""
import os
import sys
import json
import logging
import time
import shutil
import hashlib
import subprocess
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum

from .core_types import CloneArtifact, CloneLineage
from .clone_factory import CloneFactory

logger = logging.getLogger(__name__)


# ================================================================================
# ARTIFACT STORE
# ================================================================================

class ArtifactStore:
    """
    Artifact Store - Clone artifacts saqlash
    
    Bu class:
    1. Artifact larni saqlaydi
    2. Artifact larni indekslaydi
    3. Artifact larni qidirish mumkin qiladi
    4. Artifact larni tozalaydi (TTL bilan)
    """
    
    def __init__(self, factory: CloneFactory):
        self.factory = factory
        
        # Artifact storage
        self.artifacts: Dict[str, CloneArtifact] = {}
        self.artifact_index: Dict[str, List[str]] = defaultdict(list)  # clone_id -> artifact_ids
        
        # Artifact types
        self.artifact_types = [
            "patch_diff",
            "changed_file",
            "log",
            "test_result",
            "benchmark_result",
            "screenshot",
            "trace",
            "generated_doc",
            "tool_manifest",
            "error",
            "metric",
            "report"
        ]
        
        logger.info("📦 Artifact Store initialized")
    
    def store_artifact(self, 
                      clone_id: str,
                      artifact_type: str,
                      content: Any,
                      file_path: Optional[str] = None) -> CloneArtifact:
        """
        Artifact saqlash
        
        Args:
            clone_id: Clone ID
            artifact_type: Artifact turi
            content: Content
            file_path: File path (ixtiyoriy)
        
        Returns:
            CloneArtifact: Saqlangan artifact
        """
        artifact_id = f"artifact_{clone_id}_{artifact_type}_{int(time.time() * 1000)}"
        
        # Calculate size
        if isinstance(content, str):
            size = len(content.encode('utf-8'))
        elif isinstance(content, bytes):
            size = len(content)
        else:
            size = len(str(content))
        
        # Determine mime type
        mime_type = self._get_mime_type(artifact_type, file_path)
        
        artifact = CloneArtifact(
            artifact_id=artifact_id,
            clone_id=clone_id,
            artifact_type=artifact_type,
            content=content,
            file_path=file_path,
            size=size,
            mime_type=mime_type
        )
        
        # Save to file if large
        if size > 1024 * 1024:  # > 1MB
            self._save_to_file(artifact)
            artifact.content = None  # Clear from memory
        
        # Store
        self.artifacts[artifact_id] = artifact
        self.artifact_index[clone_id].append(artifact_id)
        
        logger.info(f"💾 Artifact stored: {artifact_id} ({artifact_type}, {size} bytes)")
        
        return artifact
    
    def _get_mime_type(self, artifact_type: str, file_path: Optional[str]) -> str:
        """MIME type aniqlash"""
        if file_path:
            ext = Path(file_path).suffix.lower()
            mime_map = {
                ".json": "application/json",
                ".py": "text/x-python",
                ".txt": "text/plain",
                ".md": "text/markdown",
                ".log": "text/plain",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".html": "text/html",
            }
            if ext in mime_map:
                return mime_map[ext]
        
        # Default by type
        type_mime = {
            "patch_diff": "text/plain",
            "changed_file": "text/plain",
            "log": "text/plain",
            "test_result": "application/json",
            "benchmark_result": "application/json",
            "screenshot": "image/png",
            "trace": "application/json",
            "generated_doc": "text/markdown",
            "tool_manifest": "application/json",
            "error": "text/plain",
            "metric": "application/json",
            "report": "application/json"
        }
        
        return type_mime.get(artifact_type, "application/octet-stream")
    
    def _save_to_file(self, artifact: CloneArtifact):
        """Katty file larni file ga saqlash"""
        clone_dir = self.factory.get_clone_artifacts(artifact.clone_id)
        if not clone_dir:
            return
        
        try:
            file_name = f"{artifact.artifact_id}{Path(artifact.file_path or '').suffix}"
            file_path = clone_dir / file_name
            
            with open(file_path, 'wb') as f:
                if isinstance(artifact.content, str):
                    f.write(artifact.content.encode('utf-8'))
                elif isinstance(artifact.content, bytes):
                    f.write(artifact.content)
                else:
                    f.write(str(artifact.content).encode('utf-8'))
            
            artifact.file_path = str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save artifact to file: {e}")
    
    def get_artifact(self, artifact_id: str) -> Optional[CloneArtifact]:
        """Artifact olish"""
        return self.artifacts.get(artifact_id)
    
    def get_artifacts_for_clone(self, clone_id: str) -> List[CloneArtifact]:
        """Clone uchun artifact larni olish"""
        artifact_ids = self.artifact_index.get(clone_id, [])
        return [self.artifacts[aid] for aid in artifact_ids if aid in self.artifacts]
    
    def get_artifacts_by_type(self, clone_id: str, artifact_type: str) -> List[CloneArtifact]:
        """Clone va type bo'yicha artifact larni olish"""
        artifacts = self.get_artifacts_for_clone(clone_id)
        return [a for a in artifacts if a.artifact_type == artifact_type]
    
    def search_artifacts(self, 
                       clone_id: Optional[str] = None,
                       artifact_type: Optional[str] = None,
                       start_time: Optional[float] = None) -> List[CloneArtifact]:
        """Artifact larni qidirish"""
        results = []
        
        for artifact in self.artifacts.values():
            # Filter by clone_id
            if clone_id and artifact.clone_id != clone_id:
                continue
            
            # Filter by type
            if artifact_type and artifact.artifact_type != artifact_type:
                continue
            
            # Filter by time
            if start_time and artifact.created_at < start_time:
                continue
            
            results.append(artifact)
        
        return results
    
    def delete_artifacts_for_clone(self, clone_id: str) -> int:
        """Clone uchun artifact larni o'chirish"""
        artifact_ids = self.artifact_index.get(clone_id, [])
        
        for aid in artifact_ids:
            artifact = self.artifacts.pop(aid, None)
            
            # Delete file if exists
            if artifact and artifact.file_path:
                try:
                    Path(artifact.file_path).unlink()
                except:
                    pass
        
        self.artifact_index.pop(clone_id, None)
        
        logger.info(f"🗑️ Deleted {len(artifact_ids)} artifacts for clone: {clone_id}")
        
        return len(artifact_ids)
    
    def get_artifact_stats(self) -> Dict:
        """Artifact statistics"""
        by_type = defaultdict(int)
        total_size = 0
        
        for artifact in self.artifacts.values():
            by_type[artifact.artifact_type] += 1
            total_size += artifact.size
        
        return {
            "total_artifacts": len(self.artifacts),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": dict(by_type),
            "clones": len(self.artifact_index)
        }


# ================================================================================
# LINEAGE REGISTRY
# ================================================================================

class LineageRegistry:
    """
    Lineage Registry - Clone'lar shajarasi
    
    Har clone bilishi kerak:
    - kimdan tug'ilgan
    - qaysi signal sabab bo'lgan
    - qaysi parent clone'dan chiqqan
    - qaysi benchmarkga ta'sir qilgan
    - merge bo'lganmi yo'qmi
    - forkka aylanganmi yo'qmi
    """
    
    def __init__(self):
        self.lineages: Dict[str, CloneLineage] = {}
        self.lineage_index: Dict[str, List[str]] = defaultdict(list)  # root -> lineage_ids
        
        logger.info("🌳 Lineage Registry initialized")
    
    def register_candidate(self, candidate_info: Dict) -> CloneLineage:
        """
        Clone lineage ro'yxatga olish
        
        Args:
            candidate_info: Candidate ma'lumotlari
        
        Returns:
            CloneLineage: Lineage
        """
        lineage_id = f"lineage_{candidate_info.get('clone_id', 'unknown')}_{int(time.time() * 1000)}"
        
        lineage = CloneLineage(
            lineage_id=lineage_id,
            clone_id=candidate_info.get("clone_id", ""),
            parent_clone_id=candidate_info.get("parent_clone_id"),
            root_clone_id=candidate_info.get("root_clone_id"),
            signal_reason=candidate_info.get("reason", ""),
            benchmark_affected=candidate_info.get("benchmark_affected"),
            merged=candidate_info.get("merged", False),
            rejected=candidate_info.get("rejected", False),
            forked=candidate_info.get("forked", False),
            forked_to=candidate_info.get("forked_to"),
            promoted_at=candidate_info.get("promoted_at")
        )
        
        self.lineages[lineage_id] = lineage
        
        # Update index
        root = lineage.root_clone_id or lineage.clone_id
        self.lineage_index[root].append(lineage_id)
        
        logger.info(f"🌳 Lineage registered: {lineage_id}")
        
        return lineage
    
    def get_lineage(self, lineage_id: str) -> Optional[CloneLineage]:
        """Lineage olish"""
        return self.lineages.get(lineage_id)
    
    def get_lineage_for_clone(self, clone_id: str) -> Optional[CloneLineage]:
        """Clone uchun lineage olish"""
        for lineage in self.lineages.values():
            if lineage.clone_id == clone_id:
                return lineage
        return None
    
    def get_descendants(self, root_clone_id: str) -> List[CloneLineage]:
        """Clone ning vorislarini olish"""
        lineage_ids = self.lineage_index.get(root_clone_id, [])
        return [self.lineages[lid] for lid in lineage_ids if lid in self.lineages]
    
    def mark_promoted(self, clone_id: str) -> bool:
        """Clone ni promoted deb belgilash"""
        lineage = self.get_lineage_for_clone(clone_id)
        
        if lineage:
            lineage.merged = True
            lineage.promoted_at = time.time()
            logger.info(f"🌟 Clone {clone_id} marked as promoted")
            return True
        
        return False
    
    def mark_rejected(self, clone_id: str) -> bool:
        """Clone ni rejected deb belgilash"""
        lineage = self.get_lineage_for_clone(clone_id)
        
        if lineage:
            lineage.rejected = True
            logger.info(f"❌ Clone {clone_id} marked as rejected")
            return True
        
        return False
    
    def mark_forked(self, clone_id: str, forked_to: str) -> bool:
        """Clone ni forked deb belgilash"""
        lineage = self.get_lineage_for_clone(clone_id)
        
        if lineage:
            lineage.forked = True
            lineage.forked_to = forked_to
            logger.info(f"🍴 Clone {clone_id} forked to {forked_to}")
            return True
        
        return False
    
    def get_evolution_tree(self, root_clone_id: str) -> Dict:
        """
        Evolution tree olish
        
        Bu world-class boshqaruv beradi:
        - original
        - clone A
        - clone A1
        - clone A2
        - promoted branch
        - rejected branch
        """
        root_lineage = self.get_lineage_for_clone(root_clone_id)
        
        if not root_lineage:
            return {"error": "Root not found"}
        
        tree = {
            "root": root_clone_id,
            "branches": []
        }
        
        # Get all descendants
        descendants = self.get_descendants(root_clone_id)
        
        # Build tree structure
        for desc in descendants:
            branch = {
                "clone_id": desc.clone_id,
                "reason": desc.signal_reason,
                "status": "merged" if desc.merged else ("rejected" if desc.rejected else "active"),
                "promoted_at": desc.promoted_at,
                "children": []
            }
            
            # Find children
            for child in descendants:
                if child.parent_clone_id == desc.clone_id:
                    branch["children"].append(child.clone_id)
            
            tree["branches"].append(branch)
        
        return tree
    
    def get_statistics(self) -> Dict:
        """Lineage statistics"""
        total = len(self.lineages)
        merged = sum(1 for l in self.lineages.values() if l.merged)
        rejected = sum(1 for l in self.lineages.values() if l.rejected)
        forked = sum(1 for l in self.lineages.values() if l.forked)
        
        return {
            "total_lineages": total,
            "merged": merged,
            "rejected": rejected,
            "forked": forked,
            "active": total - merged - rejected - forked
        }


# ================================================================================
# REPORT GENERATOR
# ================================================================================

class ReportGenerator:
    """
    Report Generator - Clone natijalari uchun report
    """
    
    def __init__(self, artifact_store: ArtifactStore, lineage_registry: LineageRegistry):
        self.artifact_store = artifact_store
        self.lineage_registry = lineage_registry
        
        logger.info("📋 Report Generator initialized")
    
    def generate_clone_report(self, clone_id: str) -> Dict:
        """
        Clone uchun report yaratish
        
        Args:
            clone_id: Clone ID
        
        Returns:
            Dict: Report
        """
        # Get artifacts
        artifacts = self.artifact_store.get_artifacts_for_clone(clone_id)
        
        # Get lineage
        lineage = self.lineage_registry.get_lineage_for_clone(clone_id)
        
        # Build report
        report = {
            "clone_id": clone_id,
            "generated_at": time.time(),
            "lineage": lineage.to_dict() if lineage else None,
            "artifacts_summary": self._summarize_artifacts(artifacts),
            "changes": self._get_changes(artifacts),
            "tests": self._get_test_results(artifacts),
            "benchmarks": self._get_benchmark_results(artifacts),
            "errors": self._get_errors(artifacts),
            "metrics": self._get_metrics(artifacts)
        }
        
        return report
    
    def _summarize_artifacts(self, artifacts: List[CloneArtifact]) -> Dict:
        """Artifact larni xulosa qilish"""
        by_type = defaultdict(int)
        total_size = 0
        
        for a in artifacts:
            by_type[a.artifact_type] += 1
            total_size += a.size
        
        return {
            "total": len(artifacts),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": dict(by_type)
        }
    
    def _get_changes(self, artifacts: List[CloneArtifact]) -> List[Dict]:
        """O'zgarishlarni olish"""
        changes = []
        
        for a in artifacts:
            if a.artifact_type in ["patch_diff", "changed_file"]:
                changes.append({
                    "artifact_id": a.artifact_id,
                    "type": a.artifact_type,
                    "file": a.file_path,
                    "size": a.size,
                    "created_at": a.created_at
                })
        
        return changes
    
    def _get_test_results(self, artifacts: List[CloneArtifact]) -> Dict:
        """Test natijalarini olish"""
        for a in artifacts:
            if a.artifact_type == "test_result":
                try:
                    return json.loads(a.content) if a.content else {}
                except:
                    pass
        
        return {}
    
    def _get_benchmark_results(self, artifacts: List[CloneArtifact]) -> Dict:
        """Benchmark natijalarini olish"""
        results = []
        
        for a in artifacts:
            if a.artifact_type == "benchmark_result":
                try:
                    results.append(json.loads(a.content) if a.content else {})
                except:
                    pass
        
        return {"benchmarks": results}
    
    def _get_errors(self, artifacts: List[CloneArtifact]) -> List[str]:
        """Xatolarni olish"""
        errors = []
        
        for a in artifacts:
            if a.artifact_type == "error":
                errors.append(str(a.content))
        
        return errors
    
    def _get_metrics(self, artifacts: List[CloneArtifact]) -> Dict:
        """Metriklarni olish"""
        metrics = {}
        
        for a in artifacts:
            if a.artifact_type == "metric":
                try:
                    metrics.update(json.loads(a.content) if a.content else {})
                except:
                    pass
        
        return metrics
    
    def generate_executive_summary(self) -> str:
        """
        Executive summary yaratish
        
        Returns:
            str: Summary text
        """
        artifact_stats = self.artifact_store.get_artifact_stats()
        lineage_stats = self.lineage_registry.get_statistics()
        
        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║          SELF-CLONE IMPROVEMENT SYSTEM REPORT              ║
╠══════════════════════════════════════════════════════════════╣
║  ARTIFACTS                                                 ║
║  - Total: {artifact_stats['total_artifacts']:>6}                                          ║
║  - Size:  {artifact_stats['total_size_mb']:>6} MB                                       ║
║                                                              ║
║  LINEAGE                                                    ║
║  - Total: {lineage_stats['total_lineages']:>6}                                          ║
║  - Merged:   {lineage_stats['merged']:>4}                                        ║
║  - Rejected: {lineage_stats['rejected']:>4}                                        ║
║  - Forked:   {lineage_stats['forked']:>4}                                        ║
║  - Active:   {lineage_stats['active']:>4}                                        ║
╚══════════════════════════════════════════════════════════════╝
"""
        return summary


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_artifact_store(factory: CloneFactory) -> ArtifactStore:
    """Artifact Store yaratish"""
    return ArtifactStore(factory)


def create_lineage_registry() -> LineageRegistry:
    """Lineage Registry yaratish"""
    return LineageRegistry()


def create_report_generator(artifact_store: ArtifactStore, 
                          lineage_registry: LineageRegistry) -> ReportGenerator:
    """Report Generator yaratish"""
    return ReportGenerator(artifact_store, lineage_registry)
