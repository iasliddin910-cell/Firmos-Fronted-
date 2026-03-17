"""
FilesystemGuard - Filesystem Boundary Enforcement
==============================================

Filesystem boundary enforcement.

Bu modul:
- Path traversal check
- Symlink escape check
- Write scope check
- Read-only mount enforcement

Definition of Done:
2. Forbidden path access real enforcement bilan bloklanadi.
"""

from dataclasses import dataclass
from typing import List, Set, Optional
import os
from pathlib import Path


@dataclass
class FilesystemPolicy:
    """Filesystem policy."""
    allowed_read_paths: List[str]
    allowed_write_paths: List[str]
    forbidden_paths: List[str]
    read_only_paths: List[str]


class FilesystemViolation(Exception):
    """Filesystem violation."""
    pass


class FilesystemGuard:
    """
    Filesystem boundary guard.
    
    Definition of Done:
    2. Forbidden path access real enforcement bilan bloklanadi.
    """
    
    def __init__(self, policy: FilesystemPolicy = None):
        self.policy = policy or FilesystemPolicy(
            allowed_read_paths=[],
            allowed_write_paths=[],
            forbidden_paths=[],
            read_only_paths=[],
        )
        
        # Convert to Path objects
        self._allowed_read = [Path(p).resolve() for p in self.policy.allowed_read_paths]
        self._allowed_write = [Path(p).resolve() for p in self.policy.allowed_write_paths]
        self._forbidden = [Path(p).resolve() for p in self.policy.forbidden_paths]
        self._read_only = [Path(p).resolve() for p in self.policy.read_only_paths]
    
    def check_read(self, path: str) -> bool:
        """Read ruxsatini tekshirish."""
        resolved = self._resolve_path(path)
        
        # Check forbidden
        for forbidden in self._forbidden:
            if resolved.is_relative_to(forbidden):
                raise FilesystemViolation(f"Access denied to forbidden path: {path}")
        
        # Check allowed (if specified)
        if self._allowed_read:
            for allowed in self._allowed_read:
                if resolved.is_relative_to(allowed):
                    return True
            raise FilesystemViolation(f"Path not in allowed read paths: {path}")
        
        return True
    
    def check_write(self, path: str) -> bool:
        """Write ruxsatini tekshirish."""
        resolved = self._resolve_path(path)
        
        # Check forbidden
        for forbidden in self._forbidden:
            if resolved.is_relative_to(forbidden):
                raise FilesystemViolation(f"Write denied to forbidden path: {path}")
        
        # Check read-only
        for read_only in self._read_only:
            if resolved.is_relative_to(read_only):
                raise FilesystemViolation(f"Path is read-only: {path}")
        
        # Check allowed write paths
        if self._allowed_write:
            for allowed in self._allowed_write:
                if resolved.is_relative_to(allowed):
                    return True
            raise FilesystemViolation(f"Path not in allowed write paths: {path}")
        
        return True
    
    def _resolve_path(self, path: str) -> Path:
        """Path ni resolve qilish."""
        # Handle relative paths
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        
        resolved = Path(path).resolve()
        
        # Check for symlink escape
        if os.path.islink(path):
            # Symlink bo'lsa, actual path ni olish kerak
            pass  # Already resolved
        
        # Check for path traversal
        # Basic check: .. ni olib tashlash
        parts = resolved.parts
        if ".." in parts:
            raise FilesystemViolation(f"Path traversal detected: {path}")
        
        return resolved
    
    def is_read_only(self, path: str) -> bool:
        """Path read-only-mik?"""
        resolved = self._resolve_path(path)
        
        for read_only in self._read_only:
            if resolved.is_relative_to(read_only):
                return True
        
        return False


def create_filesystem_guard(
    workspace_root: str,
    allowed_artifacts: List[str] = None,
    read_only_fixtures: List[str] = None,
) -> FilesystemGuard:
    """Filesystem guard yaratish."""
    forbidden = [
        os.path.expanduser("~"),
        "/etc",
        "/root",
        "/home",
        "/.ssh",
        "/.aws",
        "/.git",
    ]
    
    allowed_write = [workspace_root]
    if allowed_artifacts:
        allowed_write.extend(allowed_artifacts)
    
    read_only = read_only_fixtures or []
    
    policy = FilesystemPolicy(
        allowed_read_paths=[workspace_root] + (allowed_artifacts or []) + (read_only_fixtures or []),
        allowed_write_paths=allowed_write,
        forbidden_paths=forbidden,
        read_only_paths=read_only,
    )
    
    return FilesystemGuard(policy)
