"""OmniAgent X - Approval Engine with Recovery"""
import json, logging, time, threading
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

    def __post_init__(self):
        if self.expires_at == 0.0: self.expires_at = time.time() + 300

    def is_expired(self) -> bool: return time.time() > self.expires_at
    def is_retryable(self) -> bool: return self.retry_count < self.max_retries
    def approve(self, by: str): self.status = ApprovalState.APPROVED; self.approved_by = by; self.approved_at = time.time()
    def deny(self, reason: str, by: str = "system"): self.status = ApprovalState.DENIED; self.denial_reason = reason; self.approved_by = by; self.approved_at = time.time()
    def to_dict(self) -> Dict: return {"request_id": self.request_id, "tool_name": self.tool_name, "arguments": self.arguments, "risk_level": self.risk_level, "requested_by": self.requested_by, "requested_at": self.requested_at, "status": self.status.value, "approved_by": self.approved_by, "approved_at": self.approved_at, "denial_reason": self.denial_reason, "expires_at": self.expires_at}
    @classmethod
    def from_dict(cls, d: Dict) -> 'ApprovalRequest': d = d.copy(); d["status"] = ApprovalState(d.get("status", "pending")); return cls(**d)

@dataclass
class ApprovalPolicy:
    tool_name: str; approval_level: ApprovalLevel
    timeout_seconds: int = 300; max_retries: int = 3

class RecoveryMapper:
    RETRY = "retry"; SKIP = "skip"; ALT = "alternative"; ABORT = "abort"
    def __init__(self):
        self.map = {"execute_command": {"on_deny": self.ALT, "alt_tool": "safe_execute"}, "delete_file": {"on_deny": self.ABORT}, "browser_navigate": {"on_deny": self.SKIP, "on_expire": self.RETRY}}
    self.default = {"on_deny": self.RETRY, "on_expire": self.RETRY, "max_retries": 3}
    def get_action(self, tool: str, reason=None, expired=False) -> Dict:
        m = self.map.get(tool, self.default); key = "on_expire" if expired else "on_deny"
        return {"strategy": m.get(key, self.RETRY), "tool": tool, "max": m.get("max_retries", 3), "alt": m.get("alt_tool")}
    def create_recovery(self, req: ApprovalRequest, action: Dict) -> Optional[ApprovalRequest]:
        if action["strategy"] in (self.SKIP, self.ABORT): return None
        return ApprovalRequest(request_id=f"{req.request_id}_r{req.retry_count+1}", tool_name=action.get("alt", req.tool_name), arguments=req.arguments, risk_level=req.risk_level, requested_by=req.requested_by, requested_at=time.time(), parent_request_id=req.request_id, recovery_action=action["strategy"], user_session_id=req.user_session_id, user_ip=req.user_ip)

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
        try:
            pf = self.pdir / "pending.json"
            if pf.exists():
                for d in json.load(open(pf)):
                    r = ApprovalRequest.from_dict(d)
                    if not r.is_expired(): self.pending[r.request_id] = r
            cf = self.pdir / "completed.json"
            if cf.exists():
                for d in json.load(open(cf))[-100:]:
                    self.completed[d["request_id"]] = ApprovalRequest.from_dict(d)
        except Exception as e: logger.warning(f"Load error: {e}")

    def _save(self):
        try:
            json.dump([r.to_dict() for r in self.pending.values()], open(self.pdir / "pending.json", "w"), indent=2)
            json.dump([r.to_dict() for r in list(self.completed.values())[-100:]], open(self.pdir / "completed.json", "w"), indent=2)
        except: pass

    def _start_cleanup(self):
        def loop():
            while True:
                time.sleep(60)
                try:
                    with self.lock:
                        expired = [rid for rid, r in self.pending.items() if r.is_expired()]
                        for rid in expired:
                            self.completed[rid] = self.pending.pop(rid)
                            self.completed[rid].status = ApprovalState.EXPIRED
                            self.audit.append({"action": "expire", "id": rid, "time": time.time()})
                    self._save()
                except: pass
        threading.Thread(target=loop, daemon=True).start()

    def request_approval(self, tool: str, args: Dict, requested_by: str = "system", risk: str = "medium", session_id: str = None, ip: str = None) -> str:
        pol = self.policies.get(tool)
        if pol and pol.approval_level == ApprovalLevel.AUTO: return "auto"
        
        req = ApprovalRequest(request_id=f"{int(time.time()*1000)}", tool_name=tool, arguments=args, risk_level=risk, requested_by=requested_by, requested_at=time.time(), expires_at=time.time() + (pol.timeout_seconds if pol else 300), user_session_id=session_id, user_ip=ip)
        
        with self.lock:
            self.pending[req.request_id] = req
            self.queue.put(req)
            self.audit.append({"action": "request", "id": req.request_id, "tool": tool, "by": requested_by})
        self._save()
        return req.request_id

    def approve(self, rid: str, by: str = "user", session_id: str = None, ip: str = None) -> bool:
        with self.lock:
            if rid not in self.pending: return False
            req = self.pending.pop(rid)
            req.approve(by)
            self.completed[rid] = req
            self.audit.append({"action": "approve", "id": rid, "by": by})
        self._save(); return True

    def deny(self, rid: str, reason: str, by: str = "user", session_id: str = None, ip: str = None) -> bool:
        with self.lock:
            if rid not in self.pending: return False
            req = self.pending.pop(rid)
            req.deny(reason, by)
            self.completed[rid] = req
            self.audit.append({"action": "deny", "id": rid, "by": by, "reason": reason})
            
            # Recovery
            action = self.recovery.get_action(req.tool_name, reason)
            if action["strategy"] == RecoveryMapper.RETRY:
                recovery_req = self.recovery.create_recovery(req, action)
                if recovery_req:
                    self.pending[recovery_req.request_id] = recovery_req
                    self.audit.append({"action": "retry", "id": recovery_req.request_id, "parent": rid})
        self._save(); return True

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

def create_approval_engine(pdir: str = "/tmp/approval") -> ApprovalEngine:
    return ApprovalEngine(pdir=pdir)
