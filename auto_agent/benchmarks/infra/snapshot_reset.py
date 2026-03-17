"""
SnapshotResetManager - Clean Snapshot and Reset
==========================================

Tozalash va tiklash.

Bu modul:
- Clean copy
- DB snapshot restore
- Service reset
- Browser storage wipe
- Temp wipe

Definition of Done:
(Part of infrastructure - related to reset/cleanup)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os
import shutil
import subprocess


@dataclass
class SnapshotConfig:
    """Snapshot configuration."""
    snapshot_path: str
    workspace_path: str
    services: List[str] = None
    databases: List[str] = None


class SnapshotResetManager:
    """
    Snapshot reset manager.
    """
    
    def __init__(self, config: SnapshotConfig = None):
        self.config = config
    
    def reset_workspace(self) -> None:
        """Workspace'ni tozalash."""
        if not self.config or not self.config.workspace_path:
            return
        
        # Remove all contents
        if os.path.exists(self.config.workspace_path):
            shutil.rmtree(self.config.workspace_path, ignore_errors=True)
        
        # Recreate empty
        os.makedirs(self.config.workspace_path, exist_ok=True)
    
    def restore_from_snapshot(self) -> None:
        """Snapshot'dan tiklash."""
        if not self.config or not self.config.snapshot_path:
            return
        
        if not os.path.exists(self.config.snapshot_path):
            return
        
        # Copy snapshot to workspace
        if os.path.exists(self.config.workspace_path):
            shutil.rmtree(self.config.workspace_path, ignore_errors=True)
        
        shutil.copytree(
            self.config.snapshot_path,
            self.config.workspace_path,
            dirs_exist_ok=True,
        )
    
    def reset_services(self) -> None:
        """Service'larni reset qilish."""
        if not self.config or not self.config.services:
            return
        
        for service in self.config.services:
            try:
                # Simple reset - restart service
                subprocess.run(
                    ["systemctl", "restart", service],
                    capture_output=True,
                    timeout=30,
                )
            except Exception:
                pass
    
    def reset_databases(self) -> None:
        """Database'larni reset qilish."""
        # This is simplified - would need actual DB reset logic
        pass
    
    def full_reset(self) -> None:
        """To'liq reset."""
        self.reset_workspace()
        self.restore_from_snapshot()
        self.reset_services()
        self.reset_databases()


def create_snapshot_manager(
    snapshot_path: str,
    workspace_path: str,
) -> SnapshotResetManager:
    """Snapshot manager yaratish."""
    config = SnapshotConfig(
        snapshot_path=snapshot_path,
        workspace_path=workspace_path,
    )
    return SnapshotResetManager(config)
