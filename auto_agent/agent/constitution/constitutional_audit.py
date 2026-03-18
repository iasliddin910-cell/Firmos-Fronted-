"""
OmniAgent X - Constitutional Audit
==============================
Bu fayl Constitution Kernel qonunlari ishga tushganda va buzilganda log qiladi.

Audit layer:
- "main promotion blocked: missing signed decision"
- "candidate blocked: protected zone access"
- "dossier incomplete: regressions section missing"
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import threading


logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit voqea turlari"""
    # Rule checks
    RULE_CHECK = "rule_check"
    RULE_VIOLATION = "rule_violation"
    RULE_APPROVED = "rule_approved"
    
    # Promotion events
    PROMOTION_BLOCKED = "promotion_blocked"
    PROMOTION_APPROVED = "promotion_approved"
    PROMOTION_ROLLBACK = "promotion_rollback"
    
    # Protected zone
    ZONE_ACCESS_DENIED = "zone_access_denied"
    ZONE_ACCESS_APPROVED = "zone_access_approved"
    
    # Clone events
    CLONE_CREATED = "clone_created"
    CLONE_MUTATION = "clone_mutation"
    CLONE_PROMOTED = "clone_promoted"
    
    # Constitution changes
    CONSTITUTION_CHANGE_PROPOSED = "constitution_change_proposed"
    CONSTITUTION_CHANGE_APPROVED = "constitution_change_approved"
    CONSTITUTION_CHANGE_REJECTED = "constitution_change_rejected"
    
    # Profile changes
    PROFILE_SWITCHED = "profile_switched"
    PROFILE_VIOLATION = "profile_violation"
    
    # Budget events
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_WARNING = "budget_warning"


class AuditSeverity(Enum):
    """Audit og'irligi"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit voqea"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    
    # Vaqt
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Rule info
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    
    # Who/What
    actor: str = "system"
    source: str = "constitution_kernel"
    
    # Details
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    clone_id: Optional[str] = None
    candidate_id: Optional[str] = None
    proposal_id: Optional[str] = None
    profile: Optional[str] = None
    
    # Resolution
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class AuditSummary:
    """Audit xulosa"""
    total_events: int = 0
    violations: int = 0
    approvals: int = 0
    blocked: int = 0
    warnings: int = 0
    
    by_rule: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)


class ConstitutionalAudit:
    """
    Constitutional Audit - barcha constitutional eventslarni log qiladi
    """
    
    def __init__(self, audit_dir: Optional[str] = None):
        # Audit directory
        if audit_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            audit_dir = base_dir / "data" / "audit"
        
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage (for fast access)
        self.events: List[AuditEvent] = []
        self.event_index: Dict[str, AuditEvent] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Metrics
        self.metrics = AuditSummary()
        
        # Load existing events
        self._load_events()
        
        logger.info(f"ConstitutionalAudit initialized: {self.audit_dir}")
    
    def _load_events(self):
        """Mavjud eventlarni yuklash"""
        try:
            # Load recent events (last 7 days)
            cutoff = datetime.now() - timedelta(days=7)
            event_files = sorted(self.audit_dir.glob("audit_*.jsonl"), reverse=True)[:10]
            
            for event_file in event_files:
                with open(event_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                event = self._dict_to_event(data)
                                if event:
                                    self.events.append(event)
                                    self.event_index[event.event_id] = event
                            except:
                                pass
            
            # Update metrics
            self._update_metrics()
            
            logger.info(f"Loaded {len(self.events)} audit events")
            
        except Exception as e:
            logger.warning(f"Failed to load events: {e}")
    
    def _dict_to_event(self, data: Dict) -> Optional[AuditEvent]:
        """Dict ni AuditEvent ga o'girish"""
        try:
            return AuditEvent(
                event_id=data.get("event_id", ""),
                event_type=AuditEventType(data.get("event_type", "rule_check")),
                severity=AuditSeverity(data.get("severity", "info")),
                timestamp=data.get("timestamp", ""),
                rule_id=data.get("rule_id"),
                rule_name=data.get("rule_name"),
                actor=data.get("actor", "system"),
                source=data.get("source", "constitution_kernel"),
                message=data.get("message", ""),
                details=data.get("details", {}),
                clone_id=data.get("clone_id"),
                candidate_id=data.get("candidate_id"),
                proposal_id=data.get("proposal_id"),
                profile=data.get("profile"),
                resolved=data.get("resolved", False),
                resolution=data.get("resolution")
            )
        except:
            return None
    
    def _event_to_dict(self, event: AuditEvent) -> Dict:
        """AuditEvent ni dict ga o'girish"""
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "timestamp": event.timestamp,
            "rule_id": event.rule_id,
            "rule_name": event.rule_name,
            "actor": event.actor,
            "source": event.source,
            "message": event.message,
            "details": event.details,
            "clone_id": event.clone_id,
            "candidate_id": event.candidate_id,
            "proposal_id": event.proposal_id,
            "profile": event.profile,
            "resolved": event.resolved,
            "resolution": event.resolution
        }
    
    def _save_event(self, event: AuditEvent):
        """Event ni faylga saqlash"""
        try:
            # Daily file
            date_str = datetime.now().strftime("%Y-%m-%d")
            event_file = self.audit_dir / f"audit_{date_str}.jsonl"
            
            with open(event_file, 'a') as f:
                f.write(json.dumps(self._event_to_dict(event)) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to save event: {e}")
    
    def _update_metrics(self):
        """Metrikani yangilash"""
        self.metrics = AuditSummary()
        self.metrics.total_events = len(self.events)
        
        for event in self.events:
            # By type
            type_key = event.event_type.value
            self.metrics.by_type[type_key] = self.metrics.by_type.get(type_key, 0) + 1
            
            # By severity
            severity_key = event.severity.value
            self.metrics.by_severity[severity_key] = self.metrics.by_severity.get(severity_key, 0) + 1
            
            # Violations, approvals, blocked
            if event.event_type == AuditEventType.RULE_VIOLATION:
                self.metrics.violations += 1
            elif event.event_type == AuditEventType.RULE_APPROVED:
                self.metrics.approvals += 1
            elif event.event_type == AuditEventType.PROMOTION_BLOCKED:
                self.metrics.blocked += 1
            elif event.severity == AuditEventType.WARNING:
                self.metrics.warnings += 1
            
            # By rule
            if event.rule_id:
                self.metrics.by_rule[event.rule_id] = self.metrics.by_rule.get(event.rule_id, 0) + 1
    
    # =============================================
    # LOGGING METHODS
    # =============================================
    
    def log_rule_check(
        self,
        rule_id: str,
        rule_name: str,
        approved: bool,
        message: str,
        details: Dict[str, Any] = None,
        actor: str = "system"
    ) -> AuditEvent:
        """Rule tekshiruvini log qilish"""
        
        event = AuditEvent(
            event_id=f"Audit-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.RULE_APPROVED if approved else AuditEventType.RULE_VIOLATION,
            severity=AuditSeverity.INFO if approved else AuditSeverity.ERROR,
            rule_id=rule_id,
            rule_name=rule_name,
            message=message,
            details=details or {},
            actor=actor
        )
        
        return self._add_event(event)
    
    def log_violation(
        self,
        rule_id: str,
        rule_name: str,
        message: str,
        details: Dict[str, Any] = None,
        severity: AuditSeverity = AuditSeverity.ERROR,
        actor: str = "system"
    ) -> AuditEvent:
        """Qoidabuzarlashni log qilish"""
        
        event = AuditEvent(
            event_id=f"Violation-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.RULE_VIOLATION,
            severity=severity,
            rule_id=rule_id,
            rule_name=rule_name,
            message=message,
            details=details or {},
            actor=actor
        )
        
        return self._add_event(event)
    
    def log_promotion_blocked(
        self,
        reason: str,
        candidate_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        details: Dict[str, Any] = None
    ) -> AuditEvent:
        """Promotion bloklangani log qilish"""
        
        event = AuditEvent(
            event_id=f"Blocked-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.PROMOTION_BLOCKED,
            severity=AuditSeverity.WARNING,
            message=f"Promotion blocked: {reason}",
            candidate_id=candidate_id,
            rule_id=rule_id,
            details=details or {}
        )
        
        return self._add_event(event)
    
    def log_promotion_approved(
        self,
        candidate_id: str,
        destination: str,
        details: Dict[str, Any] = None
    ) -> AuditEvent:
        """Promotion tasdiqlangani log qilish"""
        
        event = AuditEvent(
            event_id=f"Approved-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.PROMOTION_APPROVED,
            severity=AuditSeverity.INFO,
            message=f"Promotion approved to {destination}",
            candidate_id=candidate_id,
            details=details or {}
        )
        
        return self._add_event(event)
    
    def log_zone_access_denied(
        self,
        zone: str,
        target_path: str,
        operation: str,
        details: Dict[str, Any] = None
    ) -> AuditEvent:
        """Protected zone access rad etilishi log qilish"""
        
        event = AuditEvent(
            event_id=f"ZoneDeny-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.ZONE_ACCESS_DENIED,
            severity=AuditSeverity.ERROR,
            message=f"Protected zone access denied: {zone}",
            details={
                "zone": zone,
                "target_path": target_path,
                "operation": operation,
                **(details or {})
            }
        )
        
        return self._add_event(event)
    
    def log_clone_mutation(
        self,
        clone_id: str,
        files_touched: List[str],
        details: Dict[str, Any] = None
    ) -> AuditEvent:
        """Clone mutation log qilish"""
        
        event = AuditEvent(
            event_id=f"CloneMut-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.CLONE_MUTATION,
            severity=AuditSeverity.INFO,
            clone_id=clone_id,
            message=f"Clone {clone_id} mutated {len(files_touched)} files",
            details={
                "files_touched": files_touched,
                **(details or {})
            }
        )
        
        return self._add_event(event)
    
    def log_constitution_change(
        self,
        proposal_id: str,
        change_type: str,
        status: str,
        details: Dict[str, Any] = None
    ) -> AuditEvent:
        """Constitution change log qilish"""
        
        event_type = AuditEventType.CONSTITUTION_CHANGE_PROPOSED
        if status == "approved":
            event_type = AuditEventType.CONSTITUTION_CHANGE_APPROVED
        elif status == "rejected":
            event_type = AuditEventType.CONSTITUTION_CHANGE_REJECTED
        
        event = AuditEvent(
            event_id=f"ConstChange-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=event_type,
            severity=AuditSeverity.INFO,
            proposal_id=proposal_id,
            message=f"Constitution change: {change_type} - {status}",
            details=details or {}
        )
        
        return self._add_event(event)
    
    def log_profile_switch(
        self,
        old_profile: str,
        new_profile: str,
        reason: str = ""
    ) -> AuditEvent:
        """Profile almashuvi log qilish"""
        
        event = AuditEvent(
            event_id=f"ProfileSw-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.PROFILE_SWITCHED,
            severity=AuditSeverity.INFO,
            profile=new_profile,
            message=f"Profile switched: {old_profile} -> {new_profile}",
            details={"old_profile": old_profile, "reason": reason}
        )
        
        return self._add_event(event)
    
    def log_budget_exceeded(
        self,
        budget_type: str,
        current: int,
        limit: int,
        details: Dict[str, Any] = None
    ) -> AuditEvent:
        """Budget oshgani log qilish"""
        
        event = AuditEvent(
            event_id=f"BudgetEx-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            event_type=AuditEventType.BUDGET_EXCEEDED,
            severity=AuditSeverity.WARNING,
            message=f"Budget exceeded: {budget_type} ({current}/{limit})",
            details={
                "budget_type": budget_type,
                "current": current,
                "limit": limit,
                **(details or {})
            }
        )
        
        return self._add_event(event)
    
    # =============================================
    # INTERNAL
    # =============================================
    
    def _add_event(self, event: AuditEvent) -> AuditEvent:
        """Event qo'shish"""
        with self._lock:
            self.events.append(event)
            self.event_index[event.event_id] = event
            self._save_event(event)
            self._update_metrics()
        
        # Also log to standard logger
        log_level = logging.INFO if event.severity == AuditSeverity.INFO else logging.WARNING
        logger.log(log_level, f"[CONSTITUTION] {event.message}")
        
        return event
    
    # =============================================
    # QUERY METHODS
    # =============================================
    
    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Event ID bo'yicha olish"""
        return self.event_index.get(event_id)
    
    def get_events_by_rule(self, rule_id: str) -> List[AuditEvent]:
        """Rule bo'yicha eventlar"""
        return [e for e in self.events if e.rule_id == rule_id]
    
    def get_events_by_type(self, event_type: AuditEventType) -> List[AuditEvent]:
        """Type bo'yicha eventlar"""
        return [e for e in self.events if e.event_type == event_type]
    
    def get_violations(self, limit: int = 100) -> List[AuditEvent]:
        """So'nggi buzilishlar"""
        violations = [e for e in self.events if e.event_type == AuditEventType.RULE_VIOLATION]
        return violations[-limit:]
    
    def get_blocked_promotions(self, limit: int = 50) -> List[AuditEvent]:
        """Bloklangan promotionlar"""
        blocked = [e for e in self.events if e.event_type == AuditEventType.PROMOTION_BLOCKED]
        return blocked[-limit:]
    
    def get_recent_events(self, hours: int = 24, limit: int = 100) -> List[AuditEvent]:
        """So'nggi eventlar"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [e for e in self.events if datetime.fromisoformat(e.timestamp) > cutoff]
        return recent[-limit:]
    
    def get_summary(self) -> AuditSummary:
        """Audit xulosasini olish"""
        return self.metrics
    
    def get_rule_statistics(self, rule_id: str) -> Dict[str, Any]:
        """Rule bo'yicha statistika"""
        rule_events = self.get_events_by_rule(rule_id)
        
        violations = len([e for e in rule_events if e.event_type == AuditEventType.RULE_VIOLATION])
        approvals = len([e for e in rule_events if e.event_type == AuditEventType.RULE_APPROVED])
        
        return {
            "rule_id": rule_id,
            "total_checks": len(rule_events),
            "violations": violations,
            "approvals": approvals,
            "violation_rate": violations / len(rule_events) if rule_events else 0
        }
    
    def resolve_event(self, event_id: str, resolution: str) -> bool:
        """Event ni hal qilish (resolved)"""
        if event_id not in self.event_index:
            return False
        
        event = self.event_index[event_id]
        event.resolved = True
        event.resolution = resolution
        
        return True
    
    def export_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event_types: Optional[List[AuditEventType]] = None
    ) -> List[Dict]:
        """Eventlarni export qilish"""
        
        filtered = self.events
        
        # Filter by date
        if start_date:
            start = datetime.fromisoformat(start_date)
            filtered = [e for e in filtered if datetime.fromisoformat(e.timestamp) >= start]
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            filtered = [e for e in filtered if datetime.fromisoformat(e.timestamp) <= end]
        
        # Filter by type
        if event_types:
            filtered = [e for e in filtered if e.event_type in event_types]
        
        return [self._event_to_dict(e) for e in filtered]
    
    def clear_old_events(self, days: int = 30):
        """Eski eventlarni tozalash (memory dan)"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._lock:
            self.events = [
                e for e in self.events 
                if datetime.fromisoformat(e.timestamp) > cutoff
            ]
            self.event_index = {e.event_id: e for e in self.events}
            self._update_metrics()


# Global audit
_audit: Optional[ConstitutionalAudit] = None


def get_constitutional_audit() -> ConstitutionalAudit:
    """Global audit olish"""
    global _audit
    if _audit is None:
        _audit = ConstitutionalAudit()
    return _audit


def log_rule_violation(
    rule_id: str,
    rule_name: str,
    message: str,
    details: Dict[str, Any] = None
) -> AuditEvent:
    """Rule violation log qilish (tez funksiya)"""
    audit = get_constitutional_audit()
    return audit.log_violation(rule_id, rule_name, message, details)


def log_promotion_blocked(
    reason: str,
    candidate_id: Optional[str] = None,
    rule_id: Optional[str] = None
) -> AuditEvent:
    """Promotion blocked log qilish (tez funksiya)"""
    audit = get_constitutional_audit()
    return audit.log_promotion_blocked(reason, candidate_id, rule_id)


def get_audit_summary() -> AuditSummary:
    """Audit xulosasini olish (tez funksiya)"""
    audit = get_constitutional_audit()
    return audit.get_summary()
