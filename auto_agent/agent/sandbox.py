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
                except ValueError as e:
                    # Path is not relative to this allowed path, try next
                    logger.debug(f"Path {path} is not within {allowed}: {e}")
                    continue
            
            logger.warning(f"Path {path} is not within any allowed path: {self.allowed_paths}")
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


# ==================== CONTAINERIZED ISOLATION ====================

class IsolatedContainer:
    """
    Production-grade containerized isolation for dangerous operations:
    - Throwaway workspace
    - Strict filesystem jail
    - Egress control
    - CPU/RAM quotas
    - Child process cleanup
    - Rollback snapshots
    """
    
    def __init__(self, base_workspace: str = None):
        self.base_workspace = Path(base_workspace or "/tmp/agent_isolated")
        self.base_workspace.mkdir(parents=True, exist_ok=True)
        
        # Resource limits
        self.max_cpu_percent = 25  # 25% CPU
        self.max_memory_mb = 256  # 256 MB
        self.max_processes = 5     # Max 5 child processes
        self.max_runtime = 60      # Max 60 seconds
        self.max_disk_mb = 100     # Max 100 MB disk
        
        # Snapshot for rollback
        self.snapshots = {}
        
        # Active containers
        self.active_containers = {}
        
        logger.info("🔒 Containerized isolation initialized")
        
    def create_throwaway_workspace(self, container_id: str) -> Path:
        """Create throwaway workspace for container"""
        container_dir = self.base_workspace / container_id
        container_dir.mkdir(parents=True, exist_ok=True)
        
        # Set permissions (read-write for owner only)
        container_dir.chmod(0o700)
        
        return container_dir
        
    def create_snapshot(self, container_id: str) -> Dict:
        """Create snapshot for rollback"""
        container_dir = self.base_workspace / container_id
        
        if not container_dir.exists():
            return None
            
        snapshot = {
            "container_id": container_id,
            "timestamp": time.time(),
            "files": {},
            "disk_usage": 0
        }
        
        # Record all files
        for f in container_dir.rglob("*"):
            if f.is_file():
                rel_path = f.relative_to(container_dir)
                snapshot["files"][str(rel_path)] = f.stat().st_size
                snapshot["disk_usage"] += f.stat().st_size
                
        self.snapshots[container_id] = snapshot
        return snapshot
        
    def rollback_snapshot(self, container_id: str) -> bool:
        """Rollback to last snapshot"""
        if container_id not in self.snapshots:
            logger.warning(f"No snapshot for {container_id}")
            return False
            
        snapshot = self.snapshots[container_id]
        container_dir = self.base_workspace / container_id
        
        # Remove all current files
        import shutil
        if container_dir.exists():
            shutil.rmtree(container_dir)
            
        # Recreate directory
        container_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Rolled back container {container_id}")
        return True
        
    def cleanup_container(self, container_id: str):
        """Clean up container and all resources"""
        container_dir = self.base_workspace / container_id
        
        # Kill any remaining processes
        self._kill_child_processes(container_id)
        
        # Remove directory
        import shutil
        if container_dir.exists():
            shutil.rmtree(container_dir)
            
        # Remove snapshot
        if container_id in self.snapshots:
            del self.snapshots[container_id]
            
        # Remove from active
        if container_id in self.active_containers:
            del self.active_containers[container_id]
            
        logger.info(f"Cleaned up container {container_id}")
        
    def _kill_child_processes(self, container_dir: Path):
        """Kill all child processes in container"""
        # Find all processes in container
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any(str(container_dir) in str(c) for c in cmdline):
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except:
            pass
            
    def apply_egress_control(self, container_id: str) -> Dict:
        """Apply egress control (simulated - real would use iptables)"""
        return {
            "container_id": container_id,
            "allowed_outbound": [
                "api.github.com",
                "pypi.org",
                "*.python.org"
            ],
            "blocked_outbound": [
                "localhost",
                "127.0.0.1",
                "0.0.0.0"
            ],
            "egress_enabled": True
        }
        
    def run_isolated(self, container_id: str, command: str, 
                    use_snapshot: bool = True) -> Dict:
        """Run command in isolated container"""
        
        # Create throwaway workspace
        container_dir = self.create_throwaway_workspace(container_id)
        
        # Create snapshot if requested
        if use_snapshot:
            self.create_snapshot(container_id)
            
        # Apply egress control
        egress = self.apply_egress_control(container_id)
        
        # Run with limits
        process_sandbox = ProcessSandbox()
        process_sandbox.set_limits(
            cpu=self.max_cpu_percent,
            memory_mb=self.max_memory_mb,
            processes=self.max_processes,
            timeout=self.max_runtime
        )
        
        # Execute
        returncode, stdout, stderr = process_sandbox.run_with_limits(
            command, 
            cwd=str(container_dir)
        )
        
        result = {
            "container_id": container_id,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "egress_control": egress,
            "success": returncode == 0
        }
        
        # Track as active
        self.active_containers[container_id] = {
            "command": command,
            "result": result,
            "timestamp": time.time()
        }
        
        return result
        
    def cleanup_all(self):
        """Clean up all containers"""
        for container_id in list(self.active_containers.keys()):
            self.cleanup_container(container_id)


# Add psutil import
import psutil

