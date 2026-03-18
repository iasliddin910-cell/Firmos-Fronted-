"""
OmniAgent X - Capability Registry
=================================
Central registry for all subkernels

Bu registry kernelga haqiqiy holatda qaysi subkernellar mavjudligini,
ularning holati, versionlari va interface'larini ko'rsatadi.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Set, Callable
from threading import RLock
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from agent.subkernel import (
    SubkernelCategory, 
    SubkernelStatus, 
    TrustLevel,
    SubkernelInterface,
    PluggableCapability,
)
from agent.subkernel.spec import SubkernelSpec, PluginManifest


logger = logging.getLogger(__name__)


class RegistryEvent(str, Enum):
    """Registry events for event-driven architecture"""
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    DEGRADED = "degraded"
    QUARANTINED = "quarantined"
    UNLOADED = "unloaded"
    HEALTH_CHANGED = "health_changed"
    STATUS_CHANGED = "status_changed"


@dataclass
class CapabilityInfo:
    """Capability haqida batafsil ma'lumot"""
    name: str
    capability_type: PluggableCapability
    category: SubkernelCategory
    version: str
    status: SubkernelStatus
    trust_class: TrustLevel
    health_score: float = 1.0
    is_active: bool = False
    is_loaded: bool = False
    last_health_check: Optional[float] = None
    error: Optional[str] = None
    degradation_reason: Optional[str] = None


class CapabilityRegistry:
    """
    Capability Registry - Barcha subkernellar haqida truth source
    
    Bu registry:
    - Qaysi subkernel mavjud
    - Qaysi biri active
    - Qaysi biri degraded
    - Qaysi biri quarantined
    - Qaysi version ishlayapti
    - Qaysi interface'ni kim beradi
    
    Hammasini bitta joyda ushlab turadi.
    """
    
    def __init__(self):
        self._lock = RLock()
        
        # Main registry: name -> manifest
        self._manifests: Dict[str, PluginManifest] = {}
        
        # Indexes for fast lookup
        self._by_category: Dict[SubkernelCategory, List[str]] = {}
        self._by_capability: Dict[PluggableCapability, str] = {}
        self._by_status: Dict[SubkernelStatus, List[str]] = {}
        self._by_trust: Dict[TrustLevel, List[str]] = {}
        
        # Event subscribers
        self._event_subscribers: Dict[RegistryEvent, List[Callable]] = {
            event: [] for event in RegistryEvent
        }
        
        # Metrics
        self._metrics = {
            "total_registrations": 0,
            "total_unregistrations": 0,
            "total_activations": 0,
            "total_deactivations": 0,
            "total_degradations": 0,
            "total_quarantines": 0,
        }
    
    # ==================== REGISTRATION ====================
    
    def register(self, manifest: PluginManifest) -> bool:
        """
        Subkernel ro'yxatdan o'tkazish
        
        Returns:
            True - muvaffaqiyatli
            False - xato (already registered, invalid spec, etc.)
        """
        with self._lock:
            name = manifest.spec.name
            
            # Check if already registered
            if name in self._manifests:
                logger.warning(f"⚠️ Subkernel {name} already registered")
                return False
            
            # Validate spec
            if not manifest.spec.validate_version("2.0"):
                logger.error(f"❌ Subkernel {name} kernel version not compatible")
                return False
            
            # Check dependencies
            for dep in manifest.spec.dependencies:
                if dep not in self._manifests:
                    # Check if it's a required core component that doesn't need registration
                    if not self._is_core_dependency(dep):
                        logger.warning(f"⚠️ Subkernel {name} dependency {dep} not registered")
            
            # Store manifest
            manifest.registered_at = datetime.now().isoformat()
            manifest.status = SubkernelStatus.READY
            self._manifests[name] = manifest
            
            # Update indexes
            self._add_to_indexes(manifest)
            
            # Update metrics
            self._metrics["total_registrations"] += 1
            
            # Emit event
            self._emit_event(RegistryEvent.REGISTERED, {
                "name": name,
                "capability": manifest.spec.capability_type.value,
                "version": manifest.spec.version,
            })
            
            logger.info(f"✅ Registered subkernel: {name} (v{manifest.spec.version})")
            return True
    
    def unregister(self, name: str, reason: str = "") -> bool:
        """
        Subkernel ro'yxatdan o'chirish
        """
        with self._lock:
            if name not in self._manifests:
                logger.warning(f"⚠️ Subkernel {name} not found for unregistration")
                return False
            
            manifest = self._manifests[name]
            
            # Check if other subkernels depend on this
            for other_name, other_manifest in self._manifests.items():
                if name in other_manifest.spec.dependencies:
                    logger.error(f"❌ Cannot unregister {name}: {other_name} depends on it")
                    return False
            
            # Remove from indexes
            self._remove_from_indexes(manifest)
            
            # Remove from main registry
            del self._manifests[name]
            
            # Update metrics
            self._metrics["total_unregistrations"] += 1
            
            # Emit event
            self._emit_event(RegistryEvent.UNREGISTERED, {
                "name": name,
                "reason": reason,
            })
            
            logger.info(f"🗑️ Unregistered subkernel: {name}")
            return True
    
    # ==================== LIFECYCLE ====================
    
    def activate(self, name: str) -> bool:
        """Subkernel'ni faollashtirish"""
        with self._lock:
            manifest = self._manifests.get(name)
            if not manifest:
                logger.error(f"❌ Cannot activate {name}: not registered")
                return False
            
            # Check if already active
            if manifest.is_active:
                return True
            
            # Check dependencies are active
            for dep in manifest.spec.dependencies:
                dep_manifest = self._manifests.get(dep)
                if not dep_manifest or not dep_manifest.is_active:
                    logger.warning(f"⚠️ Activating {name} but dependency {dep} not active")
            
            # Activate
            manifest.is_active = True
            manifest.status = SubkernelStatus.ACTIVE
            
            # Update index
            self._update_status_index(manifest, SubkernelStatus.ACTIVE)
            
            # Metrics
            self._metrics["total_activations"] += 1
            
            # Event
            self._emit_event(RegistryEvent.ACTIVATED, {"name": name})
            
            logger.info(f"🚀 Activated subkernel: {name}")
            return True
    
    def deactivate(self, name: str, reason: str = "") -> bool:
        """Subkernel'ni o'chirish (deactivate)"""
        with self._lock:
            manifest = self._manifests.get(name)
            if not manifest:
                return False
            
            manifest.is_active = False
            manifest.status = SubkernelStatus.DISABLED
            
            self._update_status_index(manifest, SubkernelStatus.DISABLED)
            self._metrics["total_deactivations"] += 1
            
            self._emit_event(RegistryEvent.DEACTIVATED, {
                "name": name,
                "reason": reason,
            })
            
            logger.info(f"🔴 Deactivated subkernel: {name}")
            return True
    
    def degrade(self, name: str, reason: str) -> bool:
        """Subkernel'ni degraded holatga o'tkazish"""
        with self._lock:
            manifest = self._manifests.get(name)
            if not manifest:
                return False
            
            if not manifest.spec.can_degrade:
                logger.warning(f"⚠️ {name} cannot degrade")
                return False
            
            manifest.status = SubkernelStatus.DEGRADED
            manifest.degradation_reason = reason
            manifest.degraded_at = time.time()
            
            # Health score gets penalty
            manifest.health_score = max(0.3, manifest.health_score - 0.3)
            
            self._update_status_index(manifest, SubkernelStatus.DEGRADED)
            self._metrics["total_degradations"] += 1
            
            self._emit_event(RegistryEvent.DEGRADED, {
                "name": name,
                "reason": reason,
            })
            
            logger.warning(f"📉 Degraded subkernel: {name} - {reason}")
            return True
    
    def quarantine(self, name: str, reason: str) -> bool:
        """Subkernel'ni karantinga o'tkazish"""
        with self._lock:
            manifest = self._manifests.get(name)
            if not manifest:
                return False
            
            if not manifest.spec.can_quarantine:
                logger.warning(f"⚠️ {name} cannot be quarantined")
                return False
            
            manifest.status = SubkernelStatus.QUARANTINED
            manifest.quarantine_reason = reason
            manifest.quarantined_at = time.time()
            
            self._update_status_index(manifest, SubkernelStatus.QUARANTINED)
            self._metrics["total_quarantines"] += 1
            
            self._emit_event(RegistryEvent.QUARANTINED, {
                "name": name,
                "reason": reason,
            })
            
            logger.warning(f"🚫 Quarantined subkernel: {name} - {reason}")
            return True
    
    # ==================== QUERIES ====================
    
    def get(self, name: str) -> Optional[PluginManifest]:
        """Subkernel manifest olish"""
        return self._manifests.get(name)
    
    def get_all(self) -> List[PluginManifest]:
        """Barcha subkernellarni olish"""
        return list(self._manifests.values())
    
    def get_active(self) -> List[PluginManifest]:
        """Faol subkernellarni olish"""
        return [m for m in self._manifests.values() if m.is_active]
    
    def get_healthy(self) -> List[PluginManifest]:
        """Sog'lom subkernellarni olish"""
        return [m for m in self._manifests.values() if m.is_healthy()]
    
    def get_by_category(self, category: SubkernelCategory) -> List[PluginManifest]:
        """Kategoriya bo'yicha olish"""
        names = self._by_category.get(category, [])
        return [self._manifests[n] for n in names if n in self._manifests]
    
    def get_by_capability(self, capability: PluggableCapability) -> Optional[PluginManifest]:
        """Capability type bo'yicha olish"""
        name = self._by_capability.get(capability)
        return self._manifests.get(name) if name else None
    
    def get_by_status(self, status: SubkernelStatus) -> List[PluginManifest]:
        """Status bo'yicha olish"""
        names = self._by_status.get(status, [])
        return [self._manifests[n] for n in names if n in self._manifests]
    
    def get_requiring(self, interface: SubkernelInterface) -> List[PluginManifest]:
        """Berilgan interface'ni talab qiluvchi subkernellarni olish"""
        result = []
        for manifest in self._manifests.values():
            if interface in manifest.spec.interfaces:
                result.append(manifest)
        return result
    
    def is_capability_available(self, capability: PluggableCapability) -> bool:
        """Capability mavjud va faolmi?"""
        manifest = self.get_by_capability(capability)
        return manifest is not None and manifest.is_active and manifest.is_healthy()
    
    # ==================== HEALTH ====================
    
    def update_health(
        self, 
        name: str, 
        health_score: float,
        error: Optional[str] = None
    ) -> bool:
        """Health holatini yangilash"""
        with self._lock:
            manifest = self._manifests.get(name)
            if not manifest:
                return False
            
            old_health = manifest.health_score
            manifest.health_score = max(0.0, min(1.0, health_score))
            manifest.last_health_check = time.time()
            
            # Track failures
            if health_score < 0.5:
                manifest.consecutive_failures += 1
            else:
                manifest.consecutive_failures = 0
            
            # Track errors
            if error:
                manifest.last_error = error
                manifest.error_count += 1
            
            # Auto-degrade if health is critical
            if health_score < 0.3 and manifest.status not in (
                SubkernelStatus.DEGRADED,
                SubkernelStatus.QUARANTINED,
                SubkernelStatus.FAILED,
            ):
                self.degrade(name, f"Critical health: {health_score:.2f}")
            
            # Auto-quarantine if too many failures
            if manifest.should_quarantine():
                self.quarantine(name, f"Consecutive failures: {manifest.consecutive_failures}")
            
            # Emit event
            if old_health != manifest.health_score:
                self._emit_event(RegistryEvent.HEALTH_CHANGED, {
                    "name": name,
                    "old_health": old_health,
                    "new_health": manifest.health_score,
                })
            
            return True
    
    def record_call(self, name: str, success: bool, latency_ms: float):
        """Call metrikasini yozish"""
        with self._lock:
            manifest = self._manifests.get(name)
            if not manifest:
                return
            
            manifest.total_calls += 1
            if success:
                manifest.successful_calls += 1
            else:
                manifest.failed_calls += 1
            manifest.total_latency_ms += latency_ms
    
    # ==================== EVENTS ====================
    
    def subscribe(self, event: RegistryEvent, callback: Callable):
        """Eventga obuna bo'lish"""
        if event not in self._event_subscribers:
            self._event_subscribers[event] = []
        self._event_subscribers[event].append(callback)
    
    def unsubscribe(self, event: RegistryEvent, callback: Callable):
        """Eventdan obunani bekor qilish"""
        if event in self._event_subscribers:
            try:
                self._event_subscribers[event].remove(callback)
            except ValueError:
                pass
    
    def _emit_event(self, event: RegistryEvent, data: Dict):
        """Event chiqarish"""
        for callback in self._event_subscribers.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
    
    # ==================== METRICS ====================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Registry metrikalarini olish"""
        with self._lock:
            active = len([m for m in self._manifests.values() if m.is_active])
            healthy = len([m for m in self._manifests.values() if m.is_healthy()])
            degraded = len(self.get_by_status(SubkernelStatus.DEGRADED))
            quarantined = len(self.get_by_status(SubkernelStatus.QUARANTINED))
            
            return {
                **self._metrics,
                "total_subkernels": len(self._manifests),
                "active": active,
                "healthy": healthy,
                "degraded": degraded,
                "quarantined": quarantined,
                "disabled": len(self.get_by_status(SubkernelStatus.DISABLED)),
            }
    
    def get_capability_matrix(self) -> List[CapabilityInfo]:
        """Capability matrix - barcha capability'lar holati"""
        result = []
        for manifest in self._manifests.values():
            result.append(CapabilityInfo(
                name=manifest.spec.name,
                capability_type=manifest.spec.capability_type,
                category=manifest.spec.category,
                version=manifest.spec.version,
                status=manifest.status,
                trust_class=manifest.spec.trust_class,
                health_score=manifest.health_score,
                is_active=manifest.is_active,
                is_loaded=manifest.is_loaded,
                last_health_check=manifest.last_health_check,
                error=manifest.last_error,
                degradation_reason=manifest.degradation_reason,
            ))
        return result
    
    # ==================== HELPERS ====================
    
    def _is_core_dependency(self, dep: str) -> bool:
        """Check if dependency is a core component that doesn't need registration"""
        core_deps = {"replay_clock", "replay_id", "kernel_api"}
        return dep in core_deps
    
    def _add_to_indexes(self, manifest: PluginManifest):
        """Manifestni indekslarga qo'shish"""
        name = manifest.spec.name
        
        # By category
        cat = manifest.spec.category
        if cat not in self._by_category:
            self._by_category[cat] = []
        self._by_category[cat].append(name)
        
        # By capability
        cap = manifest.spec.capability_type
        self._by_capability[cap] = name
        
        # By status
        status = manifest.status
        if status not in self._by_status:
            self._by_status[status] = []
        self._by_status[status].append(name)
        
        # By trust
        trust = manifest.spec.trust_class
        if trust not in self._by_trust:
            self._by_trust[trust] = []
        self._by_trust[trust].append(name)
    
    def _remove_from_indexes(self, manifest: PluginManifest):
        """Manifestni indekslardan o'chirish"""
        name = manifest.spec.name
        
        # Remove from category index
        cat = manifest.spec.category
        if cat in self._by_category and name in self._by_category[cat]:
            self._by_category[cat].remove(name)
        
        # Remove from capability index
        cap = manifest.spec.capability_type
        if cap in self._by_capability and self._by_capability[cap] == name:
            del self._by_capability[cap]
        
        # Remove from status index
        status = manifest.status
        if status in self._by_status and name in self._by_status[status]:
            self._by_status[status].remove(name)
        
        # Remove from trust index
        trust = manifest.spec.trust_class
        if trust in self._by_trust and name in self._by_trust[trust]:
            self._by_trust[trust].remove(name)
    
    def _update_status_index(self, manifest: PluginManifest, new_status: SubkernelStatus):
        """Status o'zgartirishda indeksni yangilash"""
        old_status = manifest.status
        
        # Remove from old status index
        if old_status in self._by_status and manifest.spec.name in self._by_status[old_status]:
            self._by_status[old_status].remove(manifest.spec.name)
        
        # Add to new status index
        if new_status not in self._by_status:
            self._by_status[new_status] = []
        self._by_status[new_status].append(manifest.spec.name)
        
        # Update manifest status
        manifest.status = new_status


# Global registry instance
_registry: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """Get or create global capability registry"""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry


def reset_capability_registry():
    """Reset global registry (for testing)"""
    global _registry
    _registry = None
