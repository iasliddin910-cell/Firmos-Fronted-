"""
ResultIntegritySigner - Result Integrity
====================================

Natija yaxlitligini himoya qilish.

Bu modul:
- Manifest hash
- Artifact hash
- Verifier report hash
- Final score hash

Definition of Done:
8. Result artifacts integrity hash bilan saqlanadi.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import hashlib
import json
import time


@dataclass
class IntegrityRecord:
    """Integrity record."""
    run_id: str
    timestamp: str
    
    # Hashes
    manifest_hash: str
    artifacts_hash: str
    verifier_hash: str
    score_hash: str
    
    # Metadata
    agent_version: str
    config_hash: str


class ResultIntegritySigner:
    """
    Result integrity signer.
    
    Definition of Done:
    8. Result artifacts integrity hash bilan saqlanadi.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "/tmp/eval_integrity"
        os.makedirs(self.storage_path, exist_ok=True)
    
    def sign_result(
        self,
        run_id: str,
        manifest: Dict,
        artifacts: List[str],
        verifier_report: Dict,
        score: float,
        agent_version: str,
        config: Dict,
    ) -> IntegrityRecord:
        """Resultni imzolash."""
        timestamp = time.time()
        
        # Hash manifest
        manifest_str = json.dumps(manifest, sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_str.encode()).hexdigest()
        
        # Hash artifacts
        artifacts_hash = self._hash_artifacts(artifacts)
        
        # Hash verifier report
        verifier_str = json.dumps(verifier_report, sort_keys=True)
        verifier_hash = hashlib.sha256(verifier_str.encode()).hexdigest()
        
        # Hash score
        score_str = f"{run_id}:{score}:{timestamp}"
        score_hash = hashlib.sha256(score_str.encode()).hexdigest()
        
        # Config hash
        config_str = json.dumps(config, sort_keys=True)
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()
        
        record = IntegrityRecord(
            run_id=run_id,
            timestamp=timestamp,
            manifest_hash=manifest_hash,
            artifacts_hash=artifacts_hash,
            verifier_hash=verifier_hash,
            score_hash=score_hash,
            agent_version=agent_version,
            config_hash=config_hash,
        )
        
        # Save record
        self._save_record(record)
        
        return record
    
    def verify_result(
        self,
        run_id: str,
        manifest: Dict,
        artifacts: List[str],
        verifier_report: Dict,
        score: float,
    ) -> bool:
        """Resultni tekshirish."""
        # Load record
        record = self._load_record(run_id)
        if not record:
            return False
        
        # Verify manifest
        manifest_str = json.dumps(manifest, sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_str.encode()).hexdigest()
        if manifest_hash != record.manifest_hash:
            return False
        
        # Verify artifacts
        artifacts_hash = self._hash_artifacts(artifacts)
        if artifacts_hash != record.artifacts_hash:
            return False
        
        # Verify verifier
        verifier_str = json.dumps(verifier_report, sort_keys=True)
        verifier_hash = hashlib.sha256(verifier_str.encode()).hexdigest()
        if verifier_hash != record.verifier_hash:
            return False
        
        # Verify score
        score_str = f"{run_id}:{score}:{record.timestamp}"
        score_hash = hashlib.sha256(score_str.encode()).hexdigest()
        if score_hash != record.score_hash:
            return False
        
        return True
    
    def _hash_artifacts(self, artifacts: List[str]) -> str:
        """Artifactsni hash qilish."""
        hasher = hashlib.sha256()
        
        for artifact_path in sorted(artifacts):
            if os.path.exists(artifact_path):
                with open(artifact_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def _save_record(self, record: IntegrityRecord) -> None:
        """Recordni saqlash."""
        path = os.path.join(self.storage_path, f"{record.run_id}.json")
        
        with open(path, 'w') as f:
            json.dump({
                "run_id": record.run_id,
                "timestamp": record.timestamp,
                "manifest_hash": record.manifest_hash,
                "artifacts_hash": record.artifacts_hash,
                "verifier_hash": record.verifier_hash,
                "score_hash": record.score_hash,
                "agent_version": record.agent_version,
                "config_hash": record.config_hash,
            }, f, indent=2)
    
    def _load_record(self, run_id: str) -> Optional[IntegrityRecord]:
        """Recordni yuklash."""
        path = os.path.join(self.storage_path, f"{run_id}.json")
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        return IntegrityRecord(**data)


def create_integrity_signer(storage_path: str = None) -> ResultIntegritySigner:
    """Integrity signer yaratish."""
    return ResultIntegritySigner(storage_path)
