"""
Memory + Evolution Layer - Long-term Memory and Learning
====================================================
Bu qatlam tizimning uzoq muddatli xotirasi va o'rganish tizimi.

Ichida:
- research memory
- lineage registry
- experiment archive
- capability graph
"""

import uuid
import logging
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
from dataclasses import asdict

logger = logging.getLogger(__name__)


class ResearchMemory:
    """Research Memory - Tadqiqot xotirasi"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self.memory: dict[str, dict] = {}
        logger.info("🧠 ResearchMemory initialized")
    
    def store_research(
        self,
        topic: str,
        findings: str,
        source: str = "",
        tags: list[str] = None
    ) -> str:
        """Tadqiqot natijasini saqlash"""
        research_id = f"research_{str(uuid.uuid4())[:12]}"
        
        entry = {
            "id": research_id,
            "topic": topic,
            "findings": findings,
            "source": source,
            "tags": tags or [],
            "created_at": datetime.now().isoformat()
        }
        
        self.memory[research_id] = entry
        
        if self.storage_path:
            self._save_to_disk()
        
        logger.info(f"🧠 Research stored: {research_id}")
        return research_id
    
    def get_research(self, research_id: str) -> Optional[dict]:
        """Tadqiqotni olish"""
        return self.memory.get(research_id)
    
    def search_research(self, query: str) -> list[dict]:
        """Tadqiqotlarni qidirish"""
        results = []
        query_lower = query.lower()
        
        for entry in self.memory.values():
            if query_lower in entry.get("topic", "").lower():
                results.append(entry)
            elif query_lower in entry.get("findings", "").lower():
                results.append(entry)
        
        return results
    
    def _save_to_disk(self):
        """Xotirani diskga saqlash"""
        if not self.storage_path:
            return
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self.storage_path / "research_memory.json"
        
        with open(file_path, 'w') as f:
            json.dump(self.memory, f, indent=2)


class LineageRegistry:
    """Lineage Registry - Version lineage ro'yxati"""
    
    def __init__(self):
        self.lineage: dict[str, dict] = {}
        logger.info("📜 LineageRegistry initialized")
    
    def register_version(
        self,
        version: str,
        parent_version: str,
        promotion_record: dict
    ) -> str:
        """Yangi version ro'yxatga olish"""
        entry_id = f"lineage_{str(uuid.uuid4())[:12]}"
        
        entry = {
            "id": entry_id,
            "version": version,
            "parent_version": parent_version,
            "promotion_record": promotion_record,
            "created_at": datetime.now().isoformat()
        }
        
        self.lineage[entry_id] = entry
        logger.info(f"📜 Version registered: {version}")
        
        return entry_id
    
    def get_lineage(self, version: str) -> list[dict]:
        """Version lineage olish"""
        # Simplified - realda tree structure
        return list(self.lineage.values())
    
    def get_latest_version(self) -> Optional[str]:
        """Eng oxirgi versionni olish"""
        if not self.lineage:
            return None
        
        sorted_lineage = sorted(
            self.lineage.values(),
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        
        return sorted_lineage[0].get("version") if sorted_lineage else None


class ExperimentArchive:
    """Experiment Archive - Experiment arxivi"""
    
    def __init__(self):
        self.experiments: dict[str, dict] = {}
        logger.info("🧪 ExperimentArchive initialized")
    
    def archive_experiment(
        self,
        name: str,
        hypothesis: str,
        result: str,
        outcome: str,  # "success", "failure", "inconclusive"
        metrics: dict = None
    ) -> str:
        """Experiment arxivlash"""
        exp_id = f"exp_{str(uuid.uuid4())[:12]}"
        
        experiment = {
            "id": exp_id,
            "name": name,
            "hypothesis": hypothesis,
            "result": result,
            "outcome": outcome,
            "metrics": metrics or {},
            "created_at": datetime.now().isoformat()
        }
        
        self.experiments[exp_id] = experiment
        logger.info(f"🧪 Experiment archived: {exp_id}")
        
        return exp_id
    
    def get_experiment(self, exp_id: str) -> Optional[dict]:
        """Experiment olish"""
        return self.experiments.get(exp_id)
    
    def get_successful_experiments(self) -> list[dict]:
        """Muvaffaqiyatli experimentlar"""
        return [e for e in self.experiments.values() if e.get("outcome") == "success"]
    
    def get_failed_experiments(self) -> list[dict]:
        """Muvaffaqiyatsiz experimentlar"""
        return [e for e in self.experiments.values() if e.get("outcome") == "failure"]


class CapabilityGraph:
    """Capability Graph - Imkoniyatlar grafi"""
    
    def __init__(self):
        self.capabilities: dict[str, dict] = {}
        self.dependencies: dict[str, list[str]] = {}
        logger.info("🔗 CapabilityGraph initialized")
    
    def register_capability(
        self,
        name: str,
        description: str,
        level: int = 1,
        dependencies: list[str] = None
    ) -> str:
        """Imkoniyat ro'yxatga olish"""
        cap_id = f"cap_{str(uuid.uuid4())[:12]}"
        
        capability = {
            "id": cap_id,
            "name": name,
            "description": description,
            "level": level,
            "dependencies": dependencies or [],
            "created_at": datetime.now().isoformat()
        }
        
        self.capabilities[cap_id] = capability
        
        if dependencies:
            self.dependencies[cap_id] = dependencies
        
        logger.info(f"🔗 Capability registered: {name}")
        
        return cap_id
    
    def get_capability(self, name: str) -> Optional[dict]:
        """Imkoniyatni olish"""
        for cap in self.capabilities.values():
            if cap.get("name") == name:
                return cap
        return None
    
    def get_capability_tree(self, capability_name: str) -> dict:
        """Imkoniyat daraxtini olish"""
        cap = self.get_capability(capability_name)
        if not cap:
            return {}
        
        tree = {
            "name": cap["name"],
            "level": cap["level"],
            "children": []
        }
        
        for dep_name in cap.get("dependencies", []):
            child = self.get_capability_tree(dep_name)
            if child:
                tree["children"].append(child)
        
        return tree
    
    def get_all_capabilities(self) -> list[dict]:
        """Barcha imkoniyatlar"""
        return list(self.capabilities.values())


class MemoryLayer:
    """Memory + Evolution Layer - To'liq xotira tizimi"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.research_memory = ResearchMemory(storage_path)
        self.lineage_registry = LineageRegistry()
        self.experiment_archive = ExperimentArchive()
        self.capability_graph = CapabilityGraph()
        
        logger.info("💾 MemoryLayer initialized")
    
    def learn_from_upgrade(
        self,
        candidate_id: str,
        success: bool,
        learnings: str
    ):
        """Upgrad dan o'rganish"""
        self.experiment_archive.archive_experiment(
            name=f"upgrade_{candidate_id}",
            hypothesis=f"Upgrade {candidate_id}",
            result=learnings,
            outcome="success" if success else "failure"
        )
        
        logger.info(f"💾 Learned from upgrade: {candidate_id}")
    
    def register_capability_improvement(
        self,
        capability: str,
        improvement: str
    ):
        """Imkoniyat yaxshilanishi"""
        existing = self.capability_graph.get_capability(capability)
        
        if existing:
            existing["improvements"] = existing.get("improvements", [])
            existing["improvements"].append({
                "improvement": improvement,
                "at": datetime.now().isoformat()
            })
        else:
            self.capability_graph.register_capability(
                name=capability,
                description=improvement,
                level=1
            )
    
    def get_stats(self) -> dict:
        """Xotira statistikasi"""
        return {
            "research_entries": len(self.research_memory.memory),
            "lineage_entries": len(self.lineage_registry.lineage),
            "experiments": len(self.experiment_archive.experiments),
            "capabilities": len(self.capability_graph.capabilities)
        }


def create_memory_layer(storage_path: str = None) -> MemoryLayer:
    """Memory Layer yaratish"""
    return MemoryLayer(storage_path)
