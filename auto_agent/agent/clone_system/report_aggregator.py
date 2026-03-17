"""
================================================================================
1. REPORT AGGREGATOR
================================================================================
Bu clone'dan chiqqan barcha artifactlarni yig'adi.

Yig'iladigan narsalar:
- patch diff
- changed files
- test natijalari
- benchmark natijalari
- new tool manifests
- screenshots
- logs
- errors
- trace summaries
- research signals
- planning notes
================================================================================
"""
import os
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict

from .reporting_types import EvidenceItem
from .artifact_store import ArtifactStore

logger = logging.getLogger(__name__)


class ReportAggregator:
    """
    Report Aggregator - Artifact yig'ish
    
    Bu modul clone'dan chiqqan barcha artifactlarni yig'adi
    va ularni to'liq report uchun tayyorlaydi.
    """
    
    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store
        
        logger.info("📦 Report Aggregator initialized")
    
    def aggregate_for_dossier(self, clone_id: str) -> Dict[str, Any]:
        """
        Clone uchun barcha artifactlarni yig'ish
        
        Args:
            clone_id: Clone ID
        
        Returns:
            Dict: Yig'ilgan artifactlar
        """
        aggregated = {
            "clone_id": clone_id,
            "aggregated_at": time.time(),
            "artifacts": {},
            "summary": {}
        }
        
        try:
            # Get all artifacts for this clone
            artifacts = self.artifact_store.get_artifacts_for_clone(clone_id)
            
            if not artifacts:
                logger.warning(f"No artifacts found for clone: {clone_id}")
                return aggregated
            
            # Group by type
            by_type = defaultdict(list)
            
            for artifact in artifacts:
                by_type[artifact.artifact_type].append({
                    "artifact_id": artifact.artifact_id,
                    "file_path": artifact.file_path,
                    "size": artifact.size,
                    "created_at": artifact.created_at,
                    "content_preview": self._get_preview(artifact)
                })
            
            aggregated["artifacts"] = dict(by_type)
            
            # Summary
            aggregated["summary"] = {
                "total_artifacts": len(artifacts),
                "types": list(by_type.keys()),
                "total_size": sum(a.size for a in artifacts)
            }
            
            logger.info(f"✅ Aggregated {len(artifacts)} artifacts for clone: {clone_id}")
            
        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            aggregated["error"] = str(e)
        
        return aggregated
    
    def _get_preview(self, artifact) -> str:
        """Artifact dan preview olish"""
        if not artifact.content:
            return "[Large file - see artifact]"
        
        content = str(artifact.content)
        
        # First 200 chars
        if len(content) > 200:
            return content[:200] + "..."
        
        return content
    
    def gather_evidence(self, clone_id: str) -> List[EvidenceItem]:
        """
        Evidence items yig'ish
        
        Args:
            clone_id: Clone ID
        
        Returns:
            List[EvidenceItem]: Evidence items
        """
        evidence = []
        
        try:
            # Get all artifacts
            artifacts = self.artifact_store.get_artifacts_for_clone(clone_id)
            
            for artifact in artifacts:
                # Determine evidence type
                evidence_type = self._classify_artifact(artifact.artifact_type)
                
                if evidence_type:
                    # Calculate hash for integrity
                    content_hash = ""
                    if artifact.content:
                        content_hash = hashlib.sha256(
                            str(artifact.content).encode()
                        ).hexdigest()[:16]
                    
                    item = EvidenceItem(
                        evidence_type=evidence_type,
                        artifact_id=artifact.artifact_id,
                        description=self._describe_artifact(artifact),
                        hash=content_hash,
                        available=True
                    )
                    
                    evidence.append(item)
            
            logger.info(f"📋 Gathered {len(evidence)} evidence items")
            
        except Exception as e:
            logger.error(f"Evidence gathering failed: {e}")
        
        return evidence
    
    def _classify_artifact(self, artifact_type: str) -> Optional[str]:
        """Artifact turini evidence turiga o'girish"""
        mapping = {
            "patch_diff": "diff",
            "changed_file": "diff",
            "test_result": "benchmark",
            "benchmark_result": "benchmark",
            "screenshot": "screenshot",
            "log": "log",
            "trace": "trace",
            "error": "log",
            "tool_manifest": "tool",
            "generated_doc": "documentation",
            "report": "documentation",
            "metadata": "metadata"
        }
        
        return mapping.get(artifact_type)
    
    def _describe_artifact(self, artifact) -> str:
        """Artifact ni tavsiflash"""
        descriptions = {
            "patch_diff": f"Code changes: {artifact.file_path or 'N/A'}",
            "test_result": "Test execution results",
            "benchmark_result": "Benchmark performance data",
            "screenshot": "Visual evidence",
            "log": "Execution logs",
            "trace": "Execution trace",
            "error": "Error information",
            "tool_manifest": f"Tool definition: {artifact.file_path or 'N/A'}",
            "generated_doc": "Generated documentation"
        }
        
        return descriptions.get(artifact.artifact_type, f"Artifact: {artifact.artifact_type}")
    
    def get_artifact_for_evidence(self, clone_id: str, artifact_type: str) -> Optional[Any]:
        """Specific artifact type olish"""
        artifacts = self.artifact_store.get_artifacts_by_type(clone_id, artifact_type)
        
        if artifacts:
            return artifacts[0].content
        
        return None


def create_report_aggregator(artifact_store: ArtifactStore) -> ReportAggregator:
    """Report Aggregator yaratish"""
    return ReportAggregator(artifact_store)
