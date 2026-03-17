"""
CalibrationPackManager - Calibration Pack Management
============================================

Calibration pack yaratish va boshqarish.

Bu modul:
- Tashqi benchmarkdan representative slice
- Internal calibration pack
- Novelty holdout packs

Definition of Done:
(Part of calibration system)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
import json
import os


@dataclass
class CalibrationPack:
    """Calibration pack."""
    pack_id: str
    pack_type: str  # external, internal, holdout
    
    # Task references
    task_ids: List[str] = field(default_factory=list)
    
    # Purpose
    purpose: str = ""
    source: str = ""  # swe_bench, internal, etc.
    
    # Metadata
    created_at: str = ""
    version: str = "1.0"
    
    # Stats
    task_count: int = 0
    suite_distribution: Dict[str, int] = field(default_factory=dict)


class CalibrationPackManager:
    """
    Calibration pack manager.
    
    Calibration pack - tashqi benchmarklardan representative slice.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "benchmarks/calibration/packs"
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.packs: Dict[str, CalibrationPack] = {}
        self._load_packs()
    
    def create_external_pack(
        self,
        pack_id: str,
        source: str,
        task_ids: List[str],
        purpose: str,
    ) -> CalibrationPack:
        """Tashqi calibration pack yaratish."""
        pack = CalibrationPack(
            pack_id=pack_id,
            pack_type="external",
            task_ids=task_ids,
            purpose=purpose,
            source=source,
            task_count=len(task_ids),
        )
        
        self.packs[pack_id] = pack
        self._save_pack(pack)
        
        return pack
    
    def create_internal_pack(
        self,
        pack_id: str,
        task_ids: List[str],
        purpose: str,
    ) -> CalibrationPack:
        """Ichki calibration pack yaratish."""
        pack = CalibrationPack(
            pack_id=pack_id,
            pack_type="internal",
            task_ids=task_ids,
            purpose=purpose,
            source="internal",
            task_count=len(task_ids),
        )
        
        self.packs[pack_id] = pack
        self._save_pack(pack)
        
        return pack
    
    def create_holdout_pack(
        self,
        pack_id: str,
        task_ids: List[str],
        purpose: str,
    ) -> CalibrationPack:
        """Holdout pack yaratish - self-improvement ko'rmagan tasklar."""
        pack = CalibrationPack(
            pack_id=pack_id,
            pack_type="holdout",
            task_ids=task_ids,
            purpose=purpose,
            source="never_seen",
            task_count=len(task_ids),
        )
        
        self.packs[pack_id] = pack
        self._save_pack(pack)
        
        return pack
    
    def get_pack(self, pack_id: str) -> Optional[CalibrationPack]:
        """Pack olish."""
        return self.packs.get(pack_id)
    
    def get_external_packs(self) -> List[CalibrationPack]:
        """Barcha tashqi packlar."""
        return [p for p in self.packs.values() if p.pack_type == "external"]
    
    def get_holdout_packs(self) -> List[CalibrationPack]:
        """Barcha holdout packlar."""
        return [p for p in self.packs.values() if p.pack_type == "holdout"]
    
    def get_calibration_pack(self) -> Optional[CalibrationPack]:
        """Asosiy calibration pack olish."""
        return self.packs.get("calibration_primary")
    
    def _save_pack(self, pack: CalibrationPack) -> None:
        """Packni saqlash."""
        path = os.path.join(self.storage_path, f"{pack.pack_id}.json")
        
        with open(path, 'w') as f:
            json.dump({
                "pack_id": pack.pack_id,
                "pack_type": pack.pack_type,
                "task_ids": pack.task_ids,
                "purpose": pack.purpose,
                "source": pack.source,
                "task_count": pack.task_count,
                "suite_distribution": pack.suite_distribution,
            }, f, indent=2)
    
    def _load_packs(self) -> None:
        """Packlarni yuklash."""
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                pack_id = filename.replace(".json", "")
                path = os.path.join(self.storage_path, filename)
                
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.packs[pack_id] = CalibrationPack(**data)


def create_calibration_manager(storage_path: str = None) -> CalibrationPackManager:
    """Manager yaratish."""
    return CalibrationPackManager(storage_path)
