"""
================================================================================
LAYER 4: CLONE KNOWLEDGE LAYER
================================================================================
Clone o'zini o'zgartirishdan oldin o'z tuzilishini tushunishi kerak.

Bu qavat quyidagilarni qiladi:
- repo map
- module dependency graph
- critical path analysis
- hot files
- risky files
- extension points
- config surfaces
- tool registry
- benchmark registry

Nega kerak:

Aks holda clone:
- noto'g'ri faylga patch qiladi
- keraksiz katta refactor qiladi
- coupling'ni buzadi
- testsiz joyga kiradi

MUHIM: Self-Model Graph

Bu agentning o'zi haqida bilim grafi:
- qaysi capability qaysi modulga bog'langan
- qaysi tool qayerda ulanadi
- qaysi benchmark qaysi capability'ni o'lchaydi
- qaysi config nimaga ta'sir qiladi

Bu bo'lmasa self-edit ko'r ishlaydi.
================================================================================
"""
import os
import sys
import json
import logging
import time
import shutil
import ast
import hashlib
import subprocess
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum

from .clone_factory import CloneFactory

logger = logging.getLogger(__name__)


# ================================================================================
# REPOSITORY MAP - Repozitory xaritasi
# ================================================================================

class RepositoryMapper:
    """
    Repository Mapper - Repozitory tuzilmasini xaritalash
    
    Bu class:
    1. Repozitory strukturasini aniqlaydi
    2. Modullar orasidagi bog'liqliklarni topadi
    3. Muhim fayllarni belgilaydi
    4. Extension point larni aniqlaydi
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl: int = 300  # 5 daqiqa
        
        logger.info("🗺️ Repository Mapper initialized")
    
    def map_repository(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Repozitory xaritasini yaratish
        
        Args:
            force_refresh: Cache ni ignore qilish
        
        Returns:
            Dict: Repozitory xaritasi
        """
        # Cache check
        if not force_refresh and time.time() - self._cache_time < self._cache_ttl:
            return self._cache
        
        try:
            repo_map = {
                "root": str(self.workspace_root),
                "structure": self._scan_structure(),
                "modules": self._find_modules(),
                "dependencies": self._analyze_dependencies(),
                "entry_points": self._find_entry_points(),
                "config_files": self._find_config_files(),
                "test_files": self._find_test_files(),
                "extension_points": self._find_extension_points(),
                "hot_files": self._identify_hot_files(),
                "risky_files": self._identify_risky_files(),
            }
            
            self._cache = repo_map
            self._cache_time = time.time()
            
            logger.info(f"✅ Repository mapped: {len(repo_map['modules'])} modules")
            return repo_map
            
        except Exception as e:
            logger.error(f"Repository mapping failed: {e}")
            return {"error": str(e)}
    
    def _scan_structure(self) -> Dict:
        """Strukturani skanerlash"""
        structure = {}
        
        for root, dirs, files in os.walk(self.workspace_root):
            # Skip hidden and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', '.venv']]
            
            rel_path = Path(root).relative_to(self.workspace_root)
            level = len(rel_path.parts)
            
            if level > 3:  # Max 3 levels deep
                continue
            
            structure[str(rel_path)] = {
                "dirs": dirs,
                "files": [f for f in files if not f.startswith('.') and not f.endswith('.pyc')]
            }
        
        return structure
    
    def _find_modules(self) -> List[Dict]:
        """Modullarni topish"""
        modules = []
        
        for py_file in self.workspace_root.rglob("*.py"):
            # Skip hidden and cache
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            rel_path = py_file.relative_to(self.workspace_root)
            
            # Analyze Python file
            module_info = {
                "path": str(rel_path),
                "name": py_file.stem,
                "is_package": (py_file / "__init__.py").exists(),
                "size": py_file.stat().st_size if py_file.exists() else 0,
            }
            
            # Try to extract classes and functions
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    
                tree = ast.parse(content)
                
                classes = []
                functions = []
                imports = []
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        functions.append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                
                module_info["classes"] = classes
                module_info["functions"] = functions
                module_info["imports"] = imports[:20]  # Limit
                
            except Exception as e:
                logger.debug(f"Could not parse {py_file}: {e}")
            
            modules.append(module_info)
        
        return modules
    
    def _analyze_dependencies(self) -> Dict:
        """Bog'liqliklarni tahlil qilish"""
        dependencies = defaultdict(set)
        
        # Scan imports
        for py_file in self.workspace_root.rglob("*.py"):
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                current_module = py_file.stem
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            dependencies[current_module].add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            dependencies[current_module].add(node.module.split('.')[0])
                            
            except:
                pass
        
        return {k: list(v) for k, v in dependencies.items()}
    
    def _find_entry_points(self) -> List[str]:
        """Entry point larni topish"""
        entry_points = []
        
        # Look for main files
        for name in ['main.py', 'app.py', 'run.py', 'server.py', '__main__.py']:
            for py_file in self.workspace_root.rglob(name):
                if not any(p.startswith('.') for p in py_file.parts):
                    entry_points.append(str(py_file.relative_to(self.workspace_root)))
        
        # Look for if __name__ == "__main__"
        for py_file in self.workspace_root.rglob("*.py"):
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                if '__name__' in content and '__main__' in content:
                    entry_points.append(str(py_file.relative_to(self.workspace_root)))
            except:
                pass
        
        return entry_points
    
    def _find_config_files(self) -> List[str]:
        """Config fayllarni topish"""
        config_patterns = ['*.json', '*.yaml', '*.yml', '*.toml', '*.ini', '*.cfg', 
                          '*.env', 'requirements*.txt', 'setup.py', 'pyproject.toml']
        
        config_files = []
        
        for pattern in config_patterns:
            for f in self.workspace_root.rglob(pattern):
                if not any(p.startswith('.') for p in f.parts):
                    config_files.append(str(f.relative_to(self.workspace_root)))
        
        return config_files
    
    def _find_test_files(self) -> List[str]:
        """Test fayllarni topish"""
        test_files = []
        
        for pattern in ['test_*.py', '*_test.py', 'tests.py']:
            for f in self.workspace_root.rglob(pattern):
                if not any(p.startswith('.') for p in f.parts):
                    test_files.append(str(f.relative_to(self.workspace_root)))
        
        # Also check tests directories
        for tests_dir in self.workspace_root.rglob('tests'):
            if not any(p.startswith('.') for p in tests_dir.parts):
                for f in tests_dir.rglob('*.py'):
                    if not any(p.startswith('.') for p in f.parts):
                        test_files.append(str(f.relative_to(self.workspace_root)))
        
        return test_files
    
    def _find_extension_points(self) -> List[Dict]:
        """Extension point larni topish"""
        extension_points = []
        
        # Patterns to find extension points
        patterns = [
            ("register_", "registration"),
            ("plugin_", "plugin"),
            ("factory_", "factory"),
            ("create_", "factory"),
            ("hook_", "hook"),
            ("event_", "event"),
            ("signal_", "signal"),
            ("middleware", "middleware"),
            ("extension", "extension"),
        ]
        
        for py_file in self.workspace_root.rglob("*.py"):
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for pattern, ptype in patterns:
                            if pattern in node.name.lower():
                                extension_points.append({
                                    "file": str(py_file.relative_to(self.workspace_root)),
                                    "function": node.name,
                                    "type": ptype,
                                    "line": node.lineno
                                })
                            
            except:
                pass
        
        return extension_points
    
    def _identify_hot_files(self) -> List[str]:
        """Ko'p ishlatiladigan (hot) fayllarni aniqlash"""
        # Import frequency bo'yicha
        import_count = defaultdict(int)
        
        for py_file in self.workspace_root.rglob("*.py"):
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Count imports of other files
                for other_file in self.workspace_root.rglob("*.py"):
                    if other_file == py_file:
                        continue
                    module_name = other_file.stem
                    if module_name in content:
                        import_count[module_name] += 1
                        
            except:
                pass
        
        # Sort by count
        hot = sorted(import_count.items(), key=lambda x: x[1], reverse=True)
        return [f"{m}.py" for m, c in hot[:20]]
    
    def _identify_risky_files(self) -> List[str]:
        """Riskli fayllarni aniqlash"""
        risky = []
        
        risk_patterns = [
            "kernel", "core", "main", "security", "auth", "secret",
            "database", "db", "migration", "deploy", "production"
        ]
        
        for py_file in self.workspace_root.rglob("*.py"):
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            path_str = str(py_file.relative_to(self.workspace_root)).lower()
            
            for pattern in risk_patterns:
                if pattern in path_str:
                    risky.append(str(py_file.relative_to(self.workspace_root)))
                    break
        
        return risky


# ================================================================================
# SELF-MODEL GRAPH - O'zi haqida bilim grafi
# ================================================================================

class SelfModelGraph:
    """
    Self-Model Graph - Agentning o'zi haqida bilim grafi
    
    Bu graph quyidagilarni o'z ichiga oladi:
    - qaysi capability qaysi modulga bog'langan
    - qaysi tool qayerda ulanadi
    - qaysi benchmark qaysi capability'ni o'lchaydi
    - qaysi config nimaga ta'sir qiladi
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self._graph: Dict[str, Any] = {
            "capabilities": {},      # capability -> modules
            "modules": {},          # module -> capabilities, tools, benchmarks
            "tools": {},            # tool -> module, dependencies
            "benchmarks": {},       # benchmark -> capability, metrics
            "configs": {},          # config -> affected modules
            "edges": []             # relationships
        }
        
        logger.info("🧠 Self-Model Graph initialized")
    
    def build_graph(self) -> Dict:
        """
        Self-model graph yaratish
        
        Returns:
            Dict: Graph ma'lumotlari
        """
        try:
            # 1. Capabilities ni aniqlash
            self._identify_capabilities()
            
            # 2. Module-Capability bog'liqliklari
            self._map_modules_to_capabilities()
            
            # 3. Tools va ularning bog'liqliklari
            self._identify_tools()
            
            # 4. Benchmarks
            self._identify_benchmarks()
            
            # 5. Configs
            self._identify_configs()
            
            # 6. Edges
            self._build_edges()
            
            logger.info(f"✅ Self-Model Graph built: {len(self._graph['capabilities'])} capabilities")
            return self._graph
            
        except Exception as e:
            logger.error(f"Graph building failed: {e}")
            return {"error": str(e)}
    
    def _identify_capabilities(self):
        """Capability larni aniqlash"""
        capabilities = {
            "code_execution": {
                "description": "Code execution and interpretation",
                "modules": ["code_interpreter", "code_engine"],
            },
            "file_operations": {
                "description": "File reading, writing, and management",
                "modules": ["tools", "file_tools"],
            },
            "web_browsing": {
                "description": "Web browsing and scraping",
                "modules": ["browser", "playwright_browser"],
            },
            "memory": {
                "description": "Memory and knowledge storage",
                "modules": ["memory", "memory_ultimate", "agent_memory"],
            },
            "planning": {
                "description": "Task planning and decomposition",
                "modules": ["planner", "kernel"],
            },
            "tool_creation": {
                "description": "Dynamic tool creation",
                "modules": ["tool_factory"],
            },
            "learning": {
                "description": "Self-learning and improvement",
                "modules": ["self_improvement", "learning_pipeline"],
            },
            "benchmarking": {
                "description": "Performance benchmarking",
                "modules": ["benchmark", "regression_suite"],
            },
            "security": {
                "description": "Security and secret management",
                "modules": ["secret_guard", "sandbox"],
            },
            "telemetry": {
                "description": "Error tracking and telemetry",
                "modules": ["health_check", "telemetry"],
            }
        }
        
        self._graph["capabilities"] = capabilities
    
    def _map_modules_to_capabilities(self):
        """Module larni capability lerga bog'lash"""
        for cap_name, cap_info in self._graph["capabilities"].items():
            for module_name in cap_info.get("modules", []):
                if module_name not in self._graph["modules"]:
                    self._graph["modules"][module_name] = {
                        "capabilities": [],
                        "tools": [],
                        "benchmarks": []
                    }
                self._graph["modules"][module_name]["capabilities"].append(cap_name)
    
    def _identify_tools(self):
        """Tool larni aniqlash"""
        # Tool registry ni skanerlash
        tools = {}
        
        for py_file in self.workspace_root.rglob("tools.py"):
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Find tool definitions (decorators, classes, functions)
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check for tool patterns
                        if any(p in node.name.lower() for p in ['tool', 'execute', 'run']):
                            tools[node.name] = {
                                "module": str(py_file.relative_to(self.workspace_root)),
                                "type": "function"
                            }
                            
            except:
                pass
        
        self._graph["tools"] = tools
    
    def _identify_benchmarks(self):
        """Benchmark larni aniqlash"""
        benchmarks = {}
        
        # Look for benchmark files
        for py_file in self.workspace_root.rglob("benchmark*.py"):
            if any(p.startswith('.') for p in py_file.parts):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Find benchmark functions
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        if 'benchmark' in node.name.lower() or 'test' in node.name.lower():
                            benchmarks[node.name] = {
                                "file": str(py_file.relative_to(self.workspace_root)),
                                "type": "class" if isinstance(node, ast.ClassDef) else "function"
                            }
                            
            except:
                pass
        
        self._graph["benchmarks"] = benchmarks
    
    def _identify_configs(self):
        """Config larni aniqlash"""
        configs = {}
        
        # Look for config files
        for pattern in ["config*.py", "settings*.py", "*_config.py"]:
            for py_file in self.workspace_root.rglob(pattern):
                if any(p.startswith('.') for p in py_file.parts):
                    continue
                
                configs[str(py_file.relative_to(self.workspace_root))] = {
                    "type": "python"
                }
        
        # Look for env files
        for env_file in self.workspace_root.rglob(".env*"):
            if not any(p.startswith('.') for p in env_file.parts[:-1]):
                configs[str(env_file.relative_to(self.workspace_root))] = {
                    "type": "env"
                }
        
        self._graph["configs"] = configs
    
    def _build_edges(self):
        """Graph edges yaratish"""
        edges = []
        
        # Module -> Capability edges
        for module, info in self._graph["modules"].items():
            for cap in info.get("capabilities", []):
                edges.append({
                    "from": module,
                    "to": cap,
                    "type": "implements"
                })
        
        # Tool -> Module edges
        for tool, info in self._graph["tools"].items():
            module = info.get("module", "")
            edges.append({
                "from": tool,
                "to": module,
                "type": "defined_in"
            })
        
        self._graph["edges"] = edges
    
    def get_capability_path(self, capability: str) -> List[str]:
        """Capability ga yetib borish yo'lini olish"""
        path = []
        
        if capability in self._graph["capabilities"]:
            path.append(capability)
            
            # Find modules
            for module, info in self._graph["modules"].items():
                if capability in info.get("capabilities", []):
                    path.append(module)
        
        return path
    
    def get_module_dependencies(self, module: str) -> Dict:
        """Module bog'liqliklarini olish"""
        deps = {
            "implements": [],
            "uses_tools": [],
            "benchmarked_by": [],
            "configured_by": []
        }
        
        # Implements capability
        if module in self._graph["modules"]:
            deps["implements"] = self._graph["modules"][module].get("capabilities", [])
        
        # Uses tools
        for tool, info in self._graph["tools"].items():
            if module in str(info.get("module", "")):
                deps["uses_tools"].append(tool)
        
        # Benchmarked by
        for bench, info in self._graph["benchmarks"].items():
            if module in str(info.get("file", "")):
                deps["benchmarked_by"].append(bench)
        
        return deps
    
    def suggest_safe_extensions(self) -> List[Dict]:
        """Xavfsiz extension point larni taklif qilish"""
        suggestions = []
        
        # Find modules with extension points
        for module, info in self._graph["modules"].items():
            caps = info.get("capabilities", [])
            
            # Suggest adding new tools to capable modules
            if "tool_creation" in caps:
                suggestions.append({
                    "module": module,
                    "suggestion": "Add new tool here",
                    "risk": "low"
                })
            
            # Suggest new benchmarks
            if "benchmarking" in caps:
                suggestions.append({
                    "module": module,
                    "suggestion": "Add benchmark here",
                    "risk": "low"
                })
        
        return suggestions


# ================================================================================
# KNOWLEDGE MANAGER - Bilim boshqaruvi
# ================================================================================

class CloneKnowledgeManager:
    """
    Clone Knowledge Manager - Clone bilim qavati
    
    Bu class:
    1. Repository map yaratadi
    2. Self-model graph yaratadi
    3. Clone ga bilim beradi
    4. Safe extension points aniqlaydi
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        
        self.repo_mapper = RepositoryMapper(workspace_root)
        self.self_model = SelfModelGraph(workspace_root)
        
        # Cache
        self._knowledge_cache: Dict[str, Any] = {}
        
        logger.info("📚 Clone Knowledge Manager initialized")
    
    def analyze_for_clone(self, clone_id: str) -> Dict:
        """
        Clone uchun bilim tahlili
        
        Args:
            clone_id: Clone ID
        
        Returns:
            Dict: Clone uchun bilimlar
        """
        try:
            # Repository map
            repo_map = self.repo_mapper.map_repository()
            
            # Self-model graph
            self_model = self.self_model.build_graph()
            
            # Safe extension points
            safe_extensions = self.self_model.suggest_safe_extensions()
            
            # Hot files (should be careful with these)
            hot_files = repo_map.get("hot_files", [])
            
            # Risky files (should NOT touch these)
            risky_files = repo_map.get("risky_files", [])
            
            # Test coverage map
            test_files = repo_map.get("test_files", [])
            
            knowledge = {
                "clone_id": clone_id,
                "repository": repo_map,
                "self_model": self_model,
                "safe_extensions": safe_extensions,
                "caution_files": {
                    "hot": hot_files[:10],
                    "risky": risky_files,
                    "test": test_files[:10]
                },
                "recommendations": self._generate_recommendations(repo_map, self_model)
            }
            
            self._knowledge_cache[clone_id] = knowledge
            
            logger.info(f"📖 Knowledge analyzed for clone: {clone_id}")
            return knowledge
            
        except Exception as e:
            logger.error(f"Knowledge analysis failed: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self, repo_map: Dict, self_model: Dict) -> List[str]:
        """Takliflar yaratish"""
        recommendations = []
        
        # Safe to modify
        recommendations.append("Safe to add tools in tool_factory.py")
        recommendations.append("Safe to add benchmarks in benchmark.py")
        recommendations.append("Safe to add configs in config/")
        
        # Be careful
        recommendations.append("Be careful modifying kernel.py - core component")
        recommendations.append("Be careful modifying memory modules - data loss risk")
        
        # Don't touch
        recommendations.append("DO NOT modify secret_guard.py without approval")
        recommendations.append("DO NOT modify production settings directly")
        
        return recommendations
    
    def get_safe_files(self, clone_type: str) -> Dict[str, List[str]]:
        """
        Clone turi bo'yicha xavfsiz fayllarni olish
        
        Args:
            clone_type: Clone turi
        
        Returns:
            Dict: safe, caution, blocked fayllar
        """
        repo_map = self.repo_mapper.map_repository()
        
        safe = []
        caution = []
        blocked = []
        
        # Safe for all types
        safe.extend([
            "agent/tool_factory.py",
            "agent/benchmark.py", 
            "agent/config/",
            "agent/planner/",
        ])
        
        # Caution
        caution.extend([
            "agent/kernel.py",
            "agent/native_brain.py",
            "agent/memory*.py",
        ])
        
        # Blocked
        blocked.extend([
            "agent/secret_guard.py",
            "agent/sandbox.py",
            ".env",
            "*.pem",
            "*.key",
        ])
        
        return {
            "safe": safe,
            "caution": caution,
            "blocked": blocked
        }
    
    def get_module_info(self, module_name: str) -> Optional[Dict]:
        """Module haqida ma'lumot olish"""
        return self.self_model._graph.get("modules", {}).get(module_name)


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_knowledge_manager(workspace_root: str) -> CloneKnowledgeManager:
    """Knowledge Manager yaratish"""
    return CloneKnowledgeManager(workspace_root)
