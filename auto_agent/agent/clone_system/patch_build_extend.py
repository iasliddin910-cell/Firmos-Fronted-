"""
================================================================================
LAYER 6: PATCH / BUILD / EXTEND LAYER
================================================================================
Bu qism amaliy ishni qiladi.

U quyidagilarni bajara olishi kerak:
- kodni o'zgartirish
- config yangilash
- test yozish
- benchmark qo'shish
- tool wrapper yozish
- docs/update note yozish
- migration qilish

O'zgarish turlari:
1. small patch
2. multi-file patch
3. new tool integration
4. workflow redesign
5. prompt/policy tuning
6. benchmark addition
7. architecture extension

Men tavsiya qiladigan qoida:

Har change set uchun majburiy:
- intent
- why
- expected effect
- files touched
- risk
- revert path

Bu bo'lmasa clone nima qildi degan savolga toza javob bo'lmaydi.
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
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum

from .core_types import (
    CloneType, CloneStatus, RiskClass, ChangeType,
    PatchSet, ToolSpec
)
from .clone_factory import CloneFactory, SourceCloneManager
from .runtime_isolation import CloneRuntime
from .improvement_planner import ImprovementPlanner, PatchGenerator

logger = logging.getLogger(__name__)


# ================================================================================
# PATCH EXECUTOR
# ================================================================================

class PatchExecutor:
    """
    Patch Executor - O'zgartirishlarni qo'llash
    
    Bu class:
    1. Patch setni fayllarga qo'llaydi
    2. Codeni o'zgartiradi
    3. Config yangilaydi
    4. Files yaratadi/o'chiradi
    """
    
    def __init__(self, 
                 factory: CloneFactory,
                 source_manager: SourceCloneManager,
                 runtime: Any):
        self.factory = factory
        self.source_manager = source_manager
        self.runtime = runtime
        
        logger.info("🔧 Patch Executor initialized")
    
    def apply_patch(self, patch: PatchSet) -> Dict:
        """
        Patch ni qo'llash
        
        Args:
            patch: PatchSet
        
        Returns:
            Dict: Natijalar
        """
        clone_id = patch.clone_id
        clone_dir = self.factory.get_clone_worktree(clone_id)
        
        if not clone_dir:
            return {"success": False, "error": "Clone directory not found"}
        
        results = {
            "patch_id": patch.patch_id,
            "files_applied": [],
            "files_created": [],
            "errors": []
        }
        
        # Apply diffs
        for file_path, content in patch.diffs.items():
            try:
                target = clone_dir / file_path
                target.parent.mkdir(parents=True, exist_ok=True)
                
                with open(target, 'w') as f:
                    f.write(content)
                
                results["files_applied"].append(file_path)
                logger.info(f"✅ Applied patch: {file_path}")
                
            except Exception as e:
                results["errors"].append(f"Failed to apply {file_path}: {e}")
                logger.error(f"❌ Failed to apply patch: {file_path}: {e}")
        
        # Create new files
        for file_path in patch.files_created:
            try:
                target = clone_dir / file_path
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Empty file or default content
                with open(target, 'w') as f:
                    f.write("")
                
                results["files_created"].append(file_path)
                logger.info(f"✅ Created file: {file_path}")
                
            except Exception as e:
                results["errors"].append(f"Failed to create {file_path}: {e}")
        
        results["success"] = len(results["errors"]) == 0
        
        return results
    
    def apply_string_patch(self, clone_id: str, file_path: str, 
                          old_string: str, new_string: str) -> bool:
        """
        String patch qo'llash (find-replace)
        
        Args:
            clone_id: Clone ID
            file_path: File path
            old_string: Eski string
            new_string: Yangi string
        
        Returns:
            bool: Muvaffaqiyat
        """
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            target = clone_dir / file_path
            
            if not target.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Read file
            with open(target, 'r') as f:
                content = f.read()
            
            # Replace
            if old_string not in content:
                logger.warning(f"Old string not found in {file_path}")
                return False
            
            new_content = content.replace(old_string, new_string)
            
            # Write back
            with open(target, 'w') as f:
                f.write(new_content)
            
            logger.info(f"✅ String patch applied: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"String patch failed: {e}")
            return False
    
    def create_file(self, clone_id: str, file_path: str, content: str = "") -> bool:
        """
        Yangi file yaratish
        
        Args:
            clone_id: Clone ID
            file_path: File path
            content: Content
        
        Returns:
            bool: Muvaffaqiyat
        """
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            target = clone_dir / file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ File created: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"File creation failed: {e}")
            return False
    
    def delete_file(self, clone_id: str, file_path: str) -> bool:
        """
        File o'chirish
        
        Args:
            clone_id: Clone ID
            file_path: File path
        
        Returns:
            bool: Muvaffaqiyat
        """
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            target = clone_dir / file_path
            
            if target.exists():
                target.unlink()
                logger.info(f"🗑️ File deleted: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            return False


# ================================================================================
# TOOL ONBOARDING
# ================================================================================

class ToolOnboarding:
    """
    Tool Onboarding - Yangi tool qo'shish pipeline
    
    Tool onboarding flow:
    1. tool ehtiyoji aniqlanadi
    2. tool spec yoziladi
    3. wrapper yaratiladi
    4. permission policy belgilanadi
    5. tests yoziladi
    6. benchmark scenario qo'shiladi
    7. docs/update report yaratiladi
    8. tool clone ichida sinovdan o'tadi
    """
    
    def __init__(self, 
                 factory: CloneFactory,
                 source_manager: SourceCloneManager):
        self.factory = factory
        self.source_manager = source_manager
        
        logger.info("🛠️ Tool Onboarding initialized")
    
    def create_tool_spec(self,
                        tool_name: str,
                        description: str,
                        when_to_call: str,
                        input_schema: Dict,
                        output_schema: Dict,
                        side_effects: Optional[List[str]] = None,
                        required_permissions: Optional[List[str]] = None,
                        failure_modes: Optional[List[str]] = None,
                        timeout: int = 30) -> ToolSpec:
        """
        Tool spec yaratish
        
        Args:
            tool_name: Tool nomi
            description: Tavsif
            when_to_call: Qachon chaqiriladi
            input_schema: Input schema
            output_schema: Output schema
            side_effects: Side effects
            required_permissions: Kerakli ruxsatlar
            failure_modes: Muvaffaqiyatsiz holatlar
            timeout: Timeout
        
        Returns:
            ToolSpec: Tool spetsifikatsiyasi
        """
        spec = ToolSpec(
            tool_name=tool_name,
            description=description,
            when_to_call=when_to_call,
            input_schema=input_schema,
            output_schema=output_schema,
            side_effects=side_effects or [],
            required_permissions=required_permissions or [],
            failure_modes=failure_modes or [],
            timeout=timeout,
            audit_required=len(required_permissions or []) > 0
        )
        
        logger.info(f"📝 Tool spec created: {tool_name}")
        
        return spec
    
    def create_tool_wrapper(self, 
                          clone_id: str,
                          spec: ToolSpec,
                          implementation: str) -> bool:
        """
        Tool wrapper yaratish
        
        Args:
            clone_id: Clone ID
            spec: ToolSpec
            implementation: Implementatsiya
        
        Returns:
            bool: Muvaffaqiyat
        """
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            # Create tool file
            tool_file = clone_dir / "agent" / "tools" / f"{spec.tool_name}.py"
            tool_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate tool code
            code = self._generate_tool_code(spec, implementation)
            
            with open(tool_file, 'w') as f:
                f.write(code)
            
            logger.info(f"✅ Tool wrapper created: {spec.tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Tool wrapper creation failed: {e}")
            return False
    
    def _generate_tool_code(self, spec: ToolSpec, implementation: str) -> str:
        """Tool kodi generatsiya qilish"""
        code = f'''"""
{spec.tool_name} - {spec.description}
Generated by Self-Clone Improvement System
"""
from typing import Dict, Any, Optional

class {spec.tool_name}:
    """
    {spec.description}
    
    Called: {spec.when_to_call}
    """
    
    def __init__(self):
        self.name = "{spec.tool_name}"
        self.timeout = {spec.timeout}
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool
        
        Args:
            input_data: Input data matching schema
            
        Returns:
            Dict: Output data matching schema
        """
        # Implementation
        {implementation}
    
    def get_schema(self) -> Dict:
        """Get input/output schema"""
        return {{
            "input": {json.dumps(spec.input_schema, indent=4)},
            "output": {json.dumps(spec.output_schema, indent=4)}
        }}


def create_{spec.tool_name.lower()}() -> {spec.tool_name}:
    """Factory function"""
    return {spec.tool_name}()
'''
        return code
    
    def add_tool_to_registry(self, clone_id: str, tool_name: str) -> bool:
        """
        Toolni registry ga qo'shish
        
        Args:
            clone_id: Clone ID
            tool_name: Tool nomi
        
        Returns:
            bool: Muvaffaqiyat
        """
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            # Find tools.py
            tools_file = clone_dir / "agent" / "tools.py"
            
            if not tools_file.exists():
                logger.error("tools.py not found")
                return False
            
            # Read
            with open(tools_file, 'r') as f:
                content = f.read()
            
            # Add import
            import_line = f"from agent.tools.{tool_name} import create_{tool_name.lower()}"
            
            if import_line not in content:
                # Add to content
                content = content.replace(
                    "# ADDITIONAL_TOOLS",
                    f"# ADDITIONAL_TOOLS\n{import_line}"
                )
                
                # Write back
                with open(tools_file, 'w') as f:
                    f.write(content)
            
            logger.info(f"✅ Tool added to registry: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add tool to registry: {e}")
            return False
    
    def generate_tool_test(self, clone_id: str, spec: ToolSpec) -> str:
        """
        Tool uchun test yaratish
        
        Args:
            clone_id: Clone ID
            spec: ToolSpec
        
        Returns:
            str: Test kodi
        """
        test_code = f'''
"""
Test for {spec.tool_name}
Generated by Self-Clone Improvement System
"""
import pytest
from agent.tools.{spec.tool_name} import create_{spec.tool_name.lower()}

def test_{spec.tool_name.lower()}_basic():
    """Basic test for {spec.tool_name}"""
    tool = create_{spec.tool_name.lower()}()
    result = tool.execute({{}})
    assert result is not None

def test_{spec.tool_name.lower()}_schema():
    """Schema validation test"""
    tool = create_{spec.tool_name.lower()}()
    schema = tool.get_schema()
    assert "input" in schema
    assert "output" in schema
'''
        return test_code


# ================================================================================
# BENCHMARK ADDITION
# ================================================================================

class BenchmarkAdder:
    """
    Benchmark Adder - Yangi benchmark qo'shish
    """
    
    def __init__(self, factory: CloneFactory):
        self.factory = factory
        
        logger.info("📊 Benchmark Adder initialized")
    
    def create_benchmark(self,
                        clone_id: str,
                        benchmark_name: str,
                        capability: str,
                        metric: str,
                        test_cases: List[Dict]) -> bool:
        """
        Benchmark yaratish
        
        Args:
            clone_id: Clone ID
            benchmark_name: Benchmark nomi
            capability: Capability
            metric: Metrika
            test_cases: Test case lar
        
        Returns:
            bool: Muvaffaqiyat
        """
        clone_dir = self.factory.get_clone_worktree(clone_id)
        if not clone_dir:
            return False
        
        try:
            # Create benchmark file
            bench_file = clone_dir / "agent" / "benchmarks" / f"{benchmark_name}.py"
            bench_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate benchmark code
            code = self._generate_benchmark_code(benchmark_name, capability, metric, test_cases)
            
            with open(bench_file, 'w') as f:
                f.write(code)
            
            logger.info(f"✅ Benchmark created: {benchmark_name}")
            return True
            
        except Exception as e:
            logger.error(f"Benchmark creation failed: {e}")
            return False
    
    def _generate_benchmark_code(self, name: str, capability: str, 
                                metric: str, test_cases: List[Dict]) -> str:
        """Benchmark kodi generatsiya qilish"""
        code = f'''
"""
{name} - Benchmark for {capability}
Generated by Self-Clone Improvement System
"""
import time
import asyncio
from typing import Dict, Any, List

class {name}Benchmark:
    """
    Benchmark for {capability}
    Metric: {metric}
    """
    
    def __init__(self):
        self.name = "{name}"
        self.capability = "{capability}"
        self.metric = "{metric}"
        self.results: List[Dict] = []
    
    async def run(self, test_cases: List[Dict]) -> Dict:
        """Run benchmark"""
        results = []
        
        for case in test_cases:
            start_time = time.time()
            
            # Run test case
            result = await self._run_case(case)
            
            duration = time.time() - start_time
            results.append({{
                "case": case.get("name", "unknown"),
                "duration": duration,
                "result": result,
                "success": result.get("success", False)
            }})
        
        self.results = results
        
        return self._calculate_summary(results)
    
    async def _run_case(self, case: Dict) -> Dict:
        """Run single test case"""
        # Placeholder - implement actual benchmark logic
        return {{"success": True, "data": case}}
    
    def _calculate_summary(self, results: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        total = len(results)
        successful = sum(1 for r in results if r.get("success", False))
        avg_duration = sum(r["duration"] for r in results) / total if total > 0 else 0
        
        return {{
            "benchmark": self.name,
            "total_cases": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_duration": avg_duration,
            "metric": self.metric
        }}


def create_{name.lower()}_benchmark() -> {name}Benchmark:
    """Factory function"""
    return {name}Benchmark()
'''
        return code


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_patch_executor(factory: CloneFactory, 
                        source_manager: SourceCloneManager,
                        runtime: Any) -> PatchExecutor:
    """Patch Executor yaratish"""
    return PatchExecutor(factory, source_manager, runtime)


def create_tool_onboarding(factory: CloneFactory,
                          source_manager: SourceCloneManager) -> ToolOnboarding:
    """Tool Onboarding yaratish"""
    return ToolOnboarding(factory, source_manager)


def create_benchmark_adder(factory: CloneFactory) -> BenchmarkAdder:
    """Benchmark Adder yaratish"""
    return BenchmarkAdder(factory)
