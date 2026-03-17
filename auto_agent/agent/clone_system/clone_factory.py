"""
================================================================================
LAYER 1: CLONE FACTORY
================================================================================
Bu clone yaratadigan qavat.

Har clone uchun quyidagilar yaratiladi:
- unique clone id
- source snapshot
- isolated working tree
- runtime sandbox
- temp artifact storage
- session scope
- secret scope
- eval scope

Clone oddiy papka emas. U tajriba konteyneri.
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
import tempfile
import threading
import uuid
import asyncio
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum

from .core_types import (
    CloneType, CloneStatus, RiskClass,
    CloneMetadata, ChangeBudget, CloneLineage
)

logger = logging.getLogger(__name__)


# ================================================================================
# CLONE FACTORY - Clone yaratish tizimi
# ================================================================================

class CloneFactory:
    """
    Clone Factory - Clone yaratish tizimining markazi
    
    Bu class quyidagilarni bajaradi:
    1. Clone yaratish (worktree, isolated environment)
    2. Metadata yaratish va boshqarish
    3. TTL va cleanup boshqarish
    4. Clone lifecycle boshqarish
    
    Muhim: Clone yaratilganda metadata:
    - clone_id
    - parent_version
    - candidate_id
    - created_from_commit
    - reason
    - risk_level
    - ttl
    - scope_permissions
    """
    
    def __init__(self, 
                 workspace_root: str,
                 storage_root: str = "data/clones",
                 max_clones: int = 10,
                 default_ttl: int = 3600):
        """
        Clone Factory ni ishga tushirish
        
        Args:
            workspace_root: Asosiy workspace yo'li
            storage_root: Clone storage yo'li
            max_clones: Maksimal bir vaqtda faol clone lar soni
            default_ttl: Default TTL sekundlarda
        """
        self.workspace_root = Path(workspace_root)
        self.storage_root = Path(storage_root)
        self.max_clones = max_clones
        self.default_ttl = default_ttl
        
        # Storage yaratish
        self.storage_root.mkdir(parents=True, exist_ok=True)
        (self.storage_root / "active").mkdir(exist_ok=True)
        (self.storage_root / "archived").mkdir(exist_ok=True)
        (self.storage_root / "artifacts").mkdir(exist_ok=True)
        
        # Faol clone lar
        self.active_clones: Dict[str, CloneMetadata] = {}
        self.clone_directories: Dict[str, Path] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Cleanup thread
        self._cleanup_thread = None
        self._running = True
        self._start_cleanup_thread()
        
        logger.info(f"🏭 Clone Factory initialized: workspace={workspace_root}, storage={storage_root}")
    
    def _start_cleanup_thread(self):
        """Cleanup thread ni ishga tushirish"""
        def cleanup_loop():
            while self._running:
                try:
                    self._cleanup_expired()
                    time.sleep(60)  # Har 1 daqiqada tekshirish
                except Exception as e:
                    logger.error(f"Cleanup thread error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("🧹 Cleanup thread started")
    
    def _cleanup_expired(self):
        """Muddati o'tgan clone larni tozalash"""
        current_time = time.time()
        expired = []
        
        for clone_id, metadata in self.active_clones.items():
            if metadata.expires_at < current_time:
                expired.append(clone_id)
        
        for clone_id in expired:
            logger.warning(f"🧹 Cleaning up expired clone: {clone_id}")
            try:
                self.cleanup_clone(clone_id, reason="TTL expired")
            except Exception as e:
                logger.error(f"Failed to cleanup clone {clone_id}: {e}")
    
    def create_clone(self,
                    clone_type: CloneType,
                    reason: str,
                    candidate_id: Optional[str] = None,
                    parent_clone_id: Optional[str] = None,
                    risk_level: RiskClass = RiskClass.LOW,
                    ttl: Optional[int] = None,
                    scope_permissions: Optional[Dict[str, bool]] = None) -> CloneMetadata:
        """
        Clone yaratish - ASOSIY METOD
        
        Args:
            clone_type: Clone turi (MICRO_PATCH, CAPABILITY, WORKFLOW, RESEARCH, FORK)
            reason: Clone yaratish sababi
            candidate_id: Upgrade candidate ID
            parent_clone_id: Parent clone ID (lineage uchun)
            risk_level: Risk klassi
            ttl: Time to live (sekund)
            scope_permissions: Ruxsatlar
        
        Returns:
            CloneMetadata: Clone metama'lumotlari
        
        Raises:
            RuntimeError: Clone yaratish muvaffaqiyatsiz bo'lsa
        """
        with self._lock:
            # Check max clones
            if len(self.active_clones) >= self.max_clones:
                # Try to cleanup expired first
                self._cleanup_expired()
                if len(self.active_clones) >= self.max_clones:
                    raise RuntimeError(f"Max clones reached ({self.max_clones}). Wait for cleanup.")
            
            # Generate clone ID
            clone_id = self._generate_clone_id(clone_type)
            
            # Get current commit
            commit = self._get_current_commit()
            
            # Get parent lineage
            lineage = []
            if parent_clone_id and parent_clone_id in self.active_clones:
                parent_meta = self.active_clones[parent_clone_id]
                lineage = parent_meta.lineage + [parent_clone_id]
            
            # Create metadata
            metadata = CloneMetadata(
                clone_id=clone_id,
                parent_version=self._get_version(),
                candidate_id=candidate_id or f"candidate_{clone_id}",
                created_from_commit=commit,
                reason=reason,
                risk_level=risk_level,
                ttl=ttl or self.default_ttl,
                scope_permissions=scope_permissions or self._default_permissions(),
                clone_type=clone_type,
                parent_clone_id=parent_clone_id,
                lineage=lineage,
                status=CloneStatus.CREATING
            )
            metadata.expires_at = time.time() + metadata.ttl
            
            # Create clone directory
            clone_dir = self._create_clone_directory(clone_id)
            
            # Save metadata
            self._save_metadata(metadata)
            
            # Store in memory
            self.active_clones[clone_id] = metadata
            self.clone_directories[clone_id] = clone_dir
            
            logger.info(f"✅ Clone created: {clone_id} (type={clone_type.value}, reason={reason})")
            
            return metadata
    
    def _generate_clone_id(self, clone_type: CloneType) -> str:
        """Unique clone ID yaratish"""
        timestamp = int(time.time() * 1000)
        short_type = clone_type.value[:4]
        unique = uuid.uuid4().hex[:8]
        return f"clone_{short_type}_{timestamp}_{unique}"
    
    def _get_current_commit(self) -> str:
        """Hozirgi git commit ni olish"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()[:12]
        except Exception as e:
            logger.warning(f"Could not get git commit: {e}")
        return "unknown"
    
    def _get_version(self) -> str:
        """Version olish"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "v0.0.0"
    
    def _default_permissions(self) -> Dict[str, bool]:
        """Default ruxsatlar"""
        return {
            "file_read": True,
            "file_write": True,
            "file_delete": False,
            "process_spawn": True,
            "network_access": False,
            "secret_access": False,
            "tool_create": True,
            "benchmark_create": True
        }
    
    def _create_clone_directory(self, clone_id: str) -> Path:
        """Clone directory yaratish"""
        clone_dir = self.storage_root / "active" / clone_id
        clone_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        (clone_dir / "worktree").mkdir(exist_ok=True)
        (clone_dir / "artifacts").mkdir(exist_ok=True)
        (clone_dir / "logs").mkdir(exist_ok=True)
        (clone_dir / "tmp").mkdir(exist_ok=True)
        
        return clone_dir
    
    def _save_metadata(self, metadata: CloneMetadata):
        """Metadatani saqlash"""
        metadata_file = self.storage_root / "active" / metadata.clone_id / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2, default=str)
    
    def get_clone(self, clone_id: str) -> Optional[CloneMetadata]:
        """Clone olish"""
        return self.active_clones.get(clone_id)
    
    def get_clone_directory(self, clone_id: str) -> Optional[Path]:
        """Clone directory olish"""
        return self.clone_directories.get(clone_id)
    
    def get_clone_worktree(self, clone_id: str) -> Optional[Path]:
        """Clone worktree olish"""
        clone_dir = self.clone_directories.get(clone_id)
        if clone_dir:
            return clone_dir / "worktree"
        return None
    
    def get_clone_artifacts(self, clone_id: str) -> Optional[Path]:
        """Clone artifacts directory olish"""
        clone_dir = self.clone_directories.get(clone_id)
        if clone_dir:
            return clone_dir / "artifacts"
        return None
    
    def update_clone_status(self, clone_id: str, status: CloneStatus):
        """Clone holatini yangilash"""
        with self._lock:
            if clone_id in self.active_clones:
                self.active_clones[clone_id].status = status
                self._save_metadata(self.active_clones[clone_id])
                logger.info(f"📊 Clone {clone_id} status: {status.value}")
    
    def extend_ttl(self, clone_id: str, additional_seconds: int) -> bool:
        """Clone TTL ni uzaytirish"""
        with self._lock:
            if clone_id in self.active_clones:
                metadata = self.active_clones[clone_id]
                metadata.expires_at += additional_seconds
                metadata.ttl += additional_seconds
                self._save_metadata(metadata)
                logger.info(f"⏰ Extended TTL for {clone_id}: +{additional_seconds}s")
                return True
        return False
    
    def cleanup_clone(self, clone_id: str, reason: str = "manual") -> bool:
        """
        Clone ni tozalash
        
        Bu metod:
        1. Directory larni o'chiradi
        2. Metadata ni archived ga ko'chiradi
        3. Active clones dan olib tashlaydi
        """
        with self._lock:
            if clone_id not in self.active_clones:
                logger.warning(f"Clone not found: {clone_id}")
                return False
            
            metadata = self.active_clones[clone_id]
            clone_dir = self.clone_directories.get(clone_id)
            
            try:
                # Move to archived
                if clone_dir and clone_dir.exists():
                    archived_dir = self.storage_root / "archived" / clone_id
                    shutil.move(str(clone_dir), str(archived_dir))
                    
                    # Save final metadata
                    metadata.status = CloneStatus.CLEANUP
                    metadata_file = archived_dir / "metadata.json"
                    with open(metadata_file, 'w') as f:
                        json.dump({
                            **metadata.to_dict(),
                            "cleanup_reason": reason,
                            "cleaned_at": time.time()
                        }, f, indent=2, default=str)
                
                # Remove from active
                self.active_clones.pop(clone_id, None)
                self.clone_directories.pop(clone_id, None)
                
                logger.info(f"🧹 Cleaned up clone: {clone_id} (reason: {reason})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to cleanup clone {clone_id}: {e}")
                return False
    
    def get_active_clones(self) -> List[Dict]:
        """Faol clone lar ro'yxatini olish"""
        result = []
        for clone_id, metadata in self.active_clones.items():
            result.append({
                "clone_id": clone_id,
                "type": metadata.clone_type.value,
                "status": metadata.status.value,
                "risk": metadata.risk_level.value,
                "created_at": metadata.created_at,
                "expires_at": metadata.expires_at,
                "reason": metadata.reason
            })
        return result
    
    def get_clone_stats(self) -> Dict:
        """Clone statistics"""
        total = len(self.active_clones)
        by_type = defaultdict(int)
        by_status = defaultdict(int)
        by_risk = defaultdict(int)
        
        for metadata in self.active_clones.values():
            by_type[metadata.clone_type.value] += 1
            by_status[metadata.status.value] += 1
            by_risk[metadata.risk_level.value] += 1
        
        return {
            "total_active": total,
            "max_clones": self.max_clones,
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "by_risk": dict(by_risk)
        }
    
    def shutdown(self):
        """Factory ni to'xtatish"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("🏭 Clone Factory shutdown")


# ================================================================================
# SOURCE CLONE LAYER - Kod nusxasi bilan ishlash
# ================================================================================

class SourceCloneManager:
    """
    Source Clone Layer - Kod nusxasi bilan ishlash qavati
    
    Tavsiya etilgan model (Productionga yaqin tizim uchun):
    - immutable base snapshot
    - ustidan writable overlay
    - patchlar overlay'da
    - original read-only
    
    Bu juda yaxshi model, chunki:
    - revert oson
    - diff aniq
    - corruption xavfi past
    - clone compare oson
    """
    
    def __init__(self, workspace_root: str, factory: CloneFactory):
        self.workspace_root = Path(workspace_root)
        self.factory = factory
        
        logger.info("📂 Source Clone Layer initialized")
    
    def create_source_snapshot(self, clone_id: str) -> bool:
        """
        Source snapshot yaratish - immutable base
        
        Git worktree ishlatamiz
        """
        metadata = self.factory.get_clone(clone_id)
        if not metadata:
            logger.error(f"Clone not found: {clone_id}")
            return False
        
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            logger.error(f"Clone directory not found: {clone_id}")
            return False
        
        try:
            # Git worktree yaratish
            result = subprocess.run(
                ["git", "worktree", "add", "-f", str(clone_dir), metadata.created_from_commit],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Agar worktree ishlamasa, oddiy copy qilish
                logger.warning(f"Git worktree failed, using copy: {result.stderr}")
                shutil.copytree(self.workspace_root, clone_dir, 
                             ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc', '.venv'))
            
            logger.info(f"📦 Source snapshot created for {clone_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create source snapshot: {e}")
            return False
    
    def get_file_diff(self, clone_id: str, file_path: str) -> Optional[str]:
        """File diff olish"""
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return None
        
        try:
            # Diff olish
            clone_file = clone_dir / file_path
            original_file = self.workspace_root / file_path
            
            if not clone_file.exists():
                return None
            
            if not original_file.exists():
                return f"+++ {file_path}\n(File created)"
            
            result = subprocess.run(
                ["diff", "-u", str(original_file), str(clone_file)],
                capture_output=True,
                text=True
            )
            
            return result.stdout if result.stdout else "No changes"
            
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return None
    
    def get_all_diffs(self, clone_id: str) -> Dict[str, str]:
        """Barcha file diffs olish"""
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return {}
        
        diffs = {}
        
        try:
            # Git diff ishlatish
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=clone_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for file_path in result.stdout.strip().split('\n'):
                    if file_path:
                        diff = self.get_file_diff(clone_id, file_path)
                        if diff:
                            diffs[file_path] = diff
            
        except Exception as e:
            logger.error(f"Failed to get all diffs: {e}")
        
        return diffs
    
    def revert_changes(self, clone_id: str, file_path: Optional[str] = None) -> bool:
        """
        O'zgarishlarni qaytarish
        
        Args:
            clone_id: Clone ID
            file_path: Qaytarish kerak bo'lgan file (None = hamma)
        """
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            if file_path:
                # Bitta file ni qaytarish
                original = self.workspace_root / file_path
                clone_file = clone_dir / file_path
                
                if original.exists():
                    shutil.copy2(original, clone_file)
                elif clone_file.exists():
                    clone_file.unlink()
            else:
                # Hammasini qaytarish - worktree ni qayta yaratish
                metadata = self.factory.get_clone(clone_id)
                if metadata:
                    # Worktree ni o'chirib, qayta yaratish
                    shutil.rmtree(clone_dir)
                    clone_dir.mkdir(parents=True)
                    self.create_source_snapshot(clone_id)
            
            logger.info(f"↩️ Reverted changes for {clone_id}" + (f" file: {file_path}" if file_path else ""))
            return True
            
        except Exception as e:
            logger.error(f"Failed to revert: {e}")
            return False
    
    def apply_patch(self, clone_id: str, file_path: str, content: str) -> bool:
        """Patch qo'llash"""
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            target_file = clone_dir / file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_file, 'w') as f:
                f.write(content)
            
            logger.info(f"📝 Patch applied: {clone_id}/{file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply patch: {e}")
            return False
    
    def cleanup_worktree(self, clone_id: str) -> bool:
        """Worktree ni tozalash"""
        clone_dir = self.factory.get_clone_directory(clone_id)
        if not clone_dir:
            return False
        
        try:
            worktree = clone_dir / "worktree"
            if worktree.exists():
                # Git worktree remove
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree)],
                    cwd=self.workspace_root,
                    capture_output=True
                )
            
            logger.info(f"🧹 Worktree cleaned: {clone_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup worktree: {e}")
            # Xatolik bo'lsa ham, papkani o'chirishga urinamiz
            try:
                if worktree.exists():
                    shutil.rmtree(worktree)
            except:
                pass
            return True


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_clone_factory(workspace_root: str, **kwargs) -> CloneFactory:
    """Clone Factory yaratish"""
    return CloneFactory(workspace_root, **kwargs)


def create_source_clone_manager(workspace_root: str, factory: CloneFactory) -> SourceCloneManager:
    """Source Clone Manager yaratish"""
    return SourceCloneManager(workspace_root, factory)
