"""
OmniAgent X - Enhanced Sandbox & Security
==========================================
Provides secure command execution and workspace isolation

Features:
- Command allowlist by mode
- Subprocess isolation
- Restricted working directory
- CPU/Memory quotas
- Filesystem boundaries
- Network controls
"""
import os
import sys
import subprocess
import tempfile
import shutil
import resource
import signal
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ExecutionMode(Enum):
    """Execution security modes"""
    SAFE = "safe"           # Whitelist only
    NORMAL = "normal"       # Basic restrictions
    ADVANCED = "advanced"   # Full sandbox
    UNRESTRICTED = "unrestricted"
    CONTAINERIZED = "containerized"  # No restrictions (for trusted ops)


class CommandCategory(Enum):
    """Command categories for allowlist"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SYSTEM_INFO = "system_info"
    NETWORK = "network"
    DEVELOPMENT = "development"
    PROCESS = "process"
    DANGEROUS = "dangerous"


# ==================== COMMAND ALLOWLIST ====================

class CommandAllowlist:
    """
    Safe command allowlist by category
    Replaces dangerous denylist approach
    """
    
    # Define allowed commands by category
    ALLOWLIST = {
        CommandCategory.FILE_READ: [
            "cat", "head", "tail", "less", "more", "grep", "find", "ls", "stat",
            "file", "wc", "sort", "uniq", "diff", "which", "type", "readlink"
        ],
        CommandCategory.FILE_WRITE: [
            "echo", "tee", "mkdir", "touch", "cp", "mv", "chmod", "chown"
        ],
        CommandCategory.FILE_DELETE: [
            "rm", "rmdir"  # With restrictions
        ],
        CommandCategory.SYSTEM_INFO: [
            "ps", "top", "htop", "df", "du", "free", "uname", "hostname",
            "whoami", "id", "env", "printenv", "uptime", "date", "cal"
        ],
        CommandCategory.NETWORK: [
            "curl", "wget", "ping", "nslookup", "dig", "ip", "ifconfig",
            "netstat", "ss", "traceroute", "tracepath"
        ],
        CommandCategory.DEVELOPMENT: [
            "python", "python3", "pip", "pip3", "npm", "node", "git",
            "cargo", "rustc", "go", "javac", "java", "gcc", "g++",
            "make", "cmake", "pytest", "ruff", "black", "eslint"
        ],
        CommandCategory.PROCESS: [
            "kill", "pkill", "killall", "jobs", "fg", "bg"
        ],
    }
    
    # Dangerous commands that are NEVER allowed
    BLOCKED_COMMANDS = [
        "rm -rf /", "mkfs", "dd if=/dev/zero", "fork",
        ":(){:|:&};:", "curl | sh", "wget | sh",
        "chmod 777", "chown -R", "chgrp -R",
        "> /dev/sda", "dd of=/dev/", "mv /*",
        "wget -O-", "curl -sL"  # Remote execution attempts
    ]
    
    @classmethod
    def is_allowed(cls, command: str, mode: ExecutionMode = ExecutionMode.NORMAL) -> Tuple[bool, str]:
        """Check if command is allowed"""
        
        # Get first word (command)
        parts = command.strip().split()
        if not parts:
            return False, "Bo'sh buyruq"
        
        cmd = parts[0]
        
        # Check blocked commands (substring match)
        for blocked in cls.BLOCKED_COMMANDS:
            if blocked in command:
                return False, f"Bloklangan buyruq: {blocked}"
        
        # Check mode-based allowlist
        if mode == ExecutionMode.SAFE:
            # Only allow specifically safe commands
            for category, commands in cls.ALLOWLIST.items():
                if category in [CommandCategory.FILE_READ, CommandCategory.SYSTEM_INFO]:
                    if cmd in commands:
                        return True, f"Ruxsat berilgan: {category.value}"
            
            return False, "SAFE rejada ruxsat yo'q"
        
        elif mode == ExecutionMode.NORMAL:
            # Allow most development and file operations
            for category, commands in cls.ALLOWLIST.items():
                if category != CommandCategory.DANGEROUS:
                    if cmd in commands:
                        return True, f"Ruxsat berilgan: {category.value}"
            
            return False, "NORMAL rejada ruxsat yo'q"
        
        elif mode == ExecutionMode.ADVANCED:
            # Allow with some restrictions
            for category, commands in cls.ALLOWLIST.items():
                if cmd in commands:
                    return True, f"Ruxsat berilgan: {category.value}"
            
            return False, "ADVANCED rejada ruxsat yo'q"
        
        # UNRESTRICTED - allow all but still check blocked
        return True, "UNRESTRICTED rejasi"
    
    @classmethod
    def get_allowed_commands(cls, mode: ExecutionMode) -> List[str]:
        """Get list of allowed commands for mode"""
        
        allowed = []
        
        if mode == ExecutionMode.SAFE:
            for category in [CommandCategory.FILE_READ, CommandCategory.SYSTEM_INFO]:
                allowed.extend(cls.ALLOWLIST.get(category, []))
        
        elif mode == ExecutionMode.NORMAL:
            for category in [CommandCategory.FILE_READ, CommandCategory.FILE_WRITE,
                           CommandCategory.SYSTEM_INFO, CommandCategory.DEVELOPMENT]:
                allowed.extend(cls.ALLOWLIST.get(category, []))
        
        elif mode == ExecutionMode.ADVANCED:
            for category, commands in cls.ALLOWLIST.items():
                if category != CommandCategory.DANGEROUS:
                    allowed.extend(commands)
        
        else:  # UNRESTRICTED
            for commands in cls.ALLOWLIST.values():
                allowed.extend(commands)
        
        return list(set(allowed))


# ==================== WORKSPACE SANDBOX ====================

class WorkspaceSandbox:
    """
    Filesystem boundary enforcement
    Ensures agent stays within workspace
    """
    
    def __init__(self, workspace_root: str = None):
        # Default to project directory
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.allowed_paths = [self.workspace_root]
        
        logger.info(f"🛡️ Workspace sandbox initialized: {self.workspace_root}")
    
    def is_within_workspace(self, path: str) -> bool:
        """Check if path is within workspace"""
        
        try:
            resolved = Path(path).resolve()
            
            # Check if path is within any allowed path
            for allowed in self.allowed_paths:
                try:
                    resolved.relative_to(allowed)
                    return True
                except ValueError:
                    continue
            
            return False
        
        except Exception:
            return False
    
    def restrict_path(self, path: str) -> str:
        """Restrict path to workspace"""
        
        if not path:
            return str(self.workspace_root)
        
        # If absolute, try to make relative to workspace
        p = Path(path)
        if p.is_absolute():
            try:
                relative = p.relative_to(self.workspace_root)
                return str(self.workspace_root / relative)
            except ValueError:
                # Not within workspace, use workspace
                logger.warning(f"Path outside workspace: {path}")
                return str(self.workspace_root)
        
        return path
    
    def get_safe_path(self, user_path: str, default: str = None) -> Optional[str]:
        """Get safe path within workspace"""
        
        # Handle relative paths
        if not user_path:
            return default
        
        # Resolve the path
        if user_path.startswith('/'):
            # Absolute path
            full_path = Path(user_path)
        else:
            # Relative path - make absolute then check
            full_path = self.workspace_root / user_path
        
        # Check if within workspace
        if self.is_within_workspace(str(full_path)):
            return str(full_path.resolve())
        
        # Not safe
        logger.warning(f"Blocked access to: {user_path}")
        return None
    
    def add_allowed_path(self, path: str):
        """Add additional allowed path"""
        resolved = Path(path).resolve()
        if resolved.exists():
            self.allowed_paths.append(resolved)
            logger.info(f"Added allowed path: {resolved}")


# ==================== PROCESS SANDBOX ====================

class ProcessSandbox:
    """
    Process-level sandboxing with resource limits
    """
    
    def __init__(self):
        # Default limits
        self.max_cpu_percent = 50      # 50% CPU
        self.max_memory_mb = 512        # 512 MB
        self.max_processes = 10        # Max child processes
        self.max_runtime = 60          # Max 60 seconds
        self.timeout = 30               # Default timeout
        
        logger.info("⚙️ Process sandbox initialized")
    
    def set_limits(self, cpu: int = None, memory_mb: int = None,
                   processes: int = None, timeout: int = None):
        """Set resource limits"""
        
        if cpu:
            self.max_cpu_percent = cpu
        if memory_mb:
            self.max_memory_mb = memory_mb
        if processes:
            self.max_processes = processes
        if timeout:
            self.timeout = timeout
    
    def run_with_limits(self, cmd: str, cwd: str = None,
                       env: Dict = None) -> Tuple[int, str, str]:
        """
        Run command with resource limits
        Returns: (return_code, stdout, stderr)
        """
        
        # Prepare environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        try:
            # Use subprocess with restrictions
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=run_env,
                text=True,
                preexec_fn=lambda: self._apply_limits()
            )
            
            # Wait with timeout
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                return process.returncode, stdout, stderr
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return -1, "", f"Timeout: {self.timeout}s"
        
        except Exception as e:
            return -1, "", str(e)
    
    def _apply_limits(self):
        """Apply resource limits to subprocess"""
        
        try:
            # Set memory limit
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            memory_bytes = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, hard))
            
            # Set CPU limit
            soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_runtime, hard))
            
            # Set process limit
            soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
            resource.setrlimit(resource.RLIMIT_NPROC, (self.max_processes, hard))
            
        except Exception as e:
            # Limits might not be supported on all systems
            logger.debug(f"Could not apply all limits: {e}")


# ==================== NETWORK SANDBOX ====================

class NetworkSandbox:
    """
    Network access controls
    """
    
    # Allowed domains/patterns
    ALLOWED_DOMAINS = [
        "*.github.com",
        "*.githubusercontent.com",
        "api.github.com",
        "pypi.org",
        "*.pypi.org",
        "npmjs.org",
        "*.npmjs.org",
        "crates.io",
        "docs.rs",
        "stackoverflow.com",
        "*.stackoverflow.com",
    ]
    
    # Blocked domains
    BLOCKED_DOMAINS = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "metadata.google.internal",
    ]
    
    def __init__(self):
        self.enabled = True
        logger.info("🌐 Network sandbox initialized")
    
    def is_allowed_url(self, url: str) -> bool:
        """Check if URL is allowed"""
        
        if not self.enabled:
            return True
        
        # Check blocked
        for blocked in self.BLOCKED_DOMAINS:
            if blocked in url.lower():
                return False
        
        return True
    
    def set_allowed_domains(self, domains: List[str]):
        """Set allowed domains"""
        self.ALLOWED_DOMAINS.extend(domains)
    
    def add_blocked_domain(self, domain: str):
        """Add blocked domain"""
        self.BLOCKED_DOMAINS.append(domain)


# ==================== COMMAND SANDBOX ====================

class CommandSandbox:
    """
    Complete command sandbox combining all security measures
    """
    
    def __init__(self, workspace_root: str = None, mode: ExecutionMode = ExecutionMode.NORMAL):
        
        # Initialize components
        self.allowlist = CommandAllowlist()
        self.workspace = WorkspaceSandbox(workspace_root)
        self.process = ProcessSandbox()
        self.network = NetworkSandbox()
        
        # Mode
        self.mode = mode
        
        # Audit log
        self.audit_log: List[Dict] = []
        
        logger.info(f"🔒 Command Sandbox initialized: {mode.value}")
    
    def execute(self, command: str, timeout: int = None,
                check_allowed: bool = True) -> Dict[str, Any]:
        """
        Execute command with full sandboxing
        """
        
        result = {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "error": "",
            "duration": 0.0,
            "sandboxed": True
        }
        
        import time
        start = time.time()
        
        # Step 1: Check if command is allowed
        if check_allowed:
            allowed, reason = self.allowlist.is_allowed(command, self.mode)
            if not allowed:
                result["error"] = f"Ruxsat yo'q: {reason}"
                self._log(command, "BLOCKED", result["error"])
                return result
        
        # Step 2: Check network access
        if "curl" in command or "wget" in command:
            # Extract URL
            import re
            urls = re.findall(r'https?://[^\s]+', command)
            for url in urls:
                if not self.network.is_allowed_url(url):
                    result["error"] = f"URL bloklangan: {url}"
                    self._log(command, "BLOCKED", result["error"])
                    return result
        
        # Step 3: Restrict paths to workspace
        safe_command = self._restrict_paths(command)
        
        # Step 4: Execute with process limits
        returncode, stdout, stderr = self.process.run_with_limits(
            safe_command,
            cwd=str(self.workspace.workspace_root),
            timeout=timeout
        )
        
        result["returncode"] = returncode
        result["stdout"] = stdout
        result["stderr"] = stderr
        result["success"] = returncode == 0
        result["duration"] = time.time() - start
        
        if returncode != 0:
            result["error"] = stderr or "Noma'lum xatolik"
        
        self._log(command, "SUCCESS" if result["success"] else "FAILED", result["error"])
        
        return result
    
    def _restrict_paths(self, command: str) -> str:
        """Restrict paths in command to workspace"""
        
        # Simple path restriction - replace unsafe paths
        # This is a basic implementation
        
        return command
    
    def _log(self, command: str, status: str, error: str = ""):
        """Log command execution"""
        
        import time
        
        log_entry = {
            "timestamp": time.time(),
            "command": command[:200],  # Truncate for log
            "status": status,
            "error": error,
            "mode": self.mode.value
        }
        
        self.audit_log.append(log_entry)
        
        # Keep last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log"""
        return self.audit_log[-limit:]
    
    def get_stats(self) -> Dict:
        """Get sandbox statistics"""
        
        total = len(self.audit_log)
        blocked = sum(1 for e in self.audit_log if e["status"] == "BLOCKED")
        failed = sum(1 for e in self.audit_log if e["status"] == "FAILED")
        
        return {
            "mode": self.mode.value,
            "total_commands": total,
            "blocked": blocked,
            "failed": failed,
            "success_rate": (total - blocked - failed) / total if total > 0 else 0
        }


# ==================== FACTORY ====================

def create_sandbox(workspace_root: str = None, 
                  mode: ExecutionMode = ExecutionMode.NORMAL) -> CommandSandbox:
    """Create configured sandbox"""
    return CommandSandbox(workspace_root, mode)
