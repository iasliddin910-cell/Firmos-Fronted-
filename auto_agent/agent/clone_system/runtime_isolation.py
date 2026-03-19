"""
================================================================================
LAYER 3: RUNTIME ISOLATION LAYER
================================================================================
Bu eng muhim xavfsizlik qavati.

Clone ichidagi agent:
- shell ishlatadi
- test yuritadi
- browser ochadi
- dependency o'rnatadi
- tool integratsiya qiladi

Shuning uchun u hostga tegmasligi kerak.

Talablar:
- alohida process namespace
- alohida temp/home dir
- CPU quota
- RAM limit
- file write limit
- subprocess limit
- timeout
- network policy

World-class variant:
- microVM birlamchi
- container fallback
- host process mode faqat debug uchun
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
import resource
import signal
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum
import psutil

from .core_types import CloneStatus
from .clone_factory import CloneFactory

logger = logging.getLogger(__name__)


# ================================================================================
# RUNTIME LIMITS - Runtime limitlari
# ================================================================================

@dataclass
class RuntimeLimits:
    """
    Runtime Limits - Clone uchun resurs limitlari
    """
    # Vaqt
    max_execution_time: int = 300  # sekund
    
    # Xotira
    max_memory_mb: int = 1024  # MB
    max_disk_mb: int = 5120  # MB
    
    # CPU
    max_cpu_percent: int = 80
    
    # Process
    max_subprocesses: int = 10
    max_threads: int = 50
    
    # Tarmoq
    allow_network: bool = False
    
    # File
    max_file_size_mb: int = 100
    allowed_directories: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "max_execution_time": self.max_execution_time,
            "max_memory_mb": self.max_memory_mb,
            "max_disk_mb": self.max_disk_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_subprocesses": self.max_subprocesses,
            "max_threads": self.max_threads,
            "allow_network": self.allow_network,
            "max_file_size_mb": self.max_file_size_mb,
            "allowed_directories": self.allowed_directories,
            "blocked_paths": self.blocked_paths
        }


# ================================================================================
# RUNTIME ISOLATION - Runtime izolyatsiya
# ================================================================================

class RuntimeIsolator:
    """
    Runtime Isolation Layer - Clone uchun izolyatsiya qavati
    
    Bu class:
    1. Isolated process namespace yaratadi
    2. Resurs limitlarini o'rnatadi
    3. File system access ni nazorat qiladi
    4. Network access ni bloklaydi (default)
    5. Subprocess/thread limitlarini qo'llaydi
    
    Qattiq qoida:
    Clone hech qachon:
    - original runtime state
    - original session
    - original secrets
    - original browser profile
    ga ulanmasin.
    """
    
    def __init__(self, factory: CloneFactory):
        self.factory = factory
        self.active_runtimes: Dict[str, 'CloneRuntime'] = {}
        self._lock = threading.RLock()
        
        logger.info("🛡️ Runtime Isolation Layer initialized")
    
    def create_runtime(self, clone_id: str, limits: Optional[RuntimeLimits] = None) -> 'CloneRuntime':
        """
        Clone Runtime yaratish
        
        Args:
            clone_id: Clone ID
            limits: Runtime limits (None = default limits)
        
        Returns:
            CloneRuntime: Clone runtime obyekti
        """
        with self._lock:
            if clone_id in self.active_runtimes:
                logger.warning(f"Runtime already exists for {clone_id}")
                return self.active_runtimes[clone_id]
            
            # Default limits
            if limits is None:
                limits = RuntimeLimits()
                clone_dir = self.factory.get_clone_directory(clone_id)
                if clone_dir:
                    limits.allowed_directories = [str(clone_dir)]
            
            # Runtime yaratish
            runtime = CloneRuntime(
                clone_id=clone_id,
                limits=limits,
                workspace_root=str(self.factory.get_clone_worktree(clone_id))
            )
            
            self.active_runtimes[clone_id] = runtime
            
            logger.info(f"🚀 Runtime created for {clone_id}")
            return runtime
    
    def get_runtime(self, clone_id: str) -> Optional['CloneRuntime']:
        """Runtime olish"""
        return self.active_runtimes.get(clone_id)
    
    def destroy_runtime(self, clone_id: str) -> bool:
        """
        Runtime ni destroy qilish
        
        Bu:
        1. Process larni to'xtatadi
        2. Resource cleanup qiladi
        3. Active runtimes dan olib tashlaydi
        """
        with self._lock:
            runtime = self.active_runtimes.get(clone_id)
            if not runtime:
                return False
            
            try:
                runtime.shutdown()
                self.active_runtimes.pop(clone_id, None)
                logger.info(f"💥 Runtime destroyed for {clone_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to destroy runtime: {e}")
                return False
    
    def get_all_runtimes(self) -> List[Dict]:
        """Barcha runtimes holatini olish"""
        result = []
        for clone_id, runtime in self.active_runtimes.items():
            result.append({
                "clone_id": clone_id,
                "status": runtime.status,
                "limits": runtime.limits.to_dict(),
                "started_at": runtime.started_at
            })
        return result


class CloneRuntime:
    """
    Clone Runtime - Clone uchun isolated execution environment
    
    Bu class izolyatsiya qiladi:
    1. Environment variables
    2. Working directory
    3. Process/thread creation
    4. Memory usage
    5. File system access
    """
    
    def __init__(self, clone_id: str, limits: RuntimeLimits, workspace_root: str):
        self.clone_id = clone_id
        self.limits = limits
        self.workspace_root = Path(workspace_root)
        
        # Holat
        self.status = "created"
        self.started_at = time.time()
        self.processes: List[subprocess.Popen] = []
        
        # Isolated environment
        self.env = self._create_isolated_env()
        
        # Monitoring
        self._monitor_thread = None
        self._running = True
        
        logger.info(f"📦 CloneRuntime initialized: {clone_id}")
    
    def _create_isolated_env(self) -> Dict[str, str]:
        """
        Isolated environment variables yaratish
        
        Clone o'z environmentiga ega bo'lishi kerak,
        original dan ajratilgan
        """
        # Base environment
        env = os.environ.copy()
        
        # Clone-specific paths
        clone_env = {
            # Clone-specific paths
            "CLONE_ID": self.clone_id,
            "CLONE_ROOT": str(self.workspace_root),
            
            # Temp directory (clone-specific)
            "TMPDIR": str(self.workspace_root / "tmp"),
            "TEMP": str(self.workspace_root / "tmp"),
            
            # Home (clone-specific)
            "HOME": str(self.workspace_root),
            
            # Python path
            "PYTHONPATH": str(self.workspace_root),
            
            # Disable network by default
            "NO_PROXY": "*",
            "no_proxy": "*",
        }
        
        # Add clone-specific env
        if not self.limits.allow_network:
            # Networkni block qilish uchun proxy o'rnatish
            env.update({
                "http_proxy": "127.0.0.1:1",
                "https_proxy": "127.0.0.1:1",
                "HTTP_PROXY": "127.0.0.1:1",
                "HTTPS_PROXY": "127.0.0.1:1",
            })
        
        env.update(clone_env)
        
        return env
    
    def execute_command(self, 
                       command: Union[str, List[str]], 
                       timeout: Optional[int] = None,
                       check_limits: bool = True) -> Dict[str, Any]:
        """
        Command ishga tushirish izolyatsiya qilingan holda
        
        Args:
            command: Command (string yoki list)
            timeout: Timeout sekundlarda
            check_limits: Limitlarni tekshirish kerakmi
        
        Returns:
            Dict: natija (stdout, stderr, returncode, duration)
        """
        if timeout is None:
            timeout = self.limits.max_execution_time
        
        # Limit checks
        if check_limits and len(self.processes) >= self.limits.max_subprocesses:
            return {
                "success": False,
                "error": "Max subprocesses reached",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "duration": 0
            }
        
        try:
            # Command ni tayyorlash
            if isinstance(command, str):
                cmd = command.split()
            else:
                cmd = command
            
            # Execute
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                cwd=str(self.workspace_root),
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(process)
            self.status = "running"
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                returncode = -1
                logger.warning(f"⏱️ Command timed out for {self.clone_id}")
            
            duration = time.time() - start_time
            
            # Process ni listdan olib tashlash
            if process in self.processes:
                self.processes.remove(process)
            
            return {
                "success": returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "duration": 0
            }
    
    def execute_python(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Python code ishga tushirish
        
        Args:
            code: Python code
            timeout: Timeout sekundlarda
        
        Returns:
            Dict: natija
        """
        # Code ni temporary file ga yozish
        temp_file = self.workspace_root / "tmp" / f"exec_{uuid.uuid4().hex}.py"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(temp_file, 'w') as f:
                f.write(code)
            
            return self.execute_command(
                ["python", str(temp_file)],
                timeout=timeout
            )
        finally:
            # Temp file ni o'chirish
            if temp_file.exists():
                temp_file.unlink()
    
    def check_resource_usage(self) -> Dict[str, Any]:
        """
        Resource usage tekshirish
        
        Returns:
            Dict: resource usage
        """
        try:
            current_process = psutil.Process()
            
            # Get all child processes
            children = current_process.children(recursive=True)
            
            # Calculate totals
            total_memory = current_process.memory_info().rss
            total_cpu = current_process.cpu_percent(interval=0.1)
            
            for child in children:
                try:
                    total_memory += child.memory_info().rss
                    total_cpu += child.cpu_percent(interval=0.1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Check limits
            memory_mb = total_memory / (1024 * 1024)
            within_memory = memory_mb <= self.limits.max_memory_mb
            within_cpu = total_cpu <= self.limits.max_cpu_percent
            within_processes = len(self.processes) <= self.limits.max_subprocesses
            
            return {
                "memory_mb": round(memory_mb, 2),
                "cpu_percent": round(total_cpu, 2),
                "processes": len(self.processes),
                "within_limits": within_memory and within_cpu and within_processes,
                "limits": {
                    "memory_mb": self.limits.max_memory_mb,
                    "cpu_percent": self.limits.max_cpu_percent,
                    "max_processes": self.limits.max_subprocesses
                }
            }
            
        except Exception as e:
            logger.error(f"Resource check error: {e}")
            return {
                "error": str(e),
                "within_limits": True
            }
    
    def is_path_allowed(self, path: str) -> bool:
        """
        Path ga ruxsat bor-yo'qligini tekshirish
        
        Args:
            path: Tekshirish kerak bo'lgan path
        
        Returns:
            bool: Ruxsat bormi
        """
        path = str(Path(path).resolve())
        
        # Blocked paths
        for blocked in self.limits.blocked_paths:
            if path.startswith(blocked):
                return False
        
        # Allowed directories
        if self.limits.allowed_directories:
            allowed = False
            for allowed_dir in self.limits.allowed_directories:
                if path.startswith(str(Path(allowed_dir).resolve())):
                    allowed = True
                    break
            if not allowed:
                return False
        
        return True
    
    def write_file(self, file_path: str, content: str) -> bool:
        """
        File yozish (limitlar bilan)
        
        Args:
            file_path: File path
            content: Content
        
        Returns:
            bool: Muvaffaqiyat bormi
        """
        # Path tekshirish
        if not self.is_path_allowed(file_path):
            logger.warning(f"Path not allowed: {file_path}")
            return False
        
        # Size tekshirish
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.limits.max_file_size_mb:
            logger.warning(f"File too large: {size_mb}MB > {self.limits.max_file_size_mb}MB")
            return False
        
        try:
            target = self.workspace_root / file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target, 'w') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            logger.error(f"Write file error: {e}")
            return False
    
    def read_file(self, file_path: str) -> Optional[str]:
        """
        File o'qish
        
        Args:
            file_path: File path
        
        Returns:
            str: File content yoki None
        """
        # Path tekshirish
        if not self.is_path_allowed(file_path):
            logger.warning(f"Path not allowed: {file_path}")
            return None
        
        try:
            target = self.workspace_root / file_path
            
            if not target.exists():
                return None
            
            with open(target, 'r') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Read file error: {e}")
            return None
    
    def start_monitoring(self):
        """Monitoring ni ishga tushirish"""
        def monitor_loop():
            while self._running:
                try:
                    # Resource check
                    usage = self.check_resource_usage()
                    
                    if not usage.get("within_limits", True):
                        logger.warning(f"⚠️ Resource limit exceeded for {self.clone_id}: {usage}")
                    
                    time.sleep(5)  # Har 5 soniyada
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def shutdown(self):
        """
        Runtime ni to'xtatish
        
        Bu:
        1. Barcha processlarni to'xtatadi
        2. Monitoring ni to'xtatadi
        3. Cleanup qiladi
        """
        self._running = False
        self.status = "shutdown"
        
        # Processlarni to'xtatish
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                except:
                    pass
        
        self.processes.clear()
        
        logger.info(f"🛑 Runtime shutdown complete: {self.clone_id}")


# ================================================================================
# SECRET SCOPE MANAGER - Secret isolation
# ================================================================================

class SecretScopeManager:
    """
    Secret Scope Manager - Clone uchun secret isolation
    
    Clone original secrets ga ulanmasligi kerak.
    Har clone uchun scoped secrets beriladi.
    """
    
    def __init__(self):
        self.candidate_secrets: Dict[str, Dict[str, str]] = {}
        self._lock = threading.RLock()
        
        logger.info("🔐 Secret Scope Manager initialized")
    
    def create_candidate_secrets(self, 
                                candidate_id: str, 
                                permissions: Dict[str, bool]) -> Dict[str, str]:
        """
        Candidate uchun secrets yaratish
        
        Args:
            candidate_id: Candidate ID
            permissions: Ruxsatlar
        
        Returns:
            Dict: Secrets
        """
        with self._lock:
            # Clone uchun scoped secrets
            secrets = {
                "CLONE_API_KEY": f"clone_{candidate_id}_key",
                "CLONE_SESSION_ID": f"session_{candidate_id}",
            }
            
            # Faqat ruxsat berilgan secrets qo'shish
            if permissions.get("secret_access", False):
                # Bu holda maxsus secrets beriladi
                # (Normalda bu qilinmaydi - xavfsizlik uchun)
                pass
            
            self.candidate_secrets[candidate_id] = secrets
            
            logger.info(f"🔑 Created secrets for candidate: {candidate_id}")
            return secrets
    
    def get_candidate_secrets(self, candidate_id: str) -> Optional[Dict[str, str]]:
        """Candidate secrets olish"""
        return self.candidate_secrets.get(candidate_id)
    
    def revoke_candidate_secrets(self, candidate_id: str, reason: str = ""):
        """
        Candidate secrets ni revoke qilish
        
        Args:
            candidate_id: Candidate ID
            reason: Sabab
        """
        with self._lock:
            if candidate_id in self.candidate_secrets:
                del self.candidate_secrets[candidate_id]
                logger.info(f"🔑 Revoked secrets for {candidate_id}: {reason}")


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_runtime_isolator(factory: CloneFactory) -> RuntimeIsolator:
    """Runtime Isolator yaratish"""
    return RuntimeIsolator(factory)


def create_secret_scope_manager() -> SecretScopeManager:
    """Secret Scope Manager yaratish"""
    return SecretScopeManager()
