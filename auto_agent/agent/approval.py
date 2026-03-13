"""
OmniAgent X - Tool Approval Workflow
===================================
Stateful approval system for dangerous tools

Features:
- Approval queue with states
- GUI/Telegram integration
- Timeout handling
- Approval history
- Multi-user support
"""
import os
import json
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue
import uuid

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ApprovalState(Enum):
    """Approval request states"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalLevel(Enum):
    """Approval requirement levels"""
    AUTO = "auto"          # No approval needed
    CONFIRM = "confirm"    # User confirmation
    BLOCKED = "blocked"    # Never allowed


# ==================== DATA CLASSES ====================

@dataclass
class ApprovalRequest:
    """Tool approval request"""
    request_id: str
    tool_name: str
    arguments: Dict[str, Any]
    risk_level: str  # safe, medium, high, critical
    requested_by: str  # user or system
    requested_at: float
    status: ApprovalState = ApprovalState.PENDING
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    denial_reason: Optional[str] = None
    expires_at: float = 0.0
    
    def __post_init__(self):
        if self.expires_at == 0.0:
            self.expires_at = time.time() + 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def approve(self, approved_by: str):
        self.status = ApprovalState.APPROVED
        self.approved_by = approved_by
        self.approved_at = time.time()
    
    def deny(self, reason: str, denied_by: str = "system"):
        self.status = ApprovalState.DENIED
        self.denial_reason = reason
        self.approved_by = denied_by
        self.approved_at = time.time()


@dataclass
class ApprovalPolicy:
    """Policy for tool approvals"""
    tool_name: str
    approval_level: ApprovalLevel
    timeout_seconds: int = 300
    max_retries: int = 3
    require_reason: bool = False
    allowed_users: List[str] = field(default_factory=list)  # Empty = all


# ==================== APPROVAL ENGINE ====================

class ApprovalEngine:
    """
    Stateful approval workflow engine
    Handles approval requests from all interfaces
    """
    
    def __init__(self):
        # Approval requests
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.completed_requests: Dict[str, ApprovalRequest] = {}
        
        # Approval queue
        self.approval_queue: Queue = Queue()
        
        # Policies
        self.policies: Dict[str, ApprovalPolicy] = {}
        self._register_default_policies()
        
        # Callbacks for notifications
        self.notification_callbacks: List[Callable] = []
        
        # History
        self.max_history = 1000
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        logger.info("✅ Approval Engine initialized")
    
    def _register_default_policies(self):
        """Register default approval policies"""
        
        default_policies = [
            # Safe tools - auto approve
            ApprovalPolicy("web_search", ApprovalLevel.AUTO),
            ApprovalPolicy("read_file", ApprovalLevel.AUTO),
            ApprovalPolicy("get_system_info", ApprovalLevel.AUTO),
            ApprovalPolicy("take_screenshot", ApprovalLevel.AUTO),
            ApprovalPolicy("think", ApprovalLevel.AUTO),
            
            # Medium risk - require confirmation
            ApprovalPolicy("write_file", ApprovalLevel.CONFIRM),
            ApprovalPolicy("execute_code", ApprovalLevel.CONFIRM),
            ApprovalPolicy("browser_navigate", ApprovalLevel.CONFIRM),
            
            # High risk - require explicit approval
            ApprovalPolicy("execute_command", ApprovalLevel.CONFIRM, timeout_seconds=60),
            ApprovalPolicy("delete_file", ApprovalLevel.BLOCKED),
            ApprovalPolicy("format_disk", ApprovalLevel.BLOCKED),
            ApprovalPolicy("system_reboot", ApprovalLevel.BLOCKED),
        ]
        
        for policy in default_policies:
            self.policies[policy.tool_name] = policy
    
    def register_policy(self, policy: ApprovalPolicy):
        """Register a custom approval policy"""
        self.policies[policy.tool_name] = policy
    
    def request_approval(self, tool_name: str, arguments: Dict[str, Any],
                        requested_by: str = "system",
                        risk_level: str = "medium") -> str:
        """
        Request approval for a tool
        Returns request_id
        """
        
        # Check policy
        policy = self.policies.get(tool_name)
        
        if policy and policy.approval_level == ApprovalLevel.AUTO:
            # Auto approve
            return "auto"
        
        # Create request
        request = ApprovalRequest(
            request_id=str(uuid.uuid4())[:12],
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            requested_by=requested_by,
            requested_at=time.time(),
            expires_at=time.time() + (policy.timeout_seconds if policy else 300)
        )
        
        with self.lock:
            self.pending_requests[request.request_id] = request
            self.approval_queue.put(request)
        
        # Notify via callbacks
        self._notify_request(request)
        
        logger.info(f"📋 Approval requested: {tool_name} (ID: {request.request_id})")
        
        return request.request_id
    
    def approve(self, request_id: str, approved_by: str = "user") -> bool:
        """Approve a request"""
        
        with self.lock:
            if request_id not in self.pending_requests:
                logger.warning(f"Request not found: {request_id}")
                return False
            
            request = self.pending_requests[request_id]
            request.approve(approved_by)
            
            # Move to completed
            self.completed_requests[request_id] = request
            del self.pending_requests[request_id]
        
        logger.info(f"✅ Request approved: {request_id} by {approved_by}")
        return True
    
    def deny(self, request_id: str, reason: str, denied_by: str = "user") -> bool:
        """Deny a request"""
        
        with self.lock:
            if request_id not in self.pending_requests:
                return False
            
            request = self.pending_requests[request_id]
            request.deny(reason, denied_by)
            
            self.completed_requests[request_id] = request
            del self.pending_requests[request_id]
        
        logger.info(f"❌ Request denied: {request_id} by {denied_by}")
        return True
    
    def get_pending(self) -> List[ApprovalRequest]:
        """Get all pending requests"""
        with self.lock:
            return list(self.pending_requests.values())
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get request by ID"""
        with self.lock:
            if request_id in self.pending_requests:
                return self.pending_requests[request_id]
            if request_id in self.completed_requests:
                return self.completed_requests[request_id]
        return None
    
    def check_approval(self, request_id: str) -> bool:
        """Check if request is approved"""
        
        request = self.get_request(request_id)
        
        if not request:
            return False
        
        if request_id == "auto":
            return True
        
        if request.is_expired():
            request.status = ApprovalState.EXPIRED
            return False
        
        return request.status == ApprovalState.APPROVED
    
    def wait_for_approval(self, request_id: str, timeout: float = 60.0) -> bool:
        """Wait for approval with timeout"""
        
        start = time.time()
        
        while time.time() - start < timeout:
            if self.check_approval(request_id):
                return True
            
            # Check if expired
            request = self.get_request(request_id)
            if request and request.is_expired():
                return False
            
            time.sleep(0.5)
        
        return False
    
    def cancel_expired(self):
        """Cancel expired requests"""
        with self.lock:
            expired = []
            
            for request_id, request in self.pending_requests.items():
                if request.is_expired():
                    request.status = ApprovalState.EXPIRED
                    self.completed_requests[request_id] = request
                    expired.append(request_id)
            
            for request_id in expired:
                del self.pending_requests[request_id]
            
            if expired:
                logger.info(f"⏰ Expired {len(expired)} requests")
    
    def register_notification_callback(self, callback: Callable):
        """Register callback for approval notifications"""
        self.notification_callbacks.append(callback)
    
    def _notify_request(self, request: ApprovalRequest):
        """Notify about new approval request"""
        for callback in self.notification_callbacks:
            try:
                callback(request)
            except Exception as e:
                logger.error(f"Notification callback error: {e}")
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get approval history"""
        
        with self.lock:
            history = list(self.completed_requests.values())[-limit:]
        
        return [
            {
                "request_id": r.request_id,
                "tool_name": r.tool_name,
                "status": r.status.value,
                "requested_by": r.requested_by,
                "approved_by": r.approved_by,
                "requested_at": r.requested_at,
                "approved_at": r.approved_at,
            }
            for r in history
        ]
    
    def get_stats(self) -> Dict:
        """Get approval statistics"""
        
        with self.lock:
            total = len(self.completed_requests)
            approved = sum(1 for r in self.completed_requests.values() 
                         if r.status == ApprovalState.APPROVED)
            denied = sum(1 for r in self.completed_requests.values() 
                       if r.status == ApprovalState.DENIED)
            expired = sum(1 for r in self.completed_requests.values() 
                        if r.status == ApprovalState.EXPIRED)
        
        return {
            "pending": len(self.pending_requests),
            "total": total,
            "approved": approved,
            "denied": denied,
            "expired": expired,
            "approval_rate": approved / total if total > 0 else 0
        }


# ==================== APPROVAL INTEGRATION ====================

class ApprovalIntegration:
    """
    Integrates approval with GUI and Telegram
    """
    
    def __init__(self, engine: ApprovalEngine):
        self.engine = engine
        
        # Register default callbacks
        self._setup_default_handlers()
        
        logger.info("🔗 Approval Integration initialized")
    
    def _setup_default_handlers(self):
        """Setup default handlers for different interfaces"""
        
        # These would be replaced with actual GUI/Telegram handlers
        pass
    
    def create_gui_handler(self):
        """Create GUI approval handler"""
        
        def handle_approval(request_id: str, approved: bool, reason: str = ""):
            if approved:
                self.engine.approve(request_id, "gui_user")
            else:
                self.engine.deny(request_id, reason, "gui_user")
        
        return handle_approval
    
    def create_telegram_handler(self):
        """Create Telegram approval handler"""
        
        def handle_approval(request_id: str, approved: bool, user_id: str, reason: str = ""):
            if approved:
                self.engine.approve(request_id, f"telegram_{user_id}")
            else:
                self.engine.deny(request_id, reason, f"telegram_{user_id}")
        
        return handle_approval
    
    def format_approval_message(self, request: ApprovalRequest) -> str:
        """Format approval request as message"""
        
        args_str = json.dumps(request.arguments, indent=2)[:200]
        
        return f"""⚠️ **Ruxsat so'rovi**

🔧 **Tool:** {request.tool_name}
📋 **Argumentlar:**
```
{args_str}
```

⚠️ **Xavf darajasi:** {request.risk_level}
⏰ **Muddati:** {datetime.fromtimestamp(request.expires_at).strftime('%H:%M:%S')}

✅ Ruxsat berish uchun: /approve {request.request_id}
❌ Rad etish uchun: /deny {request.request_id} [sabab]"""


# ==================== FACTORY ====================

def create_approval_engine() -> ApprovalEngine:
    """Create approval engine"""
    return ApprovalEngine()
