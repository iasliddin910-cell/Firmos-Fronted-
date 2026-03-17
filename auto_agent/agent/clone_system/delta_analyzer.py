"""
================================================================================
2. DELTA ANALYZER
================================================================================
Bu modul "nima o'zgardi?" degan savolga javob beradi.

U 4 xil delta chiqaradi:
A. Code delta - qaysi fayllar, nechta line
B. Capability delta - qaysi ability kuchaydi
C. Tool delta - yangi tool, o'zgarishlar
D. Behavior delta - amaldagi farq
================================================================================
"""
import os
import json
import logging
import difflib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict

from .reporting_types import (
    CodeDelta, CapabilityDelta, ToolDelta, BehaviorDelta,
    MetricsImpact, TrustLevel
)

logger = logging.getLogger(__name__)


class DeltaAnalyzer:
    """
    Delta Analyzer - O'zgarish tahlilchisi
    
    4 xil delta chiqaradi:
    - Code delta: fayllar, line lar
    - Capability delta: ability lar
    - Tool delta: tool lar
    - Behavior delta: amaldagi farq
    """
    
    def __init__(self):
        # Known capability mappings
        self.capability_keywords = {
            "code_execution": ["code", "interpreter", "execute", "run"],
            "file_operations": ["file", "read", "write", "directory"],
            "web_browsing": ["browser", "web", "navigation", "page", "dom"],
            "memory": ["memory", "store", "remember", "context"],
            "planning": ["plan", "task", "decompose", "workflow"],
            "tool_creation": ["tool", "create", "register", "factory"],
            "learning": ["learn", "improve", "feedback", "signal"],
            "benchmarking": ["benchmark", "test", "measure", "metric"],
            "security": ["security", "secret", "guard", "sandbox"],
            "telemetry": ["telemetry", "log", "monitor", "health"]
        }
        
        logger.info("🔍 Delta Analyzer initialized")
    
    def analyze_all(self, 
                   clone_id: str,
                   clone_files: Dict[str, str],
                   original_files: Dict[str, str],
                   knowledge_analysis: Optional[Dict] = None) -> Dict[str, Any]:
        """
        To'liq delta tahlil
        
        Args:
            clone_id: Clone ID
            clone_files: Clone dagi fayllar
            original_files: Original fayllar
            knowledge_analysis: Bilim tahlili
        
        Returns:
            Dict: Barcha delta lar
        """
        result = {
            "clone_id": clone_id,
            "analyzed_at": time.time()
        }
        
        # A. Code Delta
        result["code_delta"] = self.analyze_code_delta(
            clone_files, original_files
        )
        
        # B. Capability Delta
        result["capability_delta"] = self.analyze_capability_delta(
            clone_files, knowledge_analysis
        )
        
        # C. Tool Delta
        result["tool_delta"] = self.analyze_tool_delta(
            clone_files, original_files
        )
        
        # D. Behavior Delta (placeholder - would need actual execution)
        result["behavior_delta"] = self.analyze_behavior_delta(
            result["code_delta"], result["capability_delta"]
        )
        
        logger.info(f"✅ Delta analysis complete for {clone_id}")
        
        return result
    
    def analyze_code_delta(self,
                         clone_files: Dict[str, str],
                         original_files: Dict[str, str]) -> CodeDelta:
        """
        Code delta tahlil
        
        Args:
            clone_files: Clone dagi fayllar
            original_files: Original fayllar
        
        Returns:
            CodeDelta
        """
        delta = CodeDelta()
        
        # Find new files
        for file_path in clone_files:
            if file_path not in original_files:
                delta.files_created.append(file_path)
        
        # Find deleted files
        for file_path in original_files:
            if file_path not in clone_files:
                delta.files_deleted.append(file_path)
        
        # Find changed files and count lines
        for file_path in clone_files:
            if file_path in original_files:
                original_content = original_files[file_path]
                clone_content = clone_files[file_path]
                
                if original_content != clone_content:
                    delta.files_changed.append(file_path)
                    
                    # Count line differences
                    original_lines = original_content.split('\n')
                    clone_lines = clone_content.split('\n')
                    
                    delta.lines_added += max(0, len(clone_lines) - len(original_lines))
                    delta.lines_removed += max(0, len(original_lines) - len(clone_lines))
                    
                    # Track module
                    module = self._extract_module(file_path)
                    if module and module not in delta.modules_affected:
                        delta.modules_affected.append(module)
        
        return delta
    
    def analyze_capability_delta(self,
                               clone_files: Dict[str, str],
                               knowledge_analysis: Optional[Dict] = None) -> CapabilityDelta:
        """
        Capability delta tahlil
        
        Args:
            clone_files: Clone dagi fayllar
            knowledge_analysis: Bilim tahlili
        
        Returns:
            CapabilityDelta
        """
        delta = CapabilityDelta()
        
        # Find capabilities mentioned in changed files
        capabilities_found = set()
        
        for file_path, content in clone_files.items():
            content_lower = content.lower()
            
            for capability, keywords in self.capability_keywords.items():
                for keyword in keywords:
                    if keyword in content_lower:
                        capabilities_found.add(capability)
                        break
        
        # Determine what changed
        # This is simplified - in reality would compare with original
        for capability in capabilities_found:
            # Check if this is new or enhanced
            if knowledge_analysis:
                # Check if capability was added or strengthened
                delta.capabilities_strengthened.append(capability)
            else:
                delta.capabilities_gained.append(capability)
        
        # Look for new ability patterns
        for file_path in clone_files:
            if "new" in file_path.lower() or "add" in file_path.lower():
                # Check for new capability patterns
                content = clone_files[file_path]
                
                # Simple detection based on content
                if "class" in content and "def" in content:
                    # Likely a new capability
                    delta.new_abilities.append(file_path)
        
        return delta
    
    def analyze_tool_delta(self,
                         clone_files: Dict[str, str],
                         original_files: Dict[str, str]) -> ToolDelta:
        """
        Tool delta tahlil
        
        Args:
            clone_files: Clone dagi fayllar
            original_files: Original fayllar
        
        Returns:
            ToolDelta
        """
        delta = ToolDelta()
        
        # Find tool-related files
        tool_patterns = ["tool", "factory", "registry", "create_"]
        
        for file_path in clone_files:
            # Check if this is a tool file
            is_tool_file = any(pattern in file_path.lower() for pattern in tool_patterns)
            
            if not is_tool_file:
                continue
            
            # Check if new
            if file_path not in original_files:
                delta.tools_added.append(file_path)
            else:
                # Check if modified
                if clone_files[file_path] != original_files[file_path]:
                    delta.tools_modified.append(file_path)
        
        # Look for tool creation patterns in code
        for file_path, content in clone_files.items():
            # Detect new tool definitions
            if "def create_" in content or "class Tool" in content:
                tool_name = self._extract_tool_name(file_path)
                
                if tool_name not in delta.tools_added:
                    # Check if truly new by comparing
                    if file_path not in original_files:
                        if tool_name not in delta.tools_added:
                            delta.tools_added.append(tool_name)
                    else:
                        if tool_name not in delta.tools_modified:
                            delta.tools_modified.append(tool_name)
        
        return delta
    
    def analyze_behavior_delta(self,
                              code_delta: CodeDelta,
                              capability_delta: CapabilityDelta) -> BehaviorDelta:
        """
        Behavior delta tahlil
        
        Args:
            code_delta: Code delta
            capability_delta: Capability delta
        
        Returns:
            BehaviorDelta
        """
        delta = BehaviorDelta()
        
        # Build behavior changes list based on deltas
        if code_delta.files_changed:
            delta.behavior_changes.append({
                "type": "code_modification",
                "description": f"{len(code_delta.files_changed)} files modified",
                "impact": "medium"
            })
        
        if code_delta.files_created:
            delta.behavior_changes.append({
                "type": "new_code",
                "description": f"{len(code_delta.files_created)} new files",
                "impact": "high" if any("core" in f.lower() for f in code_delta.files_created) else "medium"
            })
        
        if capability_delta.new_abilities:
            delta.behavior_changes.append({
                "type": "new_capability",
                "description": f"{len(capability_delta.new_abilities)} new abilities",
                "impact": "high"
            })
        
        if capability_delta.capabilities_strengthened:
            delta.behavior_changes.append({
                "type": "enhanced_capability",
                "description": f"{len(capability_delta.capabilities_strengthened)} capabilities enhanced",
                "impact": "medium"
            })
        
        return delta
    
    def _extract_module(self, file_path: str) -> Optional[str]:
        """Module nomini extract qilish"""
        parts = file_path.split('/')
        
        # Find agent/ module
        if 'agent' in parts:
            idx = parts.index('agent')
            if idx + 1 < len(parts):
                return parts[idx + 1]
        
        return None
    
    def _extract_tool_name(self, file_path: str) -> str:
        """Tool nomini extract qilish"""
        # Extract from filename
        name = Path(file_path).stem
        
        # Clean up
        if name.startswith('create_'):
            name = name[7:]
        
        return name
    
    def generate_delta_summary(self, delta_result: Dict) -> str:
        """Delta dan qisqa summary"""
        parts = []
        
        code = delta_result.get("code_delta", {})
        if code.get("files_changed"):
            parts.append(f"📝 {len(code['files_changed'])} files changed")
        
        if code.get("files_created"):
            parts.append(f"➕ {len(code['files_created'])} new files")
        
        cap = delta_result.get("capability_delta", {})
        if cap.get("capabilities_gained"):
            parts.append(f"🧠 {len(cap['capabilities_gained'])} capabilities gained")
        
        if cap.get("capabilities_strengthened"):
            parts.append(f"💪 {len(cap['capabilities_strengthened'])} capabilities enhanced")
        
        tool = delta_result.get("tool_delta", {})
        if tool.get("tools_added"):
            parts.append(f"🛠️ {len(tool['tools_added'])} tools added")
        
        return ", ".join(parts) if parts else "No changes detected"


# Helper
import time
