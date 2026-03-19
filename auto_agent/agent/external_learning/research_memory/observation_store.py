"""
Observation Store - Signallarni saqlash
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ObservationStore:
    def __init__(self, storage_path: str = "data/external_learning"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.signals: Dict[str, Dict[str, Any]] = {}
        self.load()
        logger.info(f"Observation Store initialized at {storage_path}")
    
    def store_signal(self, signal: Dict[str, Any]):
        signal_id = signal.get("signal_id")
        if signal_id:
            self.signals[signal_id] = signal
            self.save()
    
    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return self.signals.get(signal_id)
    
    def get_latest(self, limit: int = 10, decision: Optional[str] = None) -> List[Dict[str, Any]]:
        signals = list(self.signals.values())
        if decision:
            signals = [s for s in signals if s.get("decision") == decision]
        signals.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        return signals[:limit]
    
    def get_by_decision(self, decision) -> List[Dict[str, Any]]:
        return [s for s in self.signals.values() if s.get("decision") == decision]
    
    def get_total_count(self) -> int:
        return len(self.signals)
    
    def increment_signal_count(self, signal_id: str):
        if signal_id in self.signals:
            self.signals[signal_id]["view_count"] = self.signals[signal_id].get("view_count", 0) + 1
    
    def save(self):
        data_file = self.storage_path / "signals.json"
        with open(data_file, "w") as f:
            json.dump(self.signals, f, indent=2, default=str)
    
    def load(self):
        data_file = self.storage_path / "signals.json"
        if data_file.exists():
            with open(data_file, "r") as f:
                self.signals = json.load(f)
