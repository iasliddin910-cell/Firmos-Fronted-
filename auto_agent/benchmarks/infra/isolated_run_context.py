"""
IsolatedRunContext - Per-Run Isolation
======================================

Har benchmark run uchun ajratilgan kontekst.

Bu modul:
- Unique workspace
- Unique temp dir
- Unique cache dir
- Unique browser profile
- Unique ports
- Unique artifact dir

Definition of Done:
1. Har run unique isolated workspace'da ishlaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import os
import shutil
import uuid
import tempfile
from pathlib import Path
from datetime import datetime


@dataclass
class IsolatedContext:
    """Isolated run context."""
    run_id: str
    task_id: str
    
    # Directories
    workspace_root: str
    temp_dir: str
    cache_dir: str
    artifact_dir: str
    
    # Browser
    browser_profile_dir: str
    
    # Ports
    allocated_ports: List[int] = field(default_factory=list)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    cleanup_policy: str = "clean"  # clean, archive, keep_on_failure
    
    def cleanup(self) -> None:
        """Contextni tozalash."""
        # Remove workspace
        if os.path.exists(self.workspace_root):
            shutil.rmtree(self.workspace_root, ignore_errors=True)
        
        # Remove temp
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Remove cache
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir, ignore_errors=True)
        
        # Remove browser profile
        if os.path.exists(self.browser_profile_dir):
            shutil.rmtree(self.browser_profile_dir, ignore_errors=True)
        
        # Remove artifact dir (but keep artifacts if archive policy)
        if self.cleanup_policy == "clean" and os.path.exists(self.artifact_dir):
            shutil.rmtree(self.artifact_dir, ignore_errors=True)


class IsolatedRunContext:
    """
    Per-run isolation context manager.
    
    Definition of Done:
    1. Har run unique isolated workspace'da ishlaydi.
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or "/tmp/eval_runs"
        os.makedirs(self.base_path, exist_ok=True)
        
        # Port allocator
        self._port_counter = 12000
        self._used_ports = set()
    
    def create_context(
        self,
        run_id: str,
        task_id: str,
        config: Dict[str, Any] = None,
    ) -> IsolatedContext:
        """Yangi isolated context yaratish."""
        # Generate unique ID
        unique_id = f"{run_id}_{task_id}_{uuid.uuid4().hex[:8]}"
        
        # Create directories
        workspace_root = os.path.join(self.base_path, unique_id, "workspace")
        temp_dir = os.path.join(self.base_path, unique_id, "temp")
        cache_dir = os.path.join(self.base_path, unique_id, "cache")
        artifact_dir = os.path.join(self.base_path, unique_id, "artifacts")
        browser_profile_dir = os.path.join(self.base_path, unique_id, "browser")
        
        for dir_path in [workspace_root, temp_dir, cache_dir, artifact_dir, browser_profile_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Allocate ports
        ports = self._allocate_ports(3)
        
        context = IsolatedContext(
            run_id=run_id,
            task_id=task_id,
            workspace_root=workspace_root,
            temp_dir=temp_dir,
            cache_dir=cache_dir,
            artifact_dir=artifact_dir,
            browser_profile_dir=browser_profile_dir,
            allocated_ports=ports,
            cleanup_policy=config.get("cleanup_policy", "clean") if config else "clean",
        )
        
        return context
    
    def _allocate_ports(self, count: int) -> List[int]:
        """Port ajratish."""
        ports = []
        for _ in range(count):
            while self._port_counter in self._used_ports:
                self._port_counter += 1
            ports.append(self._port_counter)
            self._used_ports.add(self._port_counter)
            self._port_counter += 1
        return ports
    
    def release_ports(self, ports: List[int]) -> None:
        """Portlarni bo'shatish."""
        for port in ports:
            self._used_ports.discard(port)
    
    def cleanup_all(self) -> None:
        """Barcha contextlarni tozalash."""
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path, ignore_errors=True)
        os.makedirs(self.base_path, exist_ok=True)
        self._used_ports.clear()


def create_isolated_context(
    run_id: str,
    task_id: str,
    base_path: str = None,
) -> IsolatedContext:
    """Isolated context yaratish."""
    manager = IsolatedRunContext(base_path)
    return manager.create_context(run_id, task_id)
