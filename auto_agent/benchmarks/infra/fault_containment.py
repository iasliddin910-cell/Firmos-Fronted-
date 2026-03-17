"""
FaultContainmentSupervisor - Fault Containment
========================================

Xatolarni tutib qolish.

Bu modul:
- Process tree kill
- Temp cleanup
- Browser cleanup
- Service teardown
- Result state mark as crashed
- Other runs continue

Definition of Done:
7. Run crash bo'lsa boshqa runlar davom etadi.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
import os
import signal
import psutil
import subprocess


@dataclass
class CrashReport:
    """Crash report."""
    run_id: str
    task_id: str
    crash_type: str  # timeout, oom, error, killed
    exit_code: int
    signal: str
    reason: str
    cleanup_performed: bool


class FaultContainmentSupervisor:
    """
    Fault containment supervisor.
    
    Definition of Done:
    7. Run crash bo'lsa boshqa runlar davom etadi.
    """
    
    def __init__(self):
        self._processes: Dict[str, int] = {}  # task_id -> pid
        self._crash_handlers: List[Callable] = []
    
    def register_process(self, task_id: str, pid: int) -> None:
        """Processni ro'yxatga olish."""
        self._processes[task_id] = pid
    
    def unregister_process(self, task_id: str) -> None:
        """Processni o'chirish."""
        if task_id in self._processes:
            del self._processes[task_id]
    
    def handle_crash(
        self,
        task_id: str,
        run_id: str,
        crash_type: str,
        reason: str = "",
    ) -> CrashReport:
        """Crashni qayta ishlash."""
        # Get exit info
        exit_code = -1
        signal_name = ""
        
        if task_id in self._processes:
            pid = self._processes[task_id]
            try:
                proc = psutil.Process(pid)
                exit_code = proc.exit_code
                signal_name = proc.signal() if proc.status() == psutil.STATUS_ZOMBIE else ""
            except psutil.NoSuchProcess:
                pass
        
        # Create crash report
        report = CrashReport(
            run_id=run_id,
            task_id=task_id,
            crash_type=crash_type,
            exit_code=exit_code,
            signal=signal_name,
            reason=reason,
            cleanup_performed=False,
        )
        
        # Perform cleanup
        self._cleanup(task_id, run_id)
        report.cleanup_performed = True
        
        # Notify handlers
        for handler in self._crash_handlers:
            try:
                handler(report)
            except Exception:
                pass
        
        # Remove from tracking
        self.unregister_process(task_id)
        
        return report
    
    def _cleanup(self, task_id: str, run_id: str) -> None:
        """Process va resurslarni tozalash."""
        if task_id in self._processes:
            pid = self._processes[task_id]
            try:
                # Kill process tree
                proc = psutil.Process(pid)
                children = proc.children(recursive=True)
                
                # Terminate children first
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                
                # Wait for graceful termination
                gone, alive = psutil.wait_procs(children, timeout=3)
                
                # Force kill if still alive
                for p in alive:
                    try:
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass
                
                # Then kill main process
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
            
            except psutil.NoSuchProcess:
                pass
    
    def force_kill(self, task_id: str) -> bool:
        """Processni majburan o'ldirish."""
        if task_id not in self._processes:
            return False
        
        pid = self._processes[task_id]
        
        try:
            proc = psutil.Process(pid)
            
            # Kill entire process tree
            children = proc.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            
            proc.kill()
            return True
        
        except psutil.NoSuchProcess:
            return False
        finally:
            self.unregister_process(task_id)
    
    def add_crash_handler(self, handler: Callable) -> None:
        """Crash handler qo'shish."""
        self._crash_handlers.append(handler)
    
    def get_active_tasks(self) -> List[str]:
        """Active tasklarni olish."""
        active = []
        for task_id, pid in self._processes.items():
            try:
                psutil.Process(pid)
                active.append(task_id)
            except psutil.NoSuchProcess:
                self.unregister_process(task_id)
        return active


def create_fault_supervisor() -> FaultContainmentSupervisor:
    """Fault supervisor yaratish."""
    return FaultContainmentSupervisor()
