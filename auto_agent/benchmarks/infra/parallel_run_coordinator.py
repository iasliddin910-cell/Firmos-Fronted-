"""
ParallelRunCoordinator - Parallel Run Coordination
==========================================

Parallel benchmark ishga tushirish.

Bu modul:
- Port allocator
- Temp root allocator
- Browser profile allocator
- Service namespace allocator

Definition of Done:
(Part of infrastructure - related to parallel execution)
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import uuid
import os


@dataclass
class RunSlot:
    """Run slot."""
    run_id: str
    port_base: int
    temp_root: str
    browser_profile: str
    namespace: str


class ParallelRunCoordinator:
    """
    Parallel run coordinator.
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or "/tmp/eval_parallel"
        os.makedirs(self.base_path, exist_ok=True)
        
        self._port_counter = 12000
        self._used_ports = set()
        self._slots: Dict[str, RunSlot] = {}
    
    def allocate_slot(self, run_id: str) -> RunSlot:
        """Slot ajratish."""
        # Generate unique ID
        unique_id = f"{run_id}_{uuid.uuid4().hex[:8]}"
        
        # Allocate ports
        port_base = self._allocate_port()
        
        # Allocate directories
        temp_root = os.path.join(self.base_path, unique_id, "temp")
        browser_profile = os.path.join(self.base_path, unique_id, "browser")
        
        os.makedirs(temp_root, exist_ok=True)
        os.makedirs(browser_profile, exist_ok=True)
        
        # Allocate namespace
        namespace = f"eval_{unique_id}"
        
        slot = RunSlot(
            run_id=run_id,
            port_base=port_base,
            temp_root=temp_root,
            browser_profile=browser_profile,
            namespace=namespace,
        )
        
        self._slots[run_id] = slot
        
        return slot
    
    def _allocate_port(self) -> int:
        """Port ajratish."""
        while self._port_counter in self._used_ports:
            self._port_counter += 1
        
        port = self._port_counter
        self._used_ports.add(port)
        self._port_counter += 1
        
        return port
    
    def release_slot(self, run_id: str) -> None:
        """Slotni bo'shatish."""
        if run_id in self._slots:
            slot = self._slots[run_id]
            
            # Release ports
            for i in range(3):
                self._used_ports.discard(slot.port_base + i)
            
            # Remove directories
            import shutil
            temp_root = os.path.dirname(slot.temp_root)
            if os.path.exists(temp_root):
                shutil.rmtree(temp_root, ignore_errors=True)
            
            del self._slots[run_id]
    
    def get_slot(self, run_id: str) -> Optional[RunSlot]:
        """Slot olish."""
        return self._slots.get(run_id)


def create_parallel_coordinator(base_path: str = None) -> ParallelRunCoordinator:
    """Parallel coordinator yaratish."""
    return ParallelRunCoordinator(base_path)
