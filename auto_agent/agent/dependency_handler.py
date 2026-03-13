"""
OmniAgent X - Dependency Handler
===============================
Multi-package manager support

Supports:
- pip, npm, cargo, poetry, uv
- Auto-detection of project type
- Lock file management
- Install retries
- Cache management
"""
import os
import subprocess
import logging
import json
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import time

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class PackageManager(Enum):
    """Supported package managers"""
    PIP = "pip"
    NPM = "npm"
    YARN = "yarn"
    CARGO = "cargo"
    POETRY = "poetry"
    UV = "uv"
    PNPM = "pnpm"


@dataclass
class Dependency:
    """Dependency information"""
    name: str
    version: Optional[str]
    manager: PackageManager
    is_dev: bool = False


@dataclass
class InstallResult:
    """Installation result"""
    success: bool
    packages: List[str]
    errors: List[str]
    duration: float


# ==================== DEPENDENCY DETECTOR ====================

class DependencyDetector:
    """
    Detect project type and package manager
    """
    
    @staticmethod
    def detect(root_dir: str = ".") -> List[PackageManager]:
        """Detect package managers from project files"""
        
        root = Path(root_dir)
        detected = []
        
        # Check for lock files and manifests
        if (root / "requirements.txt").exists():
            detected.append(PackageManager.PIP)
        
        if (root / "pyproject.toml").exists():
            # Check if poetry or uv
            with open(root / "pyproject.toml") as f:
                content = f.read()
                if "tool.poetry" in content:
                    detected.append(PackageManager.POETRY)
                if "tool.uv" in content:
                    detected.append(PackageManager.UV)
        
        if (root / "uv.lock").exists():
            detected.append(PackageManager.UV)
        
        if (root / "package.json").exists():
            detected.append(PackageManager.NPM)
            if (root / "yarn.lock").exists():
                detected.append(PackageManager.YARN)
            if (root / "pnpm-lock.yaml").exists():
                detected.append(PackageManager.PNPM)
        
        if (root / "Cargo.toml").exists():
            detected.append(PackageManager.CARGO)
        
        # Default to pip if nothing found
        if not detected:
            detected.append(PackageManager.PIP)
        
        return detected
    
    @staticmethod
    def get_lock_file(manager: PackageManager) -> Optional[str]:
        """Get lock file name for manager"""
        
        lock_files = {
            PackageManager.PIP: "requirements.lock",
            PackageManager.POETRY: "poetry.lock",
            PackageManager.UV: "uv.lock",
            PackageManager.NPM: "package-lock.json",
            PackageManager.YARN: "yarn.lock",
            PackageManager.PNPM: "pnpm-lock.yaml",
            PackageManager.CARGO: "Cargo.lock",
        }
        
        return lock_files.get(manager)


# ==================== DEPENDENCY INSTALLER ====================

class DependencyInstaller:
    """
    Install dependencies across package managers
    """
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        
        # Cache
        self.cache_dir = self.workspace_dir / ".dep_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Settings
        self.max_retries = 3
        self.retry_delay = 2
        
        logger.info("📦 Dependency Installer initialized")
    
    def install(self, packages: List[str], manager: PackageManager = PackageManager.PIP,
               is_dev: bool = False, extra_index: str = None) -> InstallResult:
        """Install packages"""
        
        start_time = time.time()
        errors = []
        installed = []
        
        for attempt in range(self.max_retries):
            try:
                # Build command
                cmd = self._build_install_cmd(manager, packages, is_dev, extra_index)
                
                # Execute
                result = subprocess.run(
                    cmd,
                    cwd=str(self.workspace_dir),
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    installed = packages
                    break
                else:
                    errors.append(result.stderr)
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    else:
                        errors.append(f"Failed after {self.max_retries} attempts")
            
            except subprocess.TimeoutExpired:
                errors.append("Installation timeout")
            except Exception as e:
                errors.append(str(e))
        
        return InstallResult(
            success=len(installed) > 0,
            packages=installed,
            errors=errors,
            duration=time.time() - start_time
        )
    
    def _build_install_cmd(self, manager: PackageManager, packages: List[str],
                          is_dev: bool, extra_index: str = None) -> List[str]:
        """Build install command"""
        
        if manager == PackageManager.PIP:
            cmd = ["pip", "install"]
            if is_dev:
                cmd.append("-dev")
            if extra_index:
                cmd.extend(["--index-url", extra_index])
            cmd.extend(packages)
        
        elif manager == PackageManager.UV:
            cmd = ["uv", "pip", "install"]
            if is_dev:
                cmd.append("--dev")
            if extra_index:
                cmd.extend(["--index-url", extra_index])
            cmd.extend(packages)
        
        elif manager == PackageManager.POETRY:
            cmd = ["poetry", "add"]
            if is_dev:
                cmd.append("--dev")
            cmd.extend(packages)
        
        elif manager == PackageManager.NPM:
            cmd = ["npm", "install"]
            if is_dev:
                cmd.append("--save-dev")
            cmd.extend(packages)
        
        elif manager == PackageManager.YARN:
            cmd = ["yarn", "add"]
            if is_dev:
                cmd.append("--dev")
            cmd.extend(packages)
        
        elif manager == PackageManager.CARGO:
            cmd = ["cargo", "add"]
            if is_dev:
                cmd.append("--dev")
            cmd.extend(packages)
        
        else:
            cmd = ["pip", "install"] + packages
        
        return cmd
    
    def sync(self, manager: PackageManager) -> InstallResult:
        """Sync all dependencies from lock file"""
        
        start_time = time.time()
        
        try:
            if manager == PackageManager.PIP:
                cmd = ["pip", "install", "-r", "requirements.txt"]
            elif manager == PackageManager.UV:
                cmd = ["uv", "pip", "sync"]
            elif manager == PackageManager.POETRY:
                cmd = ["poetry", "install"]
            elif manager in [PackageManager.NPM, PackageManager.YARN, PackageManager.PNPM]:
                cmd = ["npm", "install"]  # or yarn/pnpm
            elif manager == PackageManager.CARGO:
                cmd = ["cargo", "build"]
            else:
                return InstallResult(False, [], ["Unknown manager"], 0)
            
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return InstallResult(
                success=result.returncode == 0,
                packages=[],
                errors=[result.stderr] if result.returncode != 0 else [],
                duration=time.time() - start_time
            )
        
        except Exception as e:
            return InstallResult(False, [], [str(e)], time.time() - start_time)
    
    def list_installed(self, manager: PackageManager) -> List[Dependency]:
        """List installed packages"""
        
        packages = []
        
        try:
            if manager == PackageManager.PIP:
                result = subprocess.run(
                    ["pip", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    for pkg in data:
                        packages.append(Dependency(
                            name=pkg["name"],
                            version=pkg["version"],
                            manager=PackageManager.PIP
                        ))
            
            elif manager == PackageManager.NPM:
                result = subprocess.run(
                    ["npm", "list", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    deps = data.get("dependencies", {})
                    for name, info in deps.items():
                        packages.append(Dependency(
                            name=name,
                            version=info.get("version"),
                            manager=PackageManager.NPM
                        ))
            
            elif manager == PackageManager.CARGO:
                result = subprocess.run(
                    ["cargo", "tree", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Parse cargo tree output
                # Simplified
        
        except Exception as e:
            logger.error(f"Error listing packages: {e}")
        
        return packages
    
    def get_outdated(self, manager: PackageManager) -> List[Dict]:
        """Get outdated packages"""
        
        outdated = []
        
        try:
            if manager == PackageManager.PIP:
                result = subprocess.run(
                    ["pip", "list", "--outdated", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    for pkg in data:
                        outdated.append({
                            "name": pkg["name"],
                            "current": pkg["version"],
                            "latest": pkg["latest_version"],
                            "type": pkg["type"]
                        })
        
        except Exception as e:
            logger.error(f"Error checking outdated: {e}")
        
        return outdated
    
    def update(self, packages: List[str], manager: PackageManager) -> InstallResult:
        """Update specific packages"""
        
        start_time = time.time()
        
        try:
            if manager == PackageManager.PIP:
                cmd = ["pip", "install", "--upgrade"] + packages
            elif manager == PackageManager.UV:
                cmd = ["uv", "pip", "install", "--upgrade"] + packages
            elif manager == PackageManager.NPM:
                cmd = ["npm", "update"] + packages
            else:
                return InstallResult(False, [], ["Manager not supported"], 0)
            
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return InstallResult(
                success=result.returncode == 0,
                packages=packages,
                errors=[result.stderr] if result.returncode != 0 else [],
                duration=time.time() - start_time
            )
        
        except Exception as e:
            return InstallResult(False, [], [str(e)], time.time() - start_time)


# ==================== MANAGER ====================

class DependencyManager:
    """
    Unified dependency management
    """
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        
        # Auto-detect managers
        self.managers = DependencyDetector.detect(str(self.workspace_dir))
        
        # Create installers
        self.installers = {m: DependencyInstaller(str(self.workspace_dir)) 
                         for m in self.managers}
        
        logger.info(f"📦 Dependency Manager initialized: {[m.value for m in self.managers]}")
    
    def install_package(self, package: str, manager: PackageManager = None) -> InstallResult:
        """Install a single package"""
        
        if manager is None:
            manager = self.managers[0] if self.managers else PackageManager.PIP
        
        return self.installers[manager].install([package], manager)
    
    def install_requirements(self, requirements_file: str = "requirements.txt") -> InstallResult:
        """Install from requirements file"""
        
        manager = PackageManager.PIP
        if PackageManager.UV in self.managers:
            manager = PackageManager.UV
        
        return self.installers[manager].install(
            self._read_requirements(requirements_file),
            manager
        )
    
    def _read_requirements(self, filepath: str) -> List[str]:
        """Read requirements from file"""
        
        try:
            with open(filepath) as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except:
            return []
    
    def sync_all(self) -> Dict[str, InstallResult]:
        """Sync all detected package managers"""
        
        results = {}
        
        for manager in self.managers:
            result = self.installers[manager].sync(manager)
            results[manager.value] = result
        
        return results


# ==================== FACTORY ====================

def create_dependency_manager(workspace_dir: str = None) -> DependencyManager:
    """Create dependency manager"""
    return DependencyManager(workspace_dir)
