"""OmniAgent X - Approval Engine with Recovery"""
import json, logging, time, threading, shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue
from pathlib import Path

logger = logging.getLogger(__name__)

class ApprovalState(Enum):
    PENDING = "pending"; APPROVED = "approved"; DENIED = "denied"; EXPIRED = "expired"

class ApprovalLevel(Enum):
    AUTO = "auto"; CONFIRM = "confirm"; BLOCKED = "blocked"

@dataclass
class ApprovalRequest:
    request_id: str; tool_name: str; arguments: Dict; risk_level: str
    requested_by: str; requested_at: float; status: ApprovalState = ApprovalState.PENDING
    approved_by: Optional[str] = None; approved_at: Optional[float] = None
    denial_reason: Optional[str] = None; expires_at: float = 0.0
    parent_request_id: Optional[str] = None; recovery_action: Optional[str] = None
    user_session_id: Optional[str] = None; user_ip: Optional[str] = None
    retry_count: int = 0; max_retries: int = 3
    metadata: Dict = field(default_factory=dict)
    
    # Enhanced audit fields
    denial_category: Optional[str] = None  # Category: security, policy, validation, timeout, manual
    denial_details: Optional[str] = None  # Detailed reason text
    expiry_reason: Optional[str] = None  # Why expired: timeout, system_shutdown, etc.
    trace_id: Optional[str] = None  # For distributed tracing
    user_agent: Optional[str] = None  # User client info
    latency_ms: Optional[float] = None  # Approval latency in milliseconds
    previous_status: Optional[str] = None  # Previous status for state transitions
    kernel_recovery_triggered: bool = False  # If kernel recovery was triggered
    recovery_chain: List[str] = field(default_factory=list)  # Chain of recovery attempts

    def __post_init__(self):
        if self.expires_at == 0.0: self.expires_at = time.time() + 300

    def is_expired(self) -> bool: return time.time() > self.expires_at
    def is_retryable(self) -> bool: return self.retry_count < self.max_retries
    
    def approve(self, by: str, latency_ms: float = None):
        self.previous_status = self.status.value
        self.status = ApprovalState.APPROVED
        self.approved_by = by
        self.approved_at = time.time()
        self.latency_ms = latency_ms or ((self.approved_at - self.requested_at) * 1000)
    
    def deny(self, reason: str, by: str = "system", category: str = "manual"):
        self.previous_status = self.status.value
        self.status = ApprovalState.DENIED
        self.denial_reason = reason
        self.denial_category = category
        self.approved_by = by
        self.approved_at = time.time()
        self.latency_ms = (self.approved_at - self.requested_at) * 1000
    
    def mark_expired(self, reason: str = "timeout"):
        self.previous_status = self.status.value
        self.status = ApprovalState.EXPIRED
        self.expiry_reason = reason
    
    def add_to_recovery_chain(self, recovery_id: str):
        """Add a recovery attempt to the chain."""
        if self.recovery_chain is None:
            self.recovery_chain = []
        self.recovery_chain.append(recovery_id)
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "risk_level": self.risk_level,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "status": self.status.value,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "denial_reason": self.denial_reason,
            "denial_category": self.denial_category,
            "denial_details": self.denial_details,
            "expires_at": self.expires_at,
            "expiry_reason": self.expiry_reason,
            "parent_request_id": self.parent_request_id,
            "recovery_action": self.recovery_action,
            "user_session_id": self.user_session_id,
            "user_ip": self.user_ip,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "trace_id": self.trace_id,
            "user_agent": self.user_agent,
            "latency_ms": self.latency_ms,
            "previous_status": self.previous_status,
            "kernel_recovery_triggered": self.kernel_recovery_triggered,
            "recovery_chain": self.recovery_chain,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'ApprovalRequest':
        d = d.copy()
        d["status"] = ApprovalState(d.get("status", "pending"))
        # Handle optional fields that might be missing
        d.setdefault("denial_category", None)
        d.setdefault("denial_details", None)
        d.setdefault("expiry_reason", None)
        d.setdefault("trace_id", None)
        d.setdefault("user_agent", None)
        d.setdefault("latency_ms", None)
        d.setdefault("previous_status", None)
        d.setdefault("kernel_recovery_triggered", False)
        d.setdefault("recovery_chain", [])
        return cls(**d)

@dataclass
class ApprovalPolicy:
    tool_name: str; approval_level: ApprovalLevel
    timeout_seconds: int = 300; max_retries: int = 3


class DenialCategory(Enum):
    """Taxonomy of denial reasons for better analytics and recovery."""
    SECURITY = "security"  # Security policy violation
    POLICY = "policy"  # Internal policy violation
    VALIDATION = "validation"  # Input validation failure
    TIMEOUT = "timeout"  # User did not respond in time
    MANUAL = "manual"  # Manual denial by user
    SYSTEM = "system"  # System-level denial
    RATE_LIMIT = "rate_limit"  # Too many requests
    PERMISSION = "permission"  # Insufficient permissions


class RecoveryMapper:
    RETRY = "retry"; SKIP = "skip"; ALT = "alternative"; ABORT = "abort"; ESCALATE = "escalate"
    
    # Recovery strategies based on denial category
    CATEGORY_RECOVERY = {
        DenialCategory.SECURITY: {"strategy": ABORT, "notify_security": True},
        DenialCategory.POLICY: {"strategy": RETRY, "notify_admin": True},
        DenialCategory.VALIDATION: {"strategy": RETRY, "fix_input": True},
        DenialCategory.TIMEOUT: {"strategy": RETRY, "increase_timeout": True},
        DenialCategory.MANUAL: {"strategy": RETRY},
        DenialCategory.SYSTEM: {"strategy": ESCALATE, "notify_admin": True},
        DenialCategory.RATE_LIMIT: {"strategy": RETRY, "backoff": True},
        DenialCategory.PERMISSION: {"strategy": ESCALATE},
    }
    
    def __init__(self):
        self.map = {
            "execute_command": {"on_deny": self.ALT, "alt_tool": "safe_execute"},
            "delete_file": {"on_deny": self.ABORT},
            "browser_navigate": {"on_deny": self.SKIP, "on_expire": self.RETRY}
        }
        self.default = {"on_deny": self.RETRY, "on_expire": self.RETRY, "max_retries": 3}
    
    def get_action(self, tool: str, reason=None, expired=False, category: str = None) -> Dict:
        """Get recovery action with category awareness."""
        m = self.map.get(tool, self.default)
        key = "on_expire" if expired else "on_deny"
        
        base_action = {
            "strategy": m.get(key, self.RETRY),
            "tool": tool,
            "max": m.get("max_retries", 3),
            "alt": m.get("alt_tool")
        }
        
        # Add category-specific recovery
        if category:
            try:
                cat_enum = DenialCategory(category.lower())
                cat_recovery = self.CATEGORY_RECOVERY.get(cat_enum, {})
                base_action.update(cat_recovery)
            except ValueError as e:
                logger.debug(f"Invalid category: {e}")
        
        return base_action
    
    def create_recovery(self, req: ApprovalRequest, action: Dict) -> Optional[ApprovalRequest]:
        if action["strategy"] in (self.SKIP, self.ABORT):
            return None
        
        recovery_req = ApprovalRequest(
            request_id=f"{req.request_id}_r{req.retry_count+1}",
            tool_name=action.get("alt", req.tool_name),
            arguments=req.arguments,
            risk_level=req.risk_level,
            requested_by=req.requested_by,
            requested_at=time.time(),
            parent_request_id=req.request_id,
            recovery_action=action["strategy"],
            user_session_id=req.user_session_id,
            user_ip=req.user_ip,
            trace_id=req.trace_id
        )
        
        # Copy recovery chain
        if req.recovery_chain:
            recovery_req.recovery_chain = req.recovery_chain.copy()
        recovery_req.add_to_recovery_chain(req.request_id)
        
        return recovery_req

class ApprovalEngine:
    def __init__(self, pdir: str = "/tmp/approval"):
        self.pdir = Path(pdir); self.pdir.mkdir(parents=True, exist_ok=True)
        self.pending: Dict[str, ApprovalRequest] = {}
        self.completed: Dict[str, ApprovalRequest] = {}
        self.queue: Queue = Queue()
        self.policies: Dict[str, ApprovalPolicy] = {}
        self.callbacks: List = []
        self.lock = threading.Lock()
        self.audit: List[Dict] = []
        self.user_traces: Dict[str, Dict] = {}
        self.recovery = RecoveryMapper()
        self._load(); self._start_cleanup()
        self._register_default_policies()
        logger.info("Approval Engine initialized")

    def _register_default_policies(self):
        for tool, level in [("web_search", ApprovalLevel.AUTO), ("read_file", ApprovalLevel.AUTO), ("get_system_info", ApprovalLevel.AUTO), ("write_file", ApprovalLevel.CONFIRM), ("execute_code", ApprovalLevel.CONFIRM), ("execute_command", ApprovalLevel.CONFIRM), ("delete_file", ApprovalLevel.BLOCKED)]:
            self.policies[tool] = ApprovalPolicy(tool, level)

    def _load(self):
        """Load pending and completed approvals from disk."""
        try:
            pf = self.pdir / "pending.json"
            if pf.exists():
                data = json.load(open(pf))
                for d in data:
                    r = ApprovalRequest.from_dict(d)
                    if not r.is_expired():
                        self.pending[r.request_id] = r
            cf = self.pdir / "completed.json"
            if cf.exists():
                data = json.load(open(cf))
                for d in data[-100:]:
                    self.completed[d["request_id"]] = ApprovalRequest.from_dict(d)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted approval JSON file: {e}")
            # Backup corrupted file
            self._backup_corrupted_file()
        except Exception as e:
            logger.error(f"Failed to load approvals: {e}")
            # Don't lose data - continue with empty state
    
    def _backup_corrupted_file(self):
        """Backup corrupted files for diagnostics."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for filename in ["pending.json", "completed.json"]:
            filepath = self.pdir / filename
            if filepath.exists():
                backup_path = self.pdir / f"{filename}.backup_{timestamp}"
                try:
                    shutil.copy2(filepath, backup_path)
                    logger.info(f"Backed up corrupted {filename} to {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to backup {filename}: {e}")

    def _save(self):
        """Save pending and completed approvals to disk with proper error handling."""
        try:
            pending_path = self.pdir / "pending.json"
            json.dump(
                [r.to_dict() for r in self.pending.values()],
                open(pending_path, "w"),
                indent=2
            )
            
            completed_path = self.pdir / "completed.json"
            # Keep last 100 completed approvals
            completed_list = list(self.completed.values())
            json.dump(
                [r.to_dict() for r in completed_list[-100:]],
                open(completed_path, "w"),
                indent=2
            )
            
            logger.debug(f"Saved {len(self.pending)} pending, {len(self.completed)} completed approvals")
            
        except PermissionError as e:
            logger.error(f"Permission denied saving approvals: {e}")
            # Try alternative location
            self._save_to_alternative()
        except OSError as e:
            logger.error(f"OS error saving approvals: {e}")
            # Try alternative location
            self._save_to_alternative()
        except Exception as e:
            logger.error(f"Failed to save approvals: {e}")
            # At minimum, try to save audit log separately
            self._save_audit_emergency()

    def _save_to_alternative(self):
        """Try saving to alternative location if primary fails."""
        alt_dir = Path("/tmp/approval_fallback")
        alt_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            json.dump(
                [r.to_dict() for r in self.pending.values()],
                open(alt_dir / "pending.json", "w"),
                indent=2
            )
            json.dump(
                [r.to_dict() for r in list(self.completed.values())[-100:]],
                open(alt_dir / "completed.json", "w"),
                indent=2
            )
            logger.warning(f"Saved approvals to fallback location: {alt_dir}")
        except Exception as e:
            logger.error(f"Fallback save also failed: {e}")

    def _save_audit_emergency(self):
        """Emergency save of audit log only."""
        try:
            audit_path = self.pdir / "audit_emergency.json"
            json.dump(self.audit[-100:], open(audit_path, "w"), indent=2)
            logger.info("Emergency audit log saved")
        except Exception as e:
            logger.critical(f"CRITICAL: Could not save audit log: {e}")

    def _start_cleanup(self):
        def loop():
            while True:
                time.sleep(60)
                try:
                    with self.lock:
                        expired = [rid for rid, r in self.pending.items() if r.is_expired()]
                        for rid in expired:
                            req = self.pending.pop(rid)
                            req.status = ApprovalState.EXPIRED
                            self.completed[rid] = req
                            
                            # Detailed audit with full context
                            self.audit.append({
                                "action": "expire",
                                "id": rid,
                                "time": time.time(),
                                "tool": req.tool_name,
                                "requested_by": req.requested_by,
                                "risk_level": req.risk_level,
                                "duration": time.time() - req.requested_at
                            })
                    
                    self._save()
                    
                except PermissionError as e:
                    logger.error(f"Cleanup: Permission denied - {e}")
                except OSError as e:
                    logger.error(f"Cleanup: OS error - {e}")
                except Exception as e:
                    logger.error(f"Cleanup: Unexpected error - {e}")
                    # Don't let cleanup loop die - log and continue
                    
        threading.Thread(target=loop, daemon=True).start()

    def request_approval(self, tool: str, args: Dict, requested_by: str = "system", risk: str = "medium", 
                        session_id: str = None, ip: str = None, user_agent: str = None, 
                        trace_id: str = None) -> str:
        """
        Request approval for an action with full context tracking.
        
        Args:
            tool: Tool name being requested
            args: Arguments for the tool
            requested_by: Who is requesting
            risk: Risk level (low, medium, high)
            session_id: User session ID
            ip: User IP address
            user_agent: User client info
            trace_id: Distributed tracing ID
        """
        pol = self.policies.get(tool)
        if pol and pol.approval_level == ApprovalLevel.AUTO: return "auto"
        
        req = ApprovalRequest(
            request_id=f"{int(time.time()*1000)}",
            tool_name=tool,
            arguments=args,
            risk_level=risk,
            requested_by=requested_by,
            requested_at=time.time(),
            expires_at=time.time() + (pol.timeout_seconds if pol else 300),
            user_session_id=session_id,
            user_ip=ip,
            user_agent=user_agent,
            trace_id=trace_id
        )
        
        with self.lock:
            self.pending[req.request_id] = req
            self.queue.put(req)
            
            # Rich audit trail for request
            self.audit.append({
                "action": "request",
                "id": req.request_id,
                "tool": tool,
                "by": requested_by,
                "risk_level": risk,
                "session_id": session_id,
                "ip": ip,
                "trace_id": trace_id,
                "time": time.time()
            })
            
            # Initialize user trace
            self._update_user_trace(session_id, "request", req)
        
        self._save()
        return req.request_id

    def approve(self, rid: str, by: str = "user", session_id: str = None, ip: str = None, user_agent: str = None) -> bool:
        """Approve an approval request with full audit trail."""
        with self.lock:
            if rid not in self.pending:
                logger.warning(f"Approve failed: {rid} not in pending")
                return False
            
            req = self.pending.pop(rid)
            latency_ms = (time.time() - req.requested_at) * 1000
            req.approve(by, latency_ms)
            
            # Store user context
            if session_id:
                req.user_session_id = session_id
            if ip:
                req.user_ip = ip
            if user_agent:
                req.user_agent = user_agent
            
            self.completed[rid] = req
            
            # Rich audit trail
            self.audit.append({
                "action": "approve",
                "id": rid,
                "tool": req.tool_name,
                "by": by,
                "risk_level": req.risk_level,
                "latency_ms": latency_ms,
                "session_id": session_id,
                "ip": ip,
                "time": time.time()
            })
            
            # Update user trace
            self._update_user_trace(session_id, "approve", req)
            
        self._save()
        logger.info(f"Approved request {rid} by {by} (latency: {latency_ms:.2f}ms)")
        return True

    def deny(self, rid: str, reason: str, by: str = "user", session_id: str = None, ip: str = None, 
             category: str = "manual", details: str = None) -> bool:
        """
        Deny an approval request with full audit trail and kernel recovery integration.
        
        Args:
            rid: Request ID
            reason: Human-readable denial reason
            by: Who denied the request
            session_id: User session
            ip: User IP
            category: Denial category (security, policy, validation, timeout, manual)
            details: Additional details about the denial
        """
        with self.lock:
            if rid not in self.pending:
                logger.warning(f"Deny failed: {rid} not in pending")
                return False
            
            req = self.pending.pop(rid)
            latency_ms = (time.time() - req.requested_at) * 1000
            req.deny(reason, by, category)
            
            # Store additional context
            if session_id:
                req.user_session_id = session_id
            if ip:
                req.user_ip = ip
            if details:
                req.denial_details = details
            
            self.completed[rid] = req
            
            # Get recovery action with category awareness
            action = self.recovery.get_action(req.tool_name, reason, category=category)
            
            # Rich audit trail with full context
            self.audit.append({
                "action": "deny",
                "id": rid,
                "tool": req.tool_name,
                "by": by,
                "reason": reason,
                "category": category,
                "details": details,
                "risk_level": req.risk_level,
                "latency_ms": latency_ms,
                "recovery_strategy": action.get("strategy"),
                "notify_security": action.get("notify_security", False),
                "notify_admin": action.get("notify_admin", False),
                "session_id": session_id,
                "ip": ip,
                "time": time.time()
            })
            
            # Update user trace
            self._update_user_trace(session_id, "deny", req)
            
            # Handle recovery based on action
            if action["strategy"] == RecoveryMapper.RETRY:
                recovery_req = self.recovery.create_recovery(req, action)
                if recovery_req:
                    self.pending[recovery_req.request_id] = recovery_req
                    self.audit.append({
                        "action": "retry_created",
                        "id": recovery_req.request_id,
                        "parent": rid,
                        "strategy": action.get("strategy"),
                        "time": time.time()
                    })
                    logger.info(f"Created recovery request {recovery_req.request_id} for denied {rid}")
            
            elif action["strategy"] == RecoveryMapper.ESCALATE:
                # Trigger kernel escalation
                self._trigger_kernel_escalation(req, action)
                
            elif action.get("notify_security"):
                self._notify_security_team(req, reason)
                
            elif action.get("notify_admin"):
                self._notify_admin(req, reason)
        
        self._save()
        logger.info(f"Denied request {rid} by {by} (category: {category}, reason: {reason})")
        return True
    
    def _update_user_trace(self, session_id: str, action: str, req: ApprovalRequest):
        """Update user trace for analytics."""
        if not session_id:
            return
        
        if session_id not in self.user_traces:
            self.user_traces[session_id] = {
                "session_id": session_id,
                "first_seen": time.time(),
                "actions": [],
                "approvals": 0,
                "denials": 0
            }
        
        trace = self.user_traces[session_id]
        trace["actions"].append({
            "action": action,
            "request_id": req.request_id,
            "tool": req.tool_name,
            "risk_level": req.risk_level,
            "time": time.time()
        })
        
        if action == "approve":
            trace["approvals"] += 1
        elif action == "deny":
            trace["denials"] += 1
    
    def _trigger_kernel_escalation(self, req: ApprovalRequest, action: Dict):
        """Trigger kernel-level escalation for critical denials."""
        # Mark request for kernel recovery
        req.kernel_recovery_triggered = True
        
        # Log for kernel to pick up
        escalation_event = {
            "type": "approval_escalation",
            "request_id": req.request_id,
            "tool": req.tool_name,
            "reason": req.denial_reason,
            "category": req.denial_category,
            "action": action,
            "timestamp": time.time()
        }
        
        # Write to kernel watch file if exists
        kernel_file = Path("/tmp/kernel_approval_escalation")
        try:
            with open(kernel_file, "a") as f:
                json.dump(escalation_event, f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write kernel escalation: {e}")
        
        self.audit.append({
            "action": "kernel_escalation",
            "id": req.request_id,
            "strategy": action.get("strategy"),
            "time": time.time()
        })
        
        logger.warning(f"Kernel escalation triggered for {req.request_id}")
    
    def _notify_security_team(self, req: ApprovalRequest, reason: str):
        """Notify security team of security-related denial."""
        # In production, this would send to SIEM, Slack, email, etc.
        logger.warning(f"🔒 SECURITY ALERT: Request {req.request_id} denied - {reason}")
        self.audit.append({
            "action": "security_notification",
            "id": req.request_id,
            "reason": reason,
            "time": time.time()
        })
    
    def _notify_admin(self, req: ApprovalRequest, reason: str):
        """Notify admin of policy-related denial."""
        logger.warning(f"📢 ADMIN ALERT: Request {req.request_id} denied - {reason}")
        self.audit.append({
            "action": "admin_notification",
            "id": req.request_id,
            "reason": reason,
            "time": time.time()
        })

    def check(self, rid: str) -> bool:
        if rid == "auto": return True
        req = self.get(rid)
        if not req: return False
        if req.is_expired(): return False
        return req.status == ApprovalState.APPROVED

    def wait(self, rid: str, timeout: float = 60.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self.check(rid): return True
            if self.get(rid) and self.get(rid).is_expired(): return False
            time.sleep(0.5)
        return False

    def get(self, rid: str) -> Optional[ApprovalRequest]:
        if rid in self.pending: return self.pending[rid]
        if rid in self.completed: return self.completed[rid]
        return None

    def get_pending(self) -> List[ApprovalRequest]: return list(self.pending.values())
    def get_all(self, limit: int = 50) -> List[Dict]: return [{"id": r.request_id, "tool": r.tool_name, "status": r.status.value, "by": r.requested_by, "at": r.requested_at} for r in list(self.completed.values())[-limit:]]
    def get_stats(self) -> Dict: return {"pending": len(self.pending), "completed": len(self.completed), "audit": len(self.audit)}
    
    # ==================== AUDIT & DIAGNOSTICS ====================
    
    def get_audit_trail(self, limit: int = 100, action_filter: str = None) -> List[Dict]:
        """
        Get audit trail with optional filtering.
        
        Args:
            limit: Maximum number of entries to return
            action_filter: Filter by action type (approve, deny, expire, etc.)
        """
        audit = self.audit[-limit:]
        
        if action_filter:
            audit = [a for a in audit if a.get("action") == action_filter]
        
        return audit
    
    def get_audit_by_request(self, rid: str) -> List[Dict]:
        """Get all audit entries for a specific request."""
        return [a for a in self.audit if a.get("id") == rid]
    
    def get_denial_analysis(self) -> Dict:
        """Get analytics on denials for pattern detection."""
        denials = [a for a in self.audit if a.get("action") == "deny"]
        
        if not denials:
            return {"total_denials": 0, "by_category": {}, "by_tool": {}, "by_user": {}}
        
        by_category = {}
        by_tool = {}
        by_user = {}
        
        for d in denials:
            cat = d.get("category", "unknown")
            tool = d.get("tool", "unknown")
            user = d.get("by", "unknown")
            
            by_category[cat] = by_category.get(cat, 0) + 1
            by_tool[tool] = by_tool.get(tool, 0) + 1
            by_user[user] = by_user.get(user, 0) + 1
        
        return {
            "total_denials": len(denials),
            "by_category": by_category,
            "by_tool": by_tool,
            "by_user": by_user,
            "recent_denials": denials[-10:]
        }
    
    def get_recovery_chain(self, request_id: str) -> List[Dict]:
        """Get the full recovery chain for a request."""
        chain = []
        
        # Find original request
        current_id = request_id
        
        while current_id:
            req = self.get(current_id)
            if not req:
                break
            
            chain.append({
                "request_id": req.request_id,
                "status": req.status.value,
                "recovery_action": req.recovery_action,
                "timestamp": req.requested_at
            })
            
            # Move to parent if exists
            current_id = req.parent_request_id
        
        return chain
    
    def diagnose_failure(self, request_id: str) -> Dict:
        """
        Diagnose why a request failed or was denied.
        
        Returns detailed diagnostics for debugging.
        """
        req = self.get(request_id)
        
        if not req:
            return {"error": "Request not found", "request_id": request_id}
        
        audit = self.get_audit_by_request(request_id)
        
        diagnostics = {
            "request": req.to_dict(),
            "audit_trail": audit,
            "recovery_chain": self.get_recovery_chain(request_id),
            "timeline": self._build_timeline(audit)
        }
        
        return diagnostics
    
    def _build_timeline(self, audit: List[Dict]) -> List[Dict]:
        """Build a chronological timeline from audit entries."""
        timeline = []
        for entry in audit:
            timeline.append({
                "time": entry.get("time"),
                "action": entry.get("action"),
                "details": {
                    "by": entry.get("by"),
                    "reason": entry.get("reason"),
                    "category": entry.get("category"),
                    "strategy": entry.get("recovery_strategy")
                }
            })
        
        return sorted(timeline, key=lambda x: x.get("time", 0))
    
    def export_diagnostics(self, output_path: str = "/tmp/approval_diagnostics.json") -> str:
        """Export full diagnostics for support/debugging."""
        diagnostics = {
            "export_time": time.time(),
            "stats": self.get_stats(),
            "denial_analysis": self.get_denial_analysis(),
            "recent_audit": self.audit[-100:],
            "user_traces": self.user_traces
        }
        
        try:
            with open(output_path, "w") as f:
                json.dump(diagnostics, f, indent=2, default=str)
            return output_path
        except Exception as e:
            logger.error(f"Failed to export diagnostics: {e}")
            return None

def create_approval_engine(pdir: str = "/tmp/approval") -> ApprovalEngine:
    return ApprovalEngine(pdir=pdir)
