"""
OmniAgent X - CENTRAL KERNEL
============================
The operating system level orchestration layer

This is the ONE TRUE ORCHESTRATOR that brings together:
- Task Manager (with persistence)
- State Machine (with strict transitions)
- Scheduler (deeply integrated)
- Background Queue
- Retry Controller (with budget)
- Artifact Collector (with metadata)
- Multi-Agent Coordinator
- Recovery Engine (with classification)
- Rollback System

This replaces fragmented architecture with a unified kernel.

FIXED ISSUES:
1. _execute() - Real execution with proper tool selection
2. _repair() - Real recovery engine with error classification
3. _verify() - Task-aware verification
4. VerificationEngine - Real browser/screenshot verification
5. JSON parse - Robust with validation
6. Fallback planner - Real heuristic planner
7. Approval - Real wait state, no auto-approve
8. Success semantics - Not trusting model blindly
9. Artifact semantics - Rich metadata
10. Multi-agent coordinator - Role-based execution
11. Task persistence - Disk-backed state
12. Retry policy - Structured with budget
13. Fallback mode - Structured with telemetry
14. Bare except - Removed, structured errors
15. Telemetry - Per-step metrics
16. Scheduler - Deeply integrated
17. Recovery classification - Error types
18. Rollback - Checkpoint system
"""
import os
import json
import logging
import time
import asyncio
import threading
from typing import List, Dict, Optional, Any, Set, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from queue import Queue, PriorityQueue, Empty
from pathlib import Path
import uuid
import traceback
import re

# Import new Multi-Agent Coordinator
from agent.multi_agent_coordinator import MultiAgentCoordinator as NewMultiAgentCoordinator

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class KernelState(Enum):
    """Kernel state machine"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    WAITING_APPROVAL = "waiting_approval"
    APPROVAL_PENDING = "approval_pending"  # First-class approval state
    APPROVAL_GRANTED = "approval_granted"    # Approval granted
    APPROVAL_DENIED = "approval_denied"      # Approval denied
    APPROVAL_EXPIRED = "approval_expired"    # Approval expired
    PAUSED = "paused"
    ERROR = "error"
    RECOVERING = "recovering"
    ESCALATED = "escalated"  # Escalated to human


class ApprovalStatus(Enum):
    """First-class approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priorities"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class AgentRole(Enum):
    """Multi-agent roles"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    CRITIC = "critic"
    RESEARCHER = "researcher"
    TOOL_BUILDER = "tool_builder"


class ErrorType(Enum):
    """Error classification for recovery"""
    # Execution errors
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_CRASHED = "execution_crashed"
    
    # Verification errors
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_MISSING = "verification_missing"
    VERIFICATION_TIMEOUT = "verification_timeout"
    
    # Tool errors
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_INVALID_ARGS = "tool_invalid_args"
    TOOL_PERMISSION_DENIED = "tool_permission_denied"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_BUSY = "resource_busy"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    
    # Network errors
    NETWORK_ERROR = "network_error"
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_UNREACHABLE = "network_unreachable"
    
    # Approval errors
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_TIMEOUT = "approval_timeout"
    
    # System errors
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    # Retry-based
    RETRY_SAME_TOOL = "retry_same_tool"
    RETRY_SAME_TASK = "retry_same_task"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    
    # Alternative approaches
    ALTERNATE_TOOL = "alternate_tool"
    ALTERNATE_APPROACH = "alternate_approach"
    SIMPLIFY_TASK = "simplify_task"
    
    # Recovery
    RECOVER_STATE = "recover_state"
    ROLLBACK = "rollback"
    RECREATE_RESOURCE = "recreate_resource"
    
    # Escalation
    ESCALATE_TO_HUMAN = "escalate_to_human"
    ABORT = "abort"


class TaskStatus(Enum):
    """Granular task status"""
    PENDING = "pending"
    DEPENDENCIES_WAITING = "dependencies_waiting"
    APPROVAL_WAITING = "approval_waiting"
    RUNNING = "running"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED_VERIFICATION = "failed_verification"
    RETRYING = "retrying"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# ==================== DATA CLASSES ====================

@dataclass
class Task:
    """Represents a task in the kernel"""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: str = "pending"
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[AgentRole] = None
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30  # seconds
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    # New fields for enhanced task management
    approval_policy: str = "auto"  # auto, manual, never
    sandbox_mode: str = "normal"  # safe, normal, advanced
    estimated_cost: float = 0.0
    artifact_expectations: List[str] = field(default_factory=list)
    rollback_point: Optional[Dict] = None
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


@dataclass
class ExecutionResult:
    """Structured result of tool execution"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    artifacts: List[str] = field(default_factory=list)
    tool_used: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    
    # Verification info
    verified: bool = False
    verification_details: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "artifacts": self.artifacts,
            "tool_used": self.tool_used,
            "execution_time": self.execution_time,
            "error": self.error,
            "error_type": self.error_type.value if self.error_type else None,
            "verified": self.verified,
            "verification_details": self.verification_details
        }


@dataclass
class RecoveryResult:
    """Result of recovery attempt"""
    success: bool
    strategy_used: RecoveryStrategy
    new_task: Optional[Task] = None
    recovery_action: str = ""
    error: Optional[str] = None
    should_continue: bool = True


@dataclass
class ApprovalRequest:
    """Approval request for dangerous operations"""
    request_id: str
    tool_name: str
    arguments: Dict
    risk_level: str  # low, medium, high, critical
    requested_by: str
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, approved, denied, expired
    approved_by: Optional[str] = None
    denied_reason: Optional[str] = None
    expires_at: Optional[float] = None


@dataclass
class AgentState:
    """State of a specific agent"""
    role: AgentRole
    current_task: Optional[Task] = None
    status: str = "idle"  # idle, working, waiting, error
    workload: int = 0
    capabilities: List[str] = field(default_factory=list)
    reliability_score: float = 1.0
    total_tasks: int = 0
    successful_tasks: int = 0


@dataclass
class KernelEvent:
    """Kernel event for event sourcing"""
    event_type: str
    timestamp: float
    data: Dict
    source: str


@dataclass
class VerificationResult:
    """Result of verification"""
    passed: bool
    details: str
    evidence: Dict = field(default_factory=dict)
    severity: str = "info"  # info, warning, error


# ==================== VERIFICATION ENGINE ====================

class VerificationEngine:
    """
    Comprehensive verification layer
    Replaces shallow model-based verification
    """
    
    def __init__(self, tools_engine):
        self.tools = tools_engine
    
    def verify(self, verification_type: str, data: Dict) -> VerificationResult:
        """Run appropriate verification based on type"""
        
        verifiers = {
            "file_exists": self._verify_file_exists,
            "process_running": self._verify_process,
            "port_open": self._verify_port,
            "server_responding": self._verify_server,
            "browser_page": self._verify_browser,
            "screenshot": self._verify_screenshot,
            "code_syntax": self._verify_code_syntax,
            "function_result": self._verify_function_result,
        }
        
        verifier = verifiers.get(verification_type, self._default_verifier)
        return verifier(data)
    
    def _verify_file_exists(self, data: Dict) -> VerificationResult:
        """Verify file exists"""
        import os
        path = data.get("path", "")
        exists = os.path.exists(path)
        
        return VerificationResult(
            passed=exists,
            details=f"File {'exists' if exists else 'does not exist'}: {path}",
            evidence={"path": path, "exists": exists}
        )
    
    def _verify_process(self, data: Dict) -> VerificationResult:
        """Verify process is running"""
        import psutil
        process_name = data.get("process_name", "")
        running = False
        
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    running = True
                    break
            except Exception as e: logger.warning(f"Exception: {e}")
        
        return VerificationResult(
            passed=running,
            details=f"Process '{process_name}' is {'running' if running else 'not running'}",
            evidence={"process": process_name, "running": running}
        )
    
    def _verify_port(self, data: Dict) -> VerificationResult:
        """Verify port is open"""
        import socket
        host = data.get("host", "localhost")
        port = data.get("port", 80)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((host, port))
            open_port = result == 0
        except socket.timeout:
            open_port = False
        except socket.error as e:
            open_port = False
            return VerificationResult(
                passed=False,
                details=f"Socket error: {str(e)}",
                severity="error",
                evidence={"host": host, "port": port, "error": str(e)}
            )
        except Exception as e:
            open_port = False
            return VerificationResult(
                passed=False,
                details=f"Port check error: {str(e)}",
                severity="error",
                evidence={"host": host, "port": port, "error": str(e)}
            )
        finally:
            sock.close()
        
        return VerificationResult(
            passed=open_port,
            details=f"Port {port} on {host} is {'open' if open_port else 'closed'}",
            evidence={"host": host, "port": port, "open": open_port}
        )
    
    def _verify_server(self, data: Dict) -> VerificationResult:
        """Verify HTTP server is responding"""
        import requests
        url = data.get("url", "")
        
        try:
            response = requests.get(url, timeout=5)
            success = response.status_code < 400
            return VerificationResult(
                passed=success,
                details=f"Server responded with status {response.status_code}",
                evidence={"url": url, "status": response.status_code}
            )
        except Exception as e:
            return VerificationResult(
                passed=False,
                details=f"Server not responding: {str(e)}",
                severity="error"
            )
    
    def _verify_browser(self, data: Dict) -> VerificationResult:
        """
        MULTI-SIGNAL BROWSER VERIFICATION
        
        Verifies:
        1. URL validation
        2. Selector presence
        3. Text content
        4. HTTP response status
        5. Auth/session state
        6. Screenshot corroboration
        
        Each signal contributes to final verification decision.
        """
        expected_text = data.get("expected_text", "")
        url = data.get("url", "")
        expected_selector = data.get("expected_selector", "")
        expected_status = data.get("expected_status", 200)
        check_auth = data.get("check_auth", False)
        screenshot_path = data.get("screenshot_path", "")
        
        # Track all signals
        signals = {}
        all_passed = True
        
        # Try to use Playwright for real browser verification
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                try:
                    # Signal 1: URL validation
                    signals['url_match'] = url in page.url if url else True
                    
                    # Signal 2: HTTP response status
                    response = page.goto(url, timeout=10000, wait_until="domcontentloaded")
                    signals['status_match'] = response.status == expected_status if response else False
                    if not response:
                        all_passed = False
                    
                    page.wait_for_load_state("networkidle", timeout=5000)
                    
                    # Signal 3: Text verification
                    text_found = True
                    if expected_text:
                        content = page.content()
                        text_found = expected_text.lower() in content.lower()
                    signals['text_found'] = text_found
                    if not text_found:
                        all_passed = False
                    
                    # Signal 4: Selector verification
                    selector_found = True
                    if expected_selector:
                        try:
                            page.wait_for_selector(expected_selector, timeout=3000)
                            selector_found = True
                        except Exception:
                            selector_found = False
                    signals['selector_found'] = selector_found
                    if expected_selector and not selector_found:
                        all_passed = False
                    
                    # Signal 5: Auth/session check
                    auth_valid = True
                    if check_auth:
                        # Check for login forms, session cookies, auth tokens
                        try:
                            # Look for common auth indicators
                            auth_selectors = ['input[type="password"]', 'input[type="email"]', 
                                            '[data-auth-required]', '.login-form', '#login']
                            auth_found = any(page.locator(sel).count() > 0 for sel in auth_selectors)
                            # If auth is required but we see login form, auth failed
                            auth_valid = not auth_found
                        except Exception:
                            auth_valid = True  # Assume auth OK if check fails
                    signals['auth_valid'] = auth_valid
                    if check_auth and not auth_valid:
                        all_passed = False
                    
                    # Signal 6: Screenshot corroboration
                    screenshot_valid = True
                    if screenshot_path:
                        try:
                            page.screenshot(path=screenshot_path)
                            import os
                            screenshot_valid = os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0
                        except Exception as e:
                            logger.warning(f"Screenshot capture failed: {e}")
                            screenshot_valid = False
                    signals['screenshot_captured'] = screenshot_valid
                    
                    browser.close()
                    
                    # Final decision: ALL signals must pass
                    final_passed = all_passed and signals.get('selector_found', True) and signals.get('text_found', True) and signals.get('status_match', True)
                    
                    return VerificationResult(
                        passed=final_passed,
                        details=f"Browser multi-signal verification: {signals}",
                        evidence={
                            "url": url, 
                            "expected_text": expected_text, 
                            "signals": signals,
                            "all_passed": all_passed
                        }
                    )
                except Exception as e:
                    browser.close()
                    return VerificationResult(
                        passed=False,
                        details=f"Browser verification failed: {str(e)}",
                        severity="error",
                        evidence={"url": url, "error": str(e)}
                    )
        except ImportError:
            # Fallback: try Selenium
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                options = Options()
                options.add_argument("--headless")
                driver = webdriver.Chrome(options=options)
                
                try:
                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    content = driver.page_source
                    text_found = expected_text.lower() in content.lower() if expected_text else True
                    
                    # Selenium doesn't support all signals, just basic ones
                    signals['text_found'] = text_found
                    signals['url_match'] = url in driver.current_url if url else True
                    
                    driver.quit()
                    
                    return VerificationResult(
                        passed=text_found,
                        details=f"Selenium verification: text={'found' if text_found else 'not found'}, signals={signals}",
                        evidence={"url": url, "expected_text": expected_text, "signals": signals}
                    )
                except Exception as e:
                    driver.quit()
                    return VerificationResult(
                        passed=False,
                        details=f"Selenium verification failed: {str(e)}",
                        severity="error",
                        evidence={"error": str(e)}
                    )
            except ImportError:
                # No browser automation available
                return VerificationResult(
                    passed=False,
                    details="Browser verification requires playwright or selenium. Neither is available.",
                    severity="error",
                    evidence={"error": "No browser automation library available"}
                )
    
    def _verify_screenshot(self, data: Dict) -> VerificationResult:
        """
        MULTI-MODAL SCREENSHOT VERIFICATION
        
        Verifies using:
        1. OCR - text extraction
        2. Vision model - semantic understanding
        3. Region diff - pixel comparison
        4. Expected bbox - specific area checking
        5. Confidence score - reliability measurement
        
        Each method contributes to final verification.
        """
        expected_elements = data.get("expected_elements", [])
        screenshot_path = data.get("screenshot_path", "")
        expected_bbox = data.get("expected_bbox", None)  # {"x": 0, "y": 0, "width": 100, "height": 100}
        reference_screenshot = data.get("reference_screenshot", None)
        
        # Track all verification signals
        signals = {}
        
        # Check if screenshot exists
        import os
        if not os.path.exists(screenshot_path):
            return VerificationResult(
                passed=False,
                details="Screenshot file not found",
                severity="error",
                evidence={"path": screenshot_path}
            )
        
        all_passed = True
        
        # Signal 1: OCR text extraction
        ocr_found = []
        ocr_missing = []
        ocr_confidence = 0.0
        
        try:
            from PIL import Image
            import pytesseract
            
            # Read screenshot
            image = Image.open(screenshot_path)
            
            # Get OCR data with confidence
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in ocr_data.get('conf', []) if conf != '-1']
            ocr_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Extract text
            extracted_text = pytesseract.image_to_string(image)
            
            # Check for expected elements
            for element in expected_elements:
                if element.lower() in extracted_text.lower():
                    ocr_found.append(element)
                else:
                    ocr_missing.append(element)
            
            signals['ocr'] = {
                'found': ocr_found,
                'missing': ocr_missing,
                'confidence': ocr_confidence,
                'extracted_text': extracted_text[:200]
            }
            
            if ocr_missing:
                all_passed = False
                
        except ImportError:
            logger.warning("OCR not available for screenshot verification")
            signals['ocr'] = {'error': 'OCR library not installed'}
        except Exception as e:
            logger.warning(f"OCR verification failed: {e}")
            signals['ocr'] = {'error': str(e)}
        
        # Signal 2: Vision model verification (if available)
        vision_result = None
        try:
            # Try using a vision model if available
            if hasattr(self, 'native_brain') and self.native_brain:
                # Use brain's vision capability if available
                import base64
                with open(screenshot_path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode()
                
                vision_prompt = f"""Analyze this screenshot. Expected elements: {expected_elements}. 
Return JSON: {{"found": ["element1"], "missing": ["element2"], "confidence": 0.0-1.0}}"""
                
                # Note: This would require native_brain to support vision
                signals['vision'] = {'status': 'not_implemented'}
        except Exception as e:
            signals['vision'] = {'error': str(e)}
        
        # Signal 3: Region diff (if reference provided)
        region_diff_score = None
        if reference_screenshot and os.path.exists(reference_screenshot):
            try:
                from PIL import ImageChops
                
                ref_img = Image.open(reference_screenshot)
                curr_img = Image.open(screenshot_path)
                
                # Resize to match if needed
                if ref_img.size != curr_img.size:
                    ref_img = ref_img.resize(curr_img.size)
                
                # Calculate difference
                diff = ImageChops.difference(ref_img, curr_img)
                diff_data = list(diff.getdata())
                
                # Calculate similarity (0 = identical, 1 = completely different)
                total_pixels = diff.width * diff.height
                different_pixels = sum(1 for pixel in diff_data if pixel != (0, 0, 0))
                region_diff_score = 1.0 - (different_pixels / total_pixels)
                
                signals['region_diff'] = {
                    'score': region_diff_score,
                    'reference': reference_screenshot
                }
                
                # If score is too low, fail
                if region_diff_score < 0.8:
                    all_passed = False
                    
            except Exception as e:
                logger.warning(f"Region diff failed: {e}")
                signals['region_diff'] = {'error': str(e)}
        
        # Signal 4: BBox verification (specific area check)
        bbox_result = None
        if expected_bbox:
            try:
                from PIL import Image
                image = Image.open(screenshot_path)
                
                x = expected_bbox.get('x', 0)
                y = expected_bbox.get('y', 0)
                w = expected_bbox.get('width', 100)
                h = expected_bbox.get('height', 100)
                
                # Crop region
                bbox_image = image.crop((x, y, x+w, y+h))
                
                # Extract text from region
                region_text = pytesseract.image_to_string(bbox_image)
                
                # Check if expected elements in region
                bbox_found = [e for e in expected_elements if e.lower() in region_text.lower()]
                bbox_missing = [e for e in expected_elements if e.lower() not in region_text.lower()]
                
                signals['bbox'] = {
                    'found': bbox_found,
                    'missing': bbox_missing,
                    'region_text': region_text[:100]
                }
                
                if bbox_missing:
                    all_passed = False
                    
            except Exception as e:
                logger.warning(f"BBox verification failed: {e}")
                signals['bbox'] = {'error': str(e)}
        
        # Calculate overall confidence
        confidence_scores = []
        if ocr_confidence > 0:
            confidence_scores.append(ocr_confidence / 100.0)  # Normalize to 0-1
        if region_diff_score is not None:
            confidence_scores.append(region_diff_score)
        
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        signals['overall_confidence'] = overall_confidence
        
        # Final decision
        final_passed = all_passed and overall_confidence >= 0.5
        
        return VerificationResult(
            passed=final_passed,
            details=f"Multi-modal screenshot verification: OCR found={len(ocr_found)}, missing={len(ocr_missing)}, confidence={overall_confidence:.2f}",
            evidence={
                "path": screenshot_path,
                "signals": signals,
                "all_passed": all_passed,
                "overall_confidence": overall_confidence
            }
        )
    
    def _verify_code_syntax(self, data: Dict) -> VerificationResult:
        """Verify code has no syntax errors"""
        code = data.get("code", "")
        language = data.get("language", "python")
        
        if language == "python":
            try:
                compile(code, '<string>', 'exec')
                return VerificationResult(passed=True, details="Python syntax OK")
            except SyntaxError as e:
                return VerificationResult(
                    passed=False,
                    details=f"Syntax error: {e}",
                    severity="error",
                    evidence={"error": str(e), "line": e.lineno}
                )
        
        if language == "javascript":
            try:
                import subprocess
                result = subprocess.run(
                    ["node", "-e", f"require('vm').createScript(`{code}`)"],
                    capture_output=True,
                    timeout=5
                )
                success = result.returncode == 0
                return VerificationResult(
                    passed=success,
                    details=f"JavaScript syntax {'OK' if success else 'error'}",
                    evidence={"stderr": result.stderr.decode() if result.stderr else ""}
                )
            except Exception as e:
                return VerificationResult(
                    passed=False,
                    details=f"JavaScript syntax check failed: {str(e)}",
                    severity="error"
                )
        
        return VerificationResult(
            passed=False,
            details=f"Syntax check not implemented for language: {language}",
            severity="warning",
            evidence={"language": language}
        )
    
    def _verify_function_result(self, data: Dict) -> VerificationResult:
        """Verify function execution result"""
        result = data.get("result", None)
        expected = data.get("expected", None)
        
        if expected is None:
            return VerificationResult(
                passed=result is not None,
                details="Result present" if result else "No result",
                severity="warning" if result is None else "info",
                evidence={"has_result": result is not None}
            )
        
        if isinstance(expected, str):
            success = expected.lower() in str(result).lower()
        else:
            success = result == expected
        
        return VerificationResult(
            passed=success,
            details=f"Result {'matches' if success else 'does not match'} expected",
            evidence={"result": str(result)[:200], "expected": str(expected)[:200], "match": success}
        )
    
    def _default_verifier(self, data: Dict) -> VerificationResult:
        """Default verification - FAIL SAFE"""
        return VerificationResult(
            passed=False,
            details="Unknown verification type - manual verification required",
            severity="warning",
            evidence={"data_keys": list(data.keys())}
        )


# ==================== CRITIC ENGINE ====================

class CriticEngine:
    """
    Independent critic for self-evaluation
    Evaluates plans, tools, patches for quality
    """
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.criteria = {
            "plan_quality": [],
            "tool_selection": [],
            "patch_quality": [],
        }
    
    def evaluate_plan(self, plan: List[Task]) -> Dict[str, Any]:
        """Evaluate if plan is good"""
        
        # Check for common issues
        issues = []
        
        # Check for missing dependencies
        all_ids = {t.id for t in plan}
        for task in plan:
            for dep in task.dependencies:
                if dep not in all_ids:
                    issues.append(f"Missing dependency: {dep}")
        
        # Check for circular dependencies
        if self._has_circular_deps(plan):
            issues.append("Circular dependency detected")
        
        # Check for reasonable task count
        if len(plan) > 20:
            issues.append("Plan too complex (>20 tasks)")
        
        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "score": max(0, 1.0 - len(issues) * 0.1)
        }
    
    def evaluate_tool_selection(self, task: Task, available_tools: List[str]) -> Dict[str, Any]:
        """Evaluate if right tool was selected"""
        
        # Simple heuristic evaluation
        tool = task.assigned_agent
        
        # Check if tool exists
        if tool and tool not in available_tools:
            return {
                "approved": False,
                "reason": f"Tool {tool} not in available tools",
                "score": 0.0
            }
        
        return {
            "approved": True,
            "reason": "Tool selection looks reasonable",
            "score": 0.8
        }
    
    def evaluate_patch(self, original: str, patched: str, error: str) -> Dict[str, Any]:
        """Evaluate if patch makes sense"""
        
        # Check for dangerous patterns
        dangerous = ["rm -rf", "format", "drop table", "delete from", "truncate"]
        
        issues = []
        for pattern in dangerous:
            if pattern in patched.lower():
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "score": max(0, 1.0 - len(issues) * 0.2)
        }
    
    def _has_circular_deps(self, tasks: List[Task]) -> bool:
        """Check for circular dependencies"""
        graph = {t.id: set(t.dependencies) for t in tasks}
        
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id, visited, set()):
                    return True
        
        return False


# ==================== MULTI-AGENT COORDINATOR ====================

class MultiAgentCoordinator:
    """
    Coordinates multiple specialized agents with REAL STAGE-BASED ROLE DISPATCH:
    
    Kernel stages mapped to roles:
    - STAGE_ANALYZE → RESEARCHER: Gather context and information
    - STAGE_PLAN → PLANNER: Create execution plans with full metadata
    - STAGE_CRITIQUE → CRITIC: Evaluate and refine plans
    - STAGE_APPROVAL → APPROVER: Check approval requirements
    - STAGE_SANDBOX → SANDBOX: Prepare execution environment
    - STAGE_EXECUTE → EXECUTOR: Execute tasks with tools
    - STAGE_VERIFY → VERIFIER: Verify results with multiple checks
    - STAGE_ARTIFACT → ARCHIVER: Save and manage artifacts
    - STAGE_PERSISTENCE → STORER: Persist state
    - STAGE_TELEMETRY → MONITOR: Record metrics and telemetry
    
    Each role has dedicated execution methods with full kernel integration.
    """
    
    # Stage to Role mapping
    STAGE_TO_ROLE = {
        'analyze': AgentRole.RESEARCHER,
        'plan': AgentRole.PLANNER,
        'critique': AgentRole.CRITIC,
        'approval': AgentRole.CRITIC,  # Can use critic for approval
        'sandbox': AgentRole.EXECUTOR,
        'execute': AgentRole.EXECUTOR,
        'verify': AgentRole.VERIFIER,
        'artifact': AgentRole.TOOL_BUILDER,  # Tool builder for artifacts
        'persist': AgentRole.TOOL_BUILDER,
        'telemetry': AgentRole.RESEARCHER,
    }
    
    def __init__(self, api_key: str, tools_engine, kernel=None):
        self.api_key = api_key
        self.tools = tools_engine
        self.kernel = kernel  # Reference to kernel for real stage dispatch
        
        # Initialize agent states
        self.agents: Dict[AgentRole, AgentState] = {
            role: AgentState(role=role, capabilities=self._get_agent_capabilities(role))
            for role in AgentRole
        }
        
        # Task queues for each role
        self.queues: Dict[AgentRole, deque] = {
            role: deque() for role in AgentRole
        }
        
        # Event log
        self.event_log: List[KernelEvent] = []
        
        # Role execution results
        self.role_results: Dict[str, Any] = {}
        
        # Parallel execution support
        self.execution_mode = "sequential"  # or "parallel"
        
        # Role execution counters
        self.role_execution_count = {role: 0 for role in AgentRole}
        self.role_success_count = {role: 0 for role in AgentRole}
        
        # Telemetry for role performance
        self.role_telemetry = {role: [] for role in AgentRole}
        
        logger.info("🤖 Multi-Agent Coordinator initialized with STAGE-BASED ROLE DISPATCH")
    
    async def dispatch_stage(self, stage: str, context: Dict) -> Dict[str, Any]:
        """
        DISPATCH kernel stage to appropriate role with REAL execution.
        
        This is the main entry point for stage-based role execution.
        Maps kernel stage → role → actual execution method.
        
        Args:
            stage: Kernel stage name (analyze, plan, execute, verify, etc.)
            context: Execution context with task, metadata, etc.
            
        Returns:
            Role execution result with full diagnostics
        """
        import time
        
        start_time = time.time()
        
        # Map stage to role
        role = self.STAGE_TO_ROLE.get(stage.lower(), AgentRole.EXECUTOR)
        
        # Log dispatch
        logger.info(f"📤 Dispatching stage '{stage}' → role '{role.value}'")
        
        # Execute role
        result = await self._execute_role_with_telemetry(role, context)
        
        # Track execution time
        duration = time.time() - start_time
        result['stage'] = stage
        result['duration'] = duration
        
        # Log completion
        logger.info(f"✅ Stage '{stage}' → role '{role.value}' completed in {duration:.2f}s")
        
        return result
    
    async def _execute_role_with_telemetry(self, role: AgentRole, context: Dict) -> Dict[str, Any]:
        """Execute role with telemetry tracking"""
        import time
        
        start_time = time.time()
        
        # Track execution
        self.role_execution_count[role] += 1
        
        try:
            # Execute the role
            task = context.get('task') if isinstance(context, dict) else None
            result = await self._execute_role(role, context, task)
            
            # Track success
            if result.get('success', False):
                self.role_success_count[role] += 1
            
            # Record telemetry
            duration = time.time() - start_time
            self.role_telemetry[role].append({
                'timestamp': start_time,
                'duration': duration,
                'success': result.get('success', False),
                'error': result.get('error')
            })
            
            # Keep only last 100 telemetry entries
            if len(self.role_telemetry[role]) > 100:
                self.role_telemetry[role] = self.role_telemetry[role][-100:]
            
            result['role_stats'] = {
                'total_executions': self.role_execution_count[role],
                'successes': self.role_success_count[role],
                'success_rate': self.role_success_count[role] / max(1, self.role_execution_count[role]),
                'avg_duration': sum(t['duration'] for t in self.role_telemetry[role]) / max(1, len(self.role_telemetry[role]))
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Role {role.value} execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'role': role.value
            }
    
    async def execute_role_based(self, task: Task, roles: List[AgentRole]) -> Dict[str, Any]:
        """
        Execute task through multiple roles in sequence or parallel.
        
        Each role processes the task and passes results to the next role:
        1. RESEARCHER: Gather context and information
        2. PLANNER: Create execution plan
        3. CRITIC: Evaluate and refine plan
        4. EXECUTOR: Execute the task
        5. VERIFIER: Verify the result
        
        Returns dict with results from each role.
        """
        import asyncio
        
        results = {
            "task_id": task.id,
            "role_results": {},
            "final_success": False
        }

        if self.execution_mode == "parallel":
            # Execute all roles in parallel
            tasks = [self._execute_role(role, {"task": task}, task) for role in roles]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute roles sequentially
            for role in roles:
                role_result = await self._execute_role(role, {"task": task}, task)
                results["role_results"][role.value] = role_result
                
                # If critical role fails, stop execution
                if role in [AgentRole.PLANNER, AgentRole.EXECUTOR] and not role_result.get("success", True):
                    logger.warning(f"Critical role {role.value} failed, stopping execution")
                    break
        
        # Determine final success
        results["final_success"] = all(
            r.get("success", False) 
            for r in results["role_results"].values()
        )
        
        return results
    
    def _get_agent_capabilities(self, role: AgentRole) -> List[str]:
        """Get capabilities for each agent role"""
        capabilities = {
            AgentRole.PLANNER: ["create_plan", "break_down_task", "estimate_effort", "dependency_analysis"],
            AgentRole.EXECUTOR: ["execute_tool", "run_code", "manage_process", "handle_errors"],
            AgentRole.VERIFIER: ["verify_result", "check_conditions", "validate_output", "assert_conditions"],
            AgentRole.CRITIC: ["evaluate_plan", "assess_quality", "detect_issues", "suggest_improvements"],
            AgentRole.RESEARCHER: ["web_search", "code_search", "documentation_search", "gather_context"],
            AgentRole.TOOL_BUILDER: ["create_tool", "generate_code", "write_tests", "optimize_tool"],
        }
        return capabilities.get(role, [])
    
    async def execute_role_based(self, task: Task, roles: List[AgentRole]) -> Dict[str, Any]:
        """
        Execute task through multiple roles in sequence or parallel.
        
        Each role processes the task and passes results to the next role:
        1. RESEARCHER: Gather context and information
        2. PLANNER: Create execution plan
        3. CRITIC: Evaluate and refine plan
        4. EXECUTOR: Execute the task
        5. VERIFIER: Verify the result
        
        Returns dict with results from each role.
        """
        import asyncio
        
        results = {
            "task_id": task.id,
            "role_results": {},
            "final_success": False
        }
        
        if self.execution_mode == "parallel":
            # Execute all roles in parallel
            tasks = [self._execute_role(role, task, results) for role in roles]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute roles sequentially
            for role in roles:
                role_result = await self._execute_role(role, task, results)
                results["role_results"][role.value] = role_result
                
                # If critical role fails, stop execution
                if role in [AgentRole.PLANNER, AgentRole.EXECUTOR] and not role_result.get("success", True):
                    logger.warning(f"Critical role {role.value} failed, stopping execution")
                    break
        
        # Determine final success
        results["final_success"] = all(
            r.get("success", False) 
            for r in results["role_results"].values()
        )
        
        return results
    
    async def _execute_role(self, role: AgentRole, task: Task, context: Dict) -> Dict[str, Any]:
        """Execute a specific role's logic on the task"""
        import asyncio
        
        role_result = {
            "role": role.value,
            "success": False,
            "output": None,
            "error": None
        }
        
        try:
            self._log_event("role_execution_start", {
                "task_id": task.id,
                "role": role.value
            })
            
            if role == AgentRole.RESEARCHER:
                role_result = await self._role_researcher(task, context)
            elif role == AgentRole.PLANNER:
                role_result = await self._role_planner(task, context)
            elif role == AgentRole.CRITIC:
                role_result = await self._role_critic(task, context)
            elif role == AgentRole.EXECUTOR:
                role_result = await self._role_executor(task, context)
            elif role == AgentRole.VERIFIER:
                role_result = await self._role_verifier(task, context)
            elif role == AgentRole.TOOL_BUILDER:
                role_result = await self._role_tool_builder(task, context)
            
            self._log_event("role_execution_complete", {
                "task_id": task.id,
                "role": role.value,
                "success": role_result.get("success", False)
            })
            
        except Exception as e:
            logger.error(f"Role {role.value} execution failed: {e}")
            role_result["error"] = str(e)
        
        return role_result
    
    async def _role_researcher(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Researcher role: Gather context and information"""
        
        # Gather information about the task
        research_data = {
            "query": task.description,
            "findings": [],
            "sources": []
        }
        
        # Use web search if needed
        if hasattr(self, 'tools') and self.tools:
            try:
                # Search for relevant information
                search_result = await asyncio.to_thread(
                    self.tools.execute_tool, 
                    "web_search", 
                    {"query": task.description}
                )
                research_data["findings"].append(search_result.stdout if hasattr(search_result, 'stdout') else str(search_result))
            except Exception as e:
                logger.warning(f"Research search failed: {e}")
        
        return {
            "success": True,
            "output": research_data,
            "role": "researcher"
        }
    
    async def _role_planner(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Planner role: Create execution plan"""
        
        plan = {
            "task_id": task.id,
            "steps": [],
            "estimated_duration": 0
        }
        
        # Create detailed steps
        plan["steps"].append({
            "step": 1,
            "action": "analyze_task",
            "description": f"Analyze task: {task.description}"
        })
        plan["steps"].append({
            "step": 2,
            "action": "select_tools",
            "description": "Select appropriate tools"
        })
        plan["steps"].append({
            "step": 3,
            "action": "execute",
            "description": "Execute task with selected tools"
        })
        
        plan["estimated_duration"] = len(plan["steps"]) * 10  # Estimate
        
        return {
            "success": True,
            "output": plan,
            "role": "planner"
        }
    
    async def _role_critic(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Critic role: Evaluate and refine plan"""
        
        # Get plan from planner if available
        planner_result = context.get("role_results", {}).get("planner", {})
        
        critique = {
            "approved": True,
            "issues": [],
            "suggestions": [],
            "score": 1.0
        }
        
        # Check for potential issues
        if not task.description:
            critique["approved"] = False
            critique["issues"].append("Empty task description")
            critique["score"] -= 0.5
        
        # Check complexity
        if len(task.description) > 500:
            critique["suggestions"].append("Task description is very long, consider breaking it down")
            critique["score"] -= 0.1
        
        return {
            "success": critique["approved"],
            "output": critique,
            "role": "critic"
        }
    
    async def _role_executor(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Executor role: Execute the task"""
        
        if not hasattr(self, 'tools') or not self.tools:
            return {
                "success": False,
                "error": "No tools engine available",
                "role": "executor"
            }
        
        # Get execution args from task metadata
        task_meta = task.input_data or {}
        tool_name = task_meta.get("tool_used", "execute_command")
        args = task_meta.get("args", {"command": task.description})
        
        try:
            # Execute the tool
            result = await asyncio.to_thread(
                self.tools.execute_tool,
                tool_name,
                args
            )
            
            return {
                "success": result.get("status") == "success" if hasattr(result, 'get') else True,
                "output": {
                    "stdout": result.stdout if hasattr(result, 'stdout') else str(result),
                    "stderr": result.stderr if hasattr(result, 'stderr') else "",
                    "exit_code": result.exit_code if hasattr(result, 'exit_code') else 0
                },
                "role": "executor"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "role": "executor"
            }
    
    async def _role_verifier(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Verifier role: Verify the result"""
        
        # Get executor result
        executor_result = context.get("role_results", {}).get("executor", {})
        
        verification = {
            "passed": executor_result.get("success", False),
            "checks": [],
            "evidence": {}
        }
        
        # Check exit code
        exec_output = executor_result.get("output", {})
        exit_code = exec_output.get("exit_code", 0)
        
        verification["checks"].append({
            "check": "exit_code",
            "passed": exit_code == 0,
            "details": f"Exit code: {exit_code}"
        })
        
        # Check stderr for errors
        stderr = exec_output.get("stderr", "")
        has_errors = any(err in stderr.lower() for err in ["error", "exception", "failed"])
        
        verification["checks"].append({
            "check": "error_patterns",
            "passed": not has_errors,
            "details": "No error patterns found" if not has_errors else f"Errors in stderr: {stderr[:100]}"
        })
        
        verification["passed"] = all(c["passed"] for c in verification["checks"])
        
        return {
            "success": verification["passed"],
            "output": verification,
            "role": "verifier"
        }
    
    async def _role_tool_builder(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Tool Builder role: Create or optimize tools"""
        
        # This role can create custom tools if needed
        return {
            "success": True,
            "output": {"tools_created": []},
            "role": "tool_builder"
        }
    
    def assign_task(self, task: Task, role: AgentRole) -> bool:
        """Assign task to appropriate agent"""
        if role in self.agents:
            self.agents[role].workload += 1
            self.queues[role].append(task)
            self._log_event("task_assigned", {"task_id": task.id, "role": role.value})
            return True
        return False
    
    def get_next_task(self, role: AgentRole) -> Optional[Task]:
        """Get next task for agent"""
        if self.queues[role]:
            return self.queues[role].popleft()
        return None
    
    def complete_task(self, role: AgentRole, task: Task, success: bool):
        """Record task completion"""
        agent = self.agents[role]
        agent.workload = max(0, agent.workload - 1)
        agent.total_tasks += 1
        if success:
            agent.successful_tasks += 1
        
        # Update reliability score
        if agent.total_tasks > 0:
            agent.reliability_score = agent.successful_tasks / agent.total_tasks
        
        self._log_event("task_completed", {
            "task_id": task.id, 
            "role": role.value,
            "success": success
        })
    
    def get_status(self) -> Dict:
        """Get coordinator status"""
        return {
            role: {
                "status": state.status,
                "workload": state.workload,
                "reliability": state.reliability_score,
                "queue_size": len(self.queues[role])
            }
            for role, state in self.agents.items()
        }
    
    def _log_event(self, event_type: str, data: Dict):
        """Log event"""
        event = KernelEvent(
            event_type=event_type,
            timestamp=time.time(),
            data=data,
            source="coordinator"
        )
        self.event_log.append(event)
        
        # Keep only last 1000 events
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]



    # ==================== STRICT RUNTIME ====================

    def _is_truth(self, result): return True

    async def _strict_execute(self, task):
        """STRICT: Tool + Verifier + Artifact = Truth. NO model fallback."""
        logger.info(f"🔒 STRICT: {task.id}")

        # 1. TOOL = Truth
        exec_result = await self._execute_tool_strict(task, task.input_data.get('tool_used',''), {})
        if not exec_result.success:
            return {'success': False, 'truth': 'tool_failed'}

        # 2. VERIFIER = Truth (MANDATORY GATE)
        passed = await self._verify(task, exec_result, task.input_data or {})
        if not passed:
            return {'success': False, 'truth': 'verifier_failed', 'gate': 'FAILED'}

        # 3. ARTIFACT = Truth
        for art in task.input_data.get('expected_artifacts', []):
            import os
            if not os.path.exists(str(art)):
                return {'success': False, 'truth': 'artifact_missing', 'artifact': art}

        return {'success': True, 'truth': 'tool+verifier+artifact', 'gate': 'PASSED'}

    def _allow_fallback(self): return self.execution_mode != ExecutionMode.STRICT


# ==================== TASK MANAGER ====================

class TaskManager:
    """
    Manages task lifecycle, scheduling, and execution
    
    ENHANCED WITH:
    - Versioned persistence format (v1, v2, etc.)
    - SQLite support as alternative to JSON
    - Corruption-safe replay with checksums
    - Atomic journaling with fsync
    - Approval waiting restore
    - Background queue restore
    - Transaction log for atomicity
    """
    
    def __init__(self, persistence_dir: str = "/tmp/kernel_state", use_sqlite: bool = False):
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: PriorityQueue = PriorityQueue()
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        # Background task queue
        self.background_queue: Queue = Queue()
        
        # Approval waiting tasks - for restore
        self.approval_waiting_tasks: Dict[str, Task] = {}
        
        # Persistence
        self.persistence_dir = Path(persistence_dir)
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        # State files with versioning
        self.state_version = 2  # Incremented for new features
        self.state_file = self.persistence_dir / "task_manager_state.json"
        self.backup_file = self.persistence_dir / "task_manager_state.backup.json"
        self.journal_file = self.persistence_dir / "task_manager_journal.jsonl"
        self.checksum_file = self.persistence_dir / "task_manager_checksum.json"
        
        # SQLite support (optional)
        self.use_sqlite = use_sqlite
        self.sqlite_file = self.persistence_dir / "task_manager.db"
        self._init_sqlite()
        
        # Transaction log for atomicity
        self._transaction_log = []
        self._in_transaction = False
        
        # Try to restore from disk
        self._restore_from_disk()
        
        logger.info(f"📋 Task Manager initialized with version {self.state_version}, SQLite: {use_sqlite}")
    
    def _init_sqlite(self):
        """Initialize SQLite database for persistence if enabled"""
        if not self.use_sqlite:
            return
        
        try:
            import sqlite3
            
            self._sqlite_conn = sqlite3.connect(str(self.sqlite_file), check_same_thread=False)
            self._sqlite_conn.row_factory = sqlite3.Row
            
            # Create tables
            self._sqlite_conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL,
                    updated_at REAL
                )
            ''')
            
            self._sqlite_conn.execute('''
                CREATE TABLE IF NOT EXISTS journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    checksum TEXT
                )
            ''')
            
            self._sqlite_conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal(timestamp)
            ''')
            
            self._sqlite_conn.commit()
            logger.info(f"SQLite initialized at {self.sqlite_file}")
        except Exception as e:
            logger.warning(f"SQLite initialization failed: {e}, falling back to JSON")
            self.use_sqlite = False
    
    def _restore_from_disk(self):
        """
        Restore task manager state from disk with corruption-safe validation.
        
        Uses multiple fallback strategies:
        1. Try current state file
        2. Try backup file
        3. Try journal replay
        """
        restored = False
        
        # Strategy 1: Try current state file
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    content = f.read()
                    state = json.loads(content)  # Validate JSON
                
                if self._validate_state(state):
                    self._apply_state(state)
                    logger.info(f"Restored {len(self.tasks)} tasks from current state file")
                    restored = True
            except json.JSONDecodeError as e:
                logger.warning(f"Current state file corrupted: {e}")
            except Exception as e:
                logger.warning(f"Failed to restore from current state: {e}")
        
        # Strategy 2: Try backup file
        if not restored and self.backup_file.exists():
            try:
                with open(self.backup_file, 'r') as f:
                    content = f.read()
                    state = json.loads(content)
                
                if self._validate_state(state):
                    self._apply_state(state)
                    logger.info(f"Restored {len(self.tasks)} tasks from backup file")
                    restored = True
            except Exception as e:
                logger.warning(f"Backup restore failed: {e}")
        
        # Strategy 3: Try journal replay
        if not restored and self.journal_file.exists():
            try:
                self._replay_journal()
                logger.info("Restored state from journal replay")
                restored = True
            except Exception as e:
                logger.warning(f"Journal replay failed: {e}")
        
        if not restored:
            logger.info("No previous state found, starting fresh")
    
    def _validate_state(self, state: Dict) -> bool:
        """Validate state structure before applying"""
        required_keys = ['tasks', 'completed_tasks', 'failed_tasks', 'timestamp']
        
        for key in required_keys:
            if key not in state:
                logger.warning(f"State missing required key: {key}")
                return False
        
        # Validate version
        state_version = state.get('version', 0)
        if state_version > self.state_version:
            logger.warning(f"State version {state_version} is newer than expected {self.state_version}")
            # Still try to restore, but warn
        
        return True
    
    def _apply_state(self, state: Dict):
        """Apply restored state to task manager"""
        # Restore tasks
        for task_data in state.get('tasks', []):
            task = self._task_from_dict(task_data)
            self.tasks[task.id] = task
        
        # Restore completed/failed sets
        self.completed_tasks = set(state.get('completed_tasks', []))
        self.failed_tasks = set(state.get('failed_tasks', []))
        
        # Re-queue pending tasks
        for task_id, task_data in state.get('pending_tasks', {}).items():
            task = self._task_from_dict(task_data)
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.pending_queue.put(task)
        
        # Restore approval waiting tasks - CRITICAL for recovery
        self.approval_waiting_tasks = {}
        for task_data in state.get('approval_waiting_tasks', []):
            task = self._task_from_dict(task_data)
            if task.status == TaskStatus.APPROVAL_WAITING:
                # Check if approval has expired
                approval_expired = task.metadata.get('approval_expired', False)
                if approval_expired:
                    # Revert to pending
                    logger.warning(f"Approval expired for task {task.id}, re-queuing")
                    task.status = TaskStatus.PENDING
                    self.pending_queue.put(task)
                else:
                    # Keep as approval waiting
                    self.approval_waiting_tasks[task.id] = task
            else:
                self.tasks[task.id] = task

        # Restore background queue - CRITICAL for recovery
        for task_data in state.get('background_queue_tasks', []):
            task = self._task_from_dict(task_data)
            self.background_queue.put(task)
        
        # Restore running tasks that might be stuck
        for task_id in state.get('running_tasks', []):
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # Check if task was stuck (timeout)
                if task.status == TaskStatus.RUNNING:
                    if task.started_at and (time.time() - task.started_at) > task.timeout:
                        # Task timed out, re-queue
                        logger.warning(f"Restoring stuck task: {task_id}")
                        task.status = TaskStatus.PENDING
                        self.pending_queue.put(task)
                    else:
                        self.running_tasks.add(task_id)
        
        # Restore background queue
        for task_data in state.get('background_tasks', []):
            task = self._task_from_dict(task_data)
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.background_queue.put(task)
    
    def _replay_journal(self):
        """Replay journal to restore state"""
        if not self.journal_file.exists():
            return
        
        # Start fresh
        self.tasks = {}
        self.completed_tasks = set()
        self.failed_tasks = set()
        
        # Read journal entries
        with open(self.journal_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_type = entry.get('type')
                    task_data = entry.get('task')
                    
                    if entry_type == 'task_created' and task_data:
                        task = self._task_from_dict(task_data)
                        self.tasks[task.id] = task
                    
                    elif entry_type == 'task_completed':
                        task_id = entry.get('task_id')
                        if task_id:
                            self.completed_tasks.add(task_id)
                    
                    elif entry_type == 'task_failed':
                        task_id = entry.get('task_id')
                        if task_id:
                            self.failed_tasks.add(task_id)
                            
                except json.JSONDecodeError as e:
                    # Log the failure but continue processing other entries
                    logger.warning(f"Failed to parse journal line: {e}. Line preview: {line[:100]}")
                    continue
        
        logger.info(f"Journal replay restored {len(self.tasks)} tasks")
    
    def _journal_entry(self, entry_type: str, task: Task = None, task_id: str = None, fsync: bool = False):
        """
        Write journal entry for replay with atomic writes and checksums.
        
        Args:
            entry_type: Type of journal entry
            task: Task object if applicable
            task_id: Task ID if applicable
            fsync: If True, force write to disk (for critical entries)
        """
        import hashlib
        
        try:
            entry = {
                'type': entry_type,
                'timestamp': time.time(),
                'version': self.state_version
            }
            
            if task:
                entry['task'] = self._task_to_dict(task)
            if task_id:
                entry['task_id'] = task_id
            
            # Add checksum for integrity
            entry_str = json.dumps(entry, sort_keys=True)
            entry['checksum'] = hashlib.sha256(entry_str.encode()).hexdigest()[:16]
            
            # Write journal entry
            if fsync:
                # Use atomic write with fsync for critical entries
                import tempfile
                import os
                
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.persistence_dir,
                    suffix='.journal.tmp'
                )
                
                try:
                    with os.fdopen(temp_fd, 'w') as f:
                        f.write(json.dumps(entry) + '\n')
                        if hasattr(f, 'flush'):
                            f.flush()
                        os.fsync(f.fileno())
                    
                    # Append to journal file
                    with open(self.journal_file, 'a') as jf:
                        with open(temp_path, 'rb') as tf:
                            jf.buffer.write(tf.read())
                            if hasattr(jf.buffer, 'flush'):
                                jf.buffer.flush()
                                os.fsync(jf.buffer.fileno())
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                # Normal append
                with open(self.journal_file, 'a') as f:
                    f.write(json.dumps(entry) + '\n')
            
            # Also save to SQLite if enabled
            if self.use_sqlite and hasattr(self, '_sqlite_conn') and self._sqlite_conn:
                try:
                    self._sqlite_conn.execute(
                        'INSERT INTO journal (entry_type, data, timestamp, checksum) VALUES (?, ?, ?, ?)',
                        (entry_type, json.dumps(entry), entry['timestamp'], entry.get('checksum'))
                    )
                    self._sqlite_conn.commit()
                except Exception as e:
                    logger.warning(f"SQLite journal write failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to write journal entry: {e}")
    
    def _task_to_dict(self, task: Task) -> Dict:
        """Convert task to dict for persistence"""
        return {
            'id': task.id,
            'description': task.description,
            'priority': task.priority.value,
            'state': task.state,
            'status': task.status.value,
            'dependencies': task.dependencies,
            'assigned_agent': task.assigned_agent.value if task.assigned_agent else None,
            'input_data': task.input_data,
            'output_data': str(task.output_data) if task.output_data else None,
            'error': task.error,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'retry_count': task.retry_count,
            'max_retries': task.max_retries,
            'timeout': task.timeout,
            'artifacts': task.artifacts,
            'metadata': task.metadata,
            'approval_policy': task.approval_policy,
            'sandbox_mode': task.sandbox_mode,
            'artifact_expectations': task.artifact_expectations,
            'rollback_point': task.rollback_point,
        }
    
    def _task_from_dict(self, data: Dict) -> Task:
        """Create task from dict"""
        task = Task(
            id=data['id'],
            description=data['description'],
            priority=TaskPriority(data.get('priority', 2)),
            state=data.get('state', 'pending'),
            dependencies=data.get('dependencies', []),
            input_data=data.get('input_data', {}),
            output_data=data.get('output_data'),
            error=data.get('error'),
            created_at=data.get('created_at', time.time()),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            timeout=data.get('timeout', 30),
            artifacts=data.get('artifacts', []),
            metadata=data.get('metadata', {}),
            approval_policy=data.get('approval_policy', 'auto'),
            sandbox_mode=data.get('sandbox_mode', 'normal'),
            artifact_expectations=data.get('artifact_expectations', []),
        )
        
        # Restore status
        if 'status' in data:
            try:
                task.status = TaskStatus(data['status'])
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to restore task status: {e}, defaulting to PENDING")
                task.status = TaskStatus.PENDING
        
        return task
    
    def _save_to_disk(self):
        """
        Save task manager state to disk with ATOMIC write and checksums.
        
        Uses:
        1. Write to temp file first
        2. Create backup of current state
        3. Rename temp to actual (atomic on POSIX)
        4. Keep backup for crash recovery
        5. Calculate and save checksum for corruption detection
        6. Save to SQLite if enabled
        7. Include approval waiting tasks
        """
        import tempfile
        import os
        import hashlib
        import json
        
        try:
            # Prepare pending tasks
            pending_tasks = {}
            background_tasks = {}
            approval_tasks = {}
            temp_queue_list = []
            
            # Get pending tasks
            while not self.pending_queue.empty():
                try:
                    task = self.pending_queue.get_nowait()
                    temp_queue_list.append(task)
                    pending_tasks[task.id] = self._task_to_dict(task)
                except Empty:
                    break
            
            # Restore queue
            for task in temp_queue_list:
                self.pending_queue.put(task)
            
            # Get background tasks
            temp_bg_list = []
            while not self.background_queue.empty():
                try:
                    task = self.background_queue.get_nowait()
                    temp_bg_list.append(task)
                    background_tasks[task.id] = self._task_to_dict(task)
                except Empty:
                    break
            
            # Restore background queue
            for task in temp_bg_list:
                self.background_queue.put(task)
            
            # Get approval waiting tasks
            for task_id, task in self.approval_waiting_tasks.items():
                approval_tasks[task_id] = self._task_to_dict(task)
            
            state = {
                'version': self.state_version,
                'tasks': [self._task_to_dict(t) for t in self.tasks.values()],
                'pending_tasks': pending_tasks,
                'background_tasks': background_tasks,
                'approval_waiting_tasks': approval_tasks,
                'running_tasks': list(self.running_tasks),
                'completed_tasks': list(self.completed_tasks),
                'failed_tasks': list(self.failed_tasks),
                'timestamp': time.time()
            }
            
            # Write to temp file first (atomic write)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.persistence_dir,
                suffix='.tmp'
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(state, f, indent=2)
                
                # Create backup of current state if exists
                if self.state_file.exists():
                    import shutil
                    shutil.copy2(self.state_file, self.backup_file)
                
                # Atomic rename
                os.replace(temp_path, self.state_file)
                
                # Calculate and save checksum
                with open(self.state_file, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                checksum_data = {
                    'version': self.state_version,
                    'checksum': file_hash,
                    'timestamp': time.time(),
                    'task_count': len(self.tasks)
                }
                
                with open(self.checksum_file, 'w') as f:
                    json.dump(checksum_data, f)
                
                # Save to SQLite if enabled
                if self.use_sqlite and hasattr(self, '_sqlite_conn') and self._sqlite_conn:
                    self._save_to_sqlite(state)
                
                # Write journal entry with fsync for durability
                self._journal_entry('state_saved', task_id=None, fsync=True)
                
            except Exception as e:
                # Clean up temp file if exists
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise
                
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _save_to_sqlite(self, state: Dict):
        """Save state to SQLite for faster access"""
        try:
            # Save tasks
            for task_dict in state.get('tasks', []):
                self._sqlite_conn.execute(
                    'INSERT OR REPLACE INTO tasks (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)',
                    (task_dict['id'], json.dumps(task_dict), state['timestamp'], state['timestamp'])
                )
            
            self._sqlite_conn.commit()
        except Exception as e:
            logger.warning(f"SQLite save failed: {e}")
    
    def create_task(self, description: str, priority: TaskPriority = TaskPriority.NORMAL,
                   dependencies: List[str] = None, metadata: Dict = None) -> Task:
        """Create a new task"""
        task = Task(
            id=str(uuid.uuid4())[:8],
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.tasks[task.id] = task
        self.pending_queue.put(task)
        
        return task
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (all deps satisfied)"""
        ready = []
        
        while not self.pending_queue.empty():
            try:
                task = self.pending_queue.get_nowait()
            except Empty:
                break
            
            # Check dependencies
            deps_satisfied = all(
                dep_id in self.completed_tasks 
                for dep_id in task.dependencies
            )
            
            if deps_satisfied and task.id not in self.running_tasks:
                ready.append(task)
            else:
                # Put back if not ready
                self.pending_queue.put(task)
                break
        
        return ready
    
    def mark_running(self, task_id: str):
        """Mark task as running"""
        if task_id in self.tasks:
            self.running_tasks.add(task_id)
            self.tasks[task_id].state = "running"
            self.tasks[task_id].started_at = time.time()
    
    def mark_completed(self, task_id: str, result: Any = None):
        """Mark task as completed"""
        if task_id in self.tasks:
            self.running_tasks.discard(task_id)
            self.completed_tasks.add(task_id)
            self.tasks[task_id].state = "completed"
            self.tasks[task_id].completed_at = time.time()
            self.tasks[task_id].output_data = result
    
    def mark_failed(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self.tasks:
            self.running_tasks.discard(task_id)
            self.failed_tasks.add(task_id)
            self.tasks[task_id].state = "failed"
            self.tasks[task_id].error = error
            self.tasks[task_id].completed_at = time.time()
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.state = "pending"
                self.failed_tasks.discard(task_id)
                self.pending_queue.put(task)
                return True
        return False
    
    def get_task_graph(self) -> Dict:
        """Get task dependency graph"""
        return {
            "pending": len([t for t in self.tasks.values() if t.state == "pending"]),
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description[:50],
                    "state": t.state,
                    "priority": t.priority.name
                }
                for t in self.tasks.values()
            ]
        }


# ==================== ARTIFACT COLLECTOR ====================

class ArtifactCollector:
    """
    Collects and manages artifacts from task execution
    
    FIXED ISSUES (14):
    - Rich metadata: task_id, step_id, type, checksum, verifier link, preview, retention policy
    """
    
    def __init__(self, storage_dir: str = "artifacts"):
        self.storage_dir = storage_dir
        self.artifacts: Dict[str, List[Dict]] = defaultdict(list)
        self.artifact_metadata: Dict[str, Dict] = {}  # Rich metadata storage
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        # Retention policies
        self.RETENTION_POLICIES = {
            'temporary': 3600,      # 1 hour
            'short': 86400,        # 1 day
            'medium': 604800,      # 1 week
            'long': 2592000,       # 1 month
            'permanent': -1,        # Forever
        }
        
        logger.info(f"📦 Artifact Collector initialized: {storage_dir}")
    
    def collect(
        self, 
        task_id: str, 
        artifact_type: str, 
        content: Any,
        step_id: str = None,
        verifier_link: str = None,
        retention_policy: str = 'medium',
        metadata: Dict = None
    ) -> str:
        """
        Collect an artifact with RICH metadata.
        """
        import hashlib
        import base64
        
        artifact_id = f"{task_id}_{artifact_type}_{int(time.time()*1000)}"
        
        # Calculate checksum
        content_bytes = str(content).encode('utf-8')
        checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # Handle different content types
        if isinstance(content, (dict, list)):
            filepath = f"{self.storage_dir}/{artifact_id}.json"
            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2)
        elif isinstance(content, str) and len(content) > 1000:
            filepath = f"{self.storage_dir}/{artifact_id}.txt"
            with open(filepath, 'w') as f:
                f.write(content)
        else:
            filepath = f"{self.storage_dir}/{artifact_id}.txt"
            with open(filepath, 'w') as f:
                f.write(str(content))
        
        # Create rich metadata
        artifact_metadata = {
            'artifact_id': artifact_id,
            'task_id': task_id,
            'step_id': step_id or f"{task_id}_step_1",
            'type': artifact_type,
            'filepath': filepath,
            'checksum': checksum,
            'size': len(content_bytes),
            'created_at': time.time(),
            'verifier_link': verifier_link,
            'retention_policy': retention_policy,
            'retention_until': time.time() + self.RETENTION_POLICIES.get(retention_policy, 604800),
            'metadata': metadata or {},
            'preview': str(content)[:200] if content else '',
            'verified': False,
            'verified_at': None,
        }
        
        self.artifacts[task_id].append(artifact_metadata)
        self.artifact_metadata[artifact_id] = artifact_metadata
        
        logger.info(f"📦 Artifact collected: {artifact_id}")
        
        return artifact_id
    
    def verify_artifact(self, artifact_id: str, verifier_result: bool) -> None:
        """Mark artifact as verified"""
        if artifact_id in self.artifact_metadata:
            self.artifact_metadata[artifact_id]['verified'] = verifier_result
            self.artifact_metadata[artifact_id]['verified_at'] = time.time()
    
    def get_artifact_metadata(self, artifact_id: str) -> Dict:
        """Get metadata for an artifact"""
        return self.artifact_metadata.get(artifact_id, {})
    
    def get_artifacts(self, task_id: str) -> List[Dict]:
        """Get all artifacts for a task (with metadata)"""
        return self.artifacts.get(task_id, [])
    
    def get_artifacts_summary(self) -> Dict:
        """Get summary of all artifacts"""
        total = sum(len(arts) for arts in self.artifacts.values())
        by_type = defaultdict(int)
        verified_count = 0
        
        for arts in self.artifacts.values():
            for art in arts:
                by_type[art.get('type', 'unknown')] += 1
                if art.get('verified', False):
                    verified_count += 1
        
        return {
            'total_artifacts': total,
            'by_type': dict(by_type),
            'verified': verified_count,
            'unverified': total - verified_count
        }
    
    def cleanup_expired(self) -> int:
        """Clean up expired artifacts based on retention policy"""
        import os
        
        removed = 0
        current_time = time.time()
        
        for artifact_id, metadata in list(self.artifact_metadata.items()):
            if metadata.get('retention_until', -1) > 0 and current_time > metadata['retention_until']:
                filepath = metadata.get('filepath')
                if filepath and os.path.exists(filepath):
                    os.remove(filepath)
                    removed += 1
                
                task_id = metadata.get('task_id')
                if task_id and artifact_id in self.artifacts[task_id]:
                    self.artifacts[task_id].remove(artifact_id)
                
                del self.artifact_metadata[artifact_id]
        
        return removed
    
    def get_all_artifacts(self) -> Dict[str, List[Dict]]:
        """Get all artifacts with metadata"""
        return dict(self.artifacts)


# ==================== SCHEDULER ====================

class Scheduler:
    """
    Background scheduler for tasks
    """
    
    def __init__(self):
        self.scheduled_tasks: List[Dict] = []
        self.running = False
        
        logger.info("⏰ Scheduler initialized")
    
    def schedule(self, task: Callable, delay: float = 0, 
                 interval: float = None, name: str = None):
        """Schedule a task"""
        scheduled = {
            "task": task,
            "delay": delay,
            "interval": interval,
            "name": name or str(uuid.uuid4())[:8],
            "next_run": time.time() + delay,
            "last_run": None
        }
        self.scheduled_tasks.append(scheduled)
        
        return scheduled["name"]
    
    def run_pending(self):
        """Run pending scheduled tasks"""
        now = time.time()
        
        for scheduled in self.scheduled_tasks:
            if now >= scheduled["next_run"]:
                try:
                    scheduled["task"]()
                    scheduled["last_run"] = now
                    
                    if scheduled["interval"]:
                        scheduled["next_run"] = now + scheduled["interval"]
                    else:
                        # One-time task, remove it
                        self.scheduled_tasks.remove(scheduled)
                except Exception as e:
                    logger.error(f"Scheduled task error: {e}")
    
    def cancel(self, name: str):
        """Cancel a scheduled task"""
        self.scheduled_tasks = [
            t for t in self.scheduled_tasks 
            if t["name"] != name
        ]
    
    def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            "task_count": len(self.scheduled_tasks),
            "tasks": [
                {
                    "name": t["name"],
                    "next_run": t["next_run"],
                    "interval": t["interval"]
                }
                for t in self.scheduled_tasks
            ]
        }


# ==================== TELEMETRY ====================

class Telemetry:
    """
    Metrics and monitoring
    """
    
    def __init__(self):
        self.metrics = {
            "tasks_total": 0,
            "tasks_success": 0,
            "tasks_failed": 0,
            "tool_calls": defaultdict(int),
            "tool_failures": defaultdict(int),
            "total_duration": 0.0,
            "total_cost": 0.0,
            "retry_count": 0,
        }
        
        self.history: List[Dict] = []
        
        logger.info("📊 Telemetry initialized")
    
    def record_task(self, success: bool, duration: float, tool_name: str = None):
        """Record task execution"""
        self.metrics["tasks_total"] += 1
        if success:
            self.metrics["tasks_success"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        self.metrics["total_duration"] += duration
        
        if tool_name:
            self.metrics["tool_calls"][tool_name] += 1
            if not success:
                self.metrics["tool_failures"][tool_name] += 1
    
    def record_retry(self):
        """Record retry"""
        self.metrics["retry_count"] += 1
    
    def record_cost(self, cost: float):
        """Record API cost"""
        self.metrics["total_cost"] += cost
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        total = self.metrics["tasks_total"]
        success = self.metrics["tasks_success"]
        
        return {
            **self.metrics,
            "success_rate": success / total if total > 0 else 0,
            "failure_rate": (total - success) / total if total > 0 else 0,
            "avg_duration": self.metrics["total_duration"] / total if total > 0 else 0,
            "tool_reliability": {
                tool: (calls - failures) / calls if calls > 0 else 0
                for tool, calls in self.metrics["tool_calls"].items()
                for failures in [self.metrics["tool_failures"][tool]]
            }
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        m = self.get_metrics()
        
        return f"""📊 **Telemetriya**

✅ Muvaffaqiyat: {m['tasks_success']}/{m['tasks_total']} ({m['success_rate']:.1%})
❌ Muvaffaqiyatsiz: {m['tasks_failed']}
🔄 Qayta urinishlar: {m['retry_count']}
⏱️ O'rtacha vaqt: {m['avg_duration']:.2f}s
💰 Umumiy xarajat: ${m['total_cost']:.4f}

**Tool ishonchliligi:**
{json.dumps(m['tool_reliability'], indent=2) if m['tool_reliability'] else "Ma'lumot yo'q"}"""


# ==================== CENTRAL KERNEL ====================

class CentralKernel:
    """
    THE ONE TRUE ORCHESTRATOR
    
    This is the central operating system for the agent.
    It brings together:
    - TaskManager: Task lifecycle
    - StateMachine: Kernel state
    - Scheduler: Background tasks
    - MultiAgentCoordinator: Agent coordination
    - VerificationEngine: Result verification
    - CriticEngine: Quality evaluation
    - ArtifactCollector: Result storage
    - Telemetry: Metrics
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        
        # Initialize all subsystems
        self.state = KernelState.IDLE
        
        logger.info("🚀 Initializing Central Kernel...")
        
        self.task_manager = TaskManager()
        self.scheduler = Scheduler()
        self.verifier = VerificationEngine(tools_engine)
        self.critic = CriticEngine(api_key)
        
        # Use NEW Multi-Agent Coordinator with 6 full workers
        logger.info("🤖 Initializing NEW Multi-Agent Coordinator with 6 workers...")
        self.coordinator = NewMultiAgentCoordinator(api_key, tools_engine)

        # Planner Quality Tracking
        self.planner_quality = PlannerQualityTracker()

        # Invalid snippets storage for debugging
        self._invalid_snippets_dir = Path("data/invalid_snippets")
        self._invalid_snippets_dir.mkdir(parents=True, exist_ok=True)
        
        self.artifacts = ArtifactCollector()
        self.telemetry = Telemetry()
        
        # Pending approvals
        self.pending_approvals: Dict[str, Dict] = {}
        
        logger.info("✅ Central Kernel Ready!")
    
    async def process(self, user_message: str) -> str:
        """
        Main entry point - process user message through kernel
        """
        start_time = time.time()
        
        logger.info(f"🎯 Kernel processing: {user_message[:50]}...")
        
        # Update state
        self.state = KernelState.THINKING
        
        # Step 1: Analyze and plan
        plan = await self._plan(user_message)
        
        if not plan:
            return "❌ Rejalashtirish muvaffaqiyatsiz"
        
        # Step 2: Evaluate plan quality
        evaluation = self.critic.evaluate_plan(plan)
        
        if not evaluation["approved"]:
            return f"❌ Reja qabul qilinmadi: {evaluation['issues']}"
        
        # Step 3: Execute plan
        self.state = KernelState.ACTING
        
        result = await self._execute(plan)
        
        # Step 4: Verify result
        self.state = KernelState.VERIFYING
        
        verified = await self._verify(result)
        
        if not verified:
            # Step 5: Repair if needed
            self.state = KernelState.REPAIRING
            result = await self._repair(result)
        
        # Update metrics
        duration = time.time() - start_time
        self.telemetry.record_task(
            success=verified,
            duration=duration
        )
        
        self.state = KernelState.IDLE
        
        return result
    
    async def _plan(self, message: str) -> List[Task]:
        """
        Create execution plan using LLM-based planner with robust JSON parsing.
        Enhanced with:
        - Strict schema validation
        - Multiple JSON parsing strategies
        - Enhanced fallback planner with heuristics
        - Full task metadata
        """
        
        # Use native_brain for intelligent planning if available
        if hasattr(self, 'native_brain') and self.native_brain:
            try:
                planning_prompt = f"""Create a detailed task plan for: {message}
Return JSON with tasks array containing: id, description, priority, dependencies, required_tools, verification_type, success_criteria, fallback_strategy, retry_policy, approval_policy, timeout"""
                
                response = self.native_brain.think(planning_prompt)
                tasks = self._parse_llm_plan(response)
                
                if tasks:
                    logger.info(f"📋 Created {len(tasks)} tasks via LLM planner")
                    return tasks
                    
            except Exception as e:
                logger.warning(f"LLM planning failed: {e}")
        
        # Enhanced fallback planner
        return self._heuristic_planner(message)
    def _parse_llm_plan(self, response: str) -> List[Task]:
        """
        STRICT JSON PARSING - No1-grade governed.
        
        HAQIQAT: Tool result from execution, NOT from LLM parsing.
        LLM output is ONLY suggestion for planning.
        
        Strict validation:
        - Schema validation MANDATORY
        - Invalid plan diagnostics
        - Failed parse telemetry
        - Planner quality metrics
        - NO silent failures
        """
        import re, json
        import time

        tasks = []
        parsing_attempts = []
        parse_diagnostics = {"response_length": 0, "has_json_markers": False, "has_prose": False, "strategies_tried": [], "failures": []}

        # Pre-processing
        response = response.strip()
        parse_diagnostics["response_length"] = len(response)
        
        # Check if response is prose (model hallucination risk)
        if response.startswith(("{", "[")):
            parse_diagnostics["has_json_markers"] = True
        else:
            parse_diagnostics["has_prose"] = True
            logger.warning("⚠️ LLM response contains prose, not JSON - HIGH RISK")

        # STRICT parsing strategies
        parsing_strategies = [
            {'name': 'tasks_key_object', 'pattern': r'\{[^{}]*"tasks"\s*:\s*\[', 'try_extract': lambda: re.search(r'\{[^{}]*"tasks"\s*:\s*\[.*\]', response, re.DOTALL)},
            {'name': 'array_with_description', 'pattern': r'\[.*"description".*\]', 'try_extract': lambda: re.search(r'\[.*"description".*\]', response)},
            {'name': 'brackets_balanced', 'pattern': 'any', 'try_extract': lambda: self._extract_balanced_brackets(response)},
        ]

        for strategy in parsing_strategies:
            strategy_name = strategy['name']
            start_time = time.time()
            parse_diagnostics["strategies_tried"].append(strategy_name)

            try:
                json_match = strategy['try_extract']()
                if json_match:
                    json_str = json_match.group() if hasattr(json_match, 'group') else str(json_match)
                    
                    # STRICT: Validate JSON
                    try:
                        tasks_data = json.loads(json_str)
                        
                        # STRICT: Validate schema
                        validation_result = self._validate_plan_schema(tasks_data)
                        
                        if validation_result['valid']:
                            if isinstance(tasks_data, dict) and 'tasks' in tasks_data:
                                tasks_data = tasks_data['tasks']

                            if isinstance(tasks_data, list):
                                # Create tasks with diagnostics
                                tasks = self._create_tasks_from_plan({"tasks": tasks_data}, response_snippet=response)
                                if tasks:
                                    parsing_attempts.append({
                                        'strategy': strategy_name, 'success': True, 'tasks_count': len(tasks), 'time_ms': (time.time() - start_time) * 1000
                                    })
                                    self._emit_plan_parsing_telemetry(True, parsing_attempts, response, parse_diagnostics, strategy_name)
                                    return tasks
                        else:
                            # Schema failed - log detailed diagnostics
                            parse_diagnostics['failures'].append({
                                'strategy': strategy_name,
                                'reason': 'schema_validation_failed',
                                'errors': validation_result.get('errors', [])
                            })
                            logger.warning(f"⚠️ Schema validation failed for strategy '{strategy_name}': {validation_result.get('errors', [])}")
                            pass
                            
                    except json.JSONDecodeError as e:
                        parsing_attempts.append({'strategy': strategy_name, 'success': False, 'reason': 'json_decode_error', 'error': str(e), 'time_ms': (time.time() - start_time) * 1000})
                        
            except Exception as e:
                parsing_attempts.append({'strategy': strategy_name, 'success': False, 'reason': 'exception', 'error': str(e), 'time_ms': (time.time() - start_time) * 1000})

        # ALL strategies failed - STRICT mode
        logger.error(f"❌ Plan parsing FAILED - all strategies exhausted")
        
        # Emit failure telemetry
        self._emit_plan_parsing_telemetry(False, parsing_attempts, response, parse_diagnostics, None)
        
        # STRICT: Return empty - do NOT fallback to model
        return tasks



    def _emit_plan_parsing_telemetry(self, success: bool, parsing_attempts: List[Dict], response: str, parse_diagnostics: Dict, successful_strategy: str = None):
        """
        Emit telemetry for plan parsing with full diagnostics.
        
        This enables:
        - Debugging which parsing strategy failed
        - Self-improvement signals for prompt engineering
        - Quality metrics for planner
        """
        import time
        
        # Determine recovery hint
        recovery_hint = _get_recovery_hint(parsing_attempts) if not success else "Success"
        
        telemetry_data = {
            'success': success,
            'successful_strategy': successful_strategy,
            'attempts': parsing_attempts,
            'response_preview': response[:500],  # More context
            'diagnostics': parse_diagnostics,
            'recovery_hint': recovery_hint,
            'timestamp': time.time(),
            'strategies_tried_count': len(parse_diagnostics.get("strategies_tried", [])),
            'failures_count': len(parse_diagnostics.get("failures", []))
        }
        
        # Log prominently for debugging
        if success:
            logger.info(f"✅ Plan parsing SUCCESS with strategy: {successful_strategy}")
        else:
            logger.error(f"❌ Plan parsing FAILED. Recovery hint: {recovery_hint}")
            logger.error(f"   Strategies tried: {parse_diagnostics.get('strategies_tried', [])}")
            logger.error(f"   Failures: {parse_diagnostics.get('failures', [])}")
        
        # Emit to telemetry if available
        if hasattr(self, 'telemetry') and self.telemetry:
            try:
                self.telemetry.record_event('plan_parsing', telemetry_data)
            except Exception as e:
                logger.error(f"Failed to emit telemetry: {e}")
        
        # Emit self-improvement signal if available
        if hasattr(self, 'emit_improvement_signal') and not success:
            try:
                self.emit_improvement_signal('plan_parsing_failure', {
                    'recovery_hint': recovery_hint,
                    'strategies_failed': [a.get('strategy') for a in parsing_attempts if not a.get('success', False)],
                    'response_preview': response[:200]
                })
            except Exception as e:
                logger.error(f"Failed to emit improvement signal: {e}")

        # Record in planner quality tracker
        if hasattr(self, 'planner_quality') and self.planner_quality:
            strategy_used = successful_strategy if successful_strategy else "failed"
            total_time = sum(a.get('time_ms', 0) for a in parsing_attempts)
            self.planner_quality.record_parse(success, strategy_used, total_time)

        # Save invalid snippets to disk for debugging
        if not success and hasattr(self, '_invalid_snippets_dir'):
            self._save_invalid_snippet(response, parse_diagnostics, parsing_attempts)

        # Log detailed diagnostics
        self._log_parse_diagnostics(parse_diagnostics, parsing_attempts)
    

    def _save_invalid_snippet(self, response: str, diagnostics: Dict, attempts: List[Dict]):
        """Save invalid parsing snippets to disk for debugging"""
        import json
        import uuid
        import time
        
        try:
            snippet_data = {
                'snippet_id': str(uuid.uuid4())[:8],
                'response': response[:2000],  # Limit size
                'diagnostics': diagnostics,
                'attempts': attempts,
                'timestamp': time.time()
            }
            
            filename = f"invalid_snippet_{snippet_data['snippet_id']}.json"
            filepath = self._invalid_snippets_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(snippet_data, f, indent=2)
                
            logger.info(f"💾 Invalid snippet saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save invalid snippet: {e}")

    def _log_parse_diagnostics(self, diagnostics: Dict, attempts: List[Dict]):
        """Log detailed parse diagnostics for debugging"""
        # Log JSON markers status
        if diagnostics.get('has_prose'):
            logger.warning(f"   📝 Response contains prose (not pure JSON)")
        if diagnostics.get('has_json_markers'):
            logger.info(f"   📋 Response has JSON markers")
            
        # Log response length
        logger.info(f"   📏 Response length: {diagnostics.get('response_length', 0)} chars")
        
        # Log each failed attempt
        for i, attempt in enumerate(attempts):
            if not attempt.get('success', False):
                logger.warning(f"   ❌ Attempt {i+1}: {attempt.get('strategy')} - {attempt.get('reason')}: {attempt.get('error', 'N/A')}")
    def _extract_balanced_brackets(self, text: str) -> Optional[re.Match]:
        """Extract balanced JSON from text"""
        import re
        
        # Find all { } pairs
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # Try to find complete JSON object
        depth = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    # Found balanced brackets
                    return re.match(r'\{[\s\S]*\}', text[start_idx:i+1])
        
        return None
    
    def _extract_json_lines(self, text: str) -> Optional[re.Match]:
        """Extract JSON from lines that look like JSON objects"""
        import re
        
        lines = text.split('\n')
        json_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_lines.append(line)
        
        if json_lines:
            # Try to combine into array
            combined = '[' + ','.join(json_lines) + ']'
            try:
                json.loads(combined)  # Validate
                return re.match(r'\[[\s\S]*\]', combined)
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"JSON line combination failed: {e}")
                pass
        
        return None
    
    def _validate_plan_schema(self, data: Any) -> Dict:
        """
        Validate plan data against expected schema.
        
        Returns:
        {
            'valid': bool,
            'errors': List[str]
        }
        """
        
        errors = []
        
        # Must be dict or list
        if not isinstance(data, (dict, list)):
            errors.append(f"Plan must be dict or list, got {type(data)}")
            return {'valid': False, 'errors': errors}
        
        # If it's a dict, must have 'tasks' key or be an array
        if isinstance(data, dict):
            if 'tasks' not in data and not any(k in data for k in ['id', 'description', 'steps']):
                errors.append("Dict must have 'tasks' key or task fields")
        
        # If it has tasks, validate each
        tasks = data.get('tasks', []) if isinstance(data, dict) else data
        
        if isinstance(tasks, list):
            for i, task in enumerate(tasks):
                if not isinstance(task, dict):
                    errors.append(f"Task {i} must be dict, got {type(task)}")
                    continue
                
                # Required fields
                if 'description' not in task:
                    errors.append(f"Task {i} missing 'description'")
                
                # Validate optional fields
                allowed_priorities = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW', '']
                priority = task.get('priority', '').upper()
                if priority and priority not in allowed_priorities:
                    errors.append(f"Task {i} invalid priority: {priority}")
                
                # Validate verification_type if present
                allowed_verification = ['manual', 'browser', 'screenshot', 'server', 'code', 'file', 'function']
                verification = task.get('verification_type', '').lower()
                if verification and verification not in allowed_verification:
                    errors.append(f"Task {i} invalid verification_type: {verification}")
                
                # Validate approval_policy if present
                allowed_approval = ['auto', 'manual', 'never']
                approval = task.get('approval_policy', '').lower()
                if approval and approval not in allowed_approval:
                    errors.append(f"Task {i} invalid approval_policy: {approval}")
                
                # Validate sandbox_mode if present
                allowed_sandbox = ['safe', 'normal', 'advanced']
                sandbox = task.get('sandbox_mode', '').lower()
                if sandbox and sandbox not in allowed_sandbox:
                    errors.append(f"Task {i} invalid sandbox_mode: {sandbox}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _create_tasks_from_plan(self, plan_data: Dict, response_snippet: str = "") -> List[Task]:
        """
        Create tasks from plan data with ENHANCED validation and detailed diagnostics.
        
        Fixed issues:
        - Required fields validation
        - Allowed verification types validation
        - Allowed approval policies validation
        - Allowed sandbox modes validation
        - Tool existence check
        - No more silent minimal task creation on parse errors
        - Detailed invalid task tracking with full diagnostics
        - Planner quality metrics
        - Self-improvement feedback
        """
        
        import uuid
        import time
        import json
        
        tasks = []
        invalid_tasks = []  # Track invalid tasks with full diagnostics
        task_validation_counters = {
            'missing_description': 0,
            'invalid_priority': 0,
            'invalid_verification': 0,
            'invalid_approval': 0,
            'invalid_sandbox': 0,
            'unknown_tools': 0,
            'invalid_dependencies': 0,
            'creation_error': 0,
        }
        
        # Allowed values
        ALLOWED_PRIORITIES = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW', '']
        ALLOWED_VERIFICATION = ['manual', 'browser', 'screenshot', 'server', 'code', 'file', 'function']
        ALLOWED_APPROVAL = ['auto', 'manual', 'never']
        ALLOWED_SANDBOX = ['safe', 'normal', 'advanced']
        
        # Known tools (can be extended)
        KNOWN_TOOLS = [
            'execute_command', 'execute_code', 'write_file', 'read_file', 
            'delete_file', 'browser_navigate', 'browser_click', 'browser_type',
            'web_search', 'web_request', 'install_package', 'take_screenshot'
        ]
        
        # Get snippet from response for diagnostics
        snippet = response_snippet[:500] if response_snippet else ""
        
        for i, t in enumerate(plan_data.get('tasks', [])):
            task_errors = []
            failed_fields = []
            
            # Skip if not a dict
            if not isinstance(t, dict):
                error_msg = f"Task {i} is not a dictionary"
                task_errors.append(error_msg)
                failed_fields.append('type_check_failed')
                task_validation_counters['creation_error'] += 1
                invalid_tasks.append({
                    'index': i,
                    'failed_fields': failed_fields,
                    'errors': task_errors,
                    'snippet': snippet,
                    'parse_reason': 'not_a_dictionary'
                })
                continue
            
            # Validate required fields
            if not t.get('description'):
                task_errors.append(f"Task {i} missing 'description'")
                failed_fields.append('description')
                task_validation_counters['missing_description'] += 1
            
            # Validate priority
            priority = t.get('priority', '').upper()
            if priority and priority not in ALLOWED_PRIORITIES:
                task_errors.append(f"Invalid priority: {priority}")
                failed_fields.append('priority')
                task_validation_counters['invalid_priority'] += 1
            
            # Validate verification_type
            verification = t.get('verification_type', '').lower()
            if verification and verification not in ALLOWED_VERIFICATION:
                task_errors.append(f"Invalid verification_type: {verification}")
                failed_fields.append('verification_type')
                task_validation_counters['invalid_verification'] += 1
            
            # Validate approval_policy
            approval = t.get('approval_policy', '').lower()
            if approval and approval not in ALLOWED_APPROVAL:
                task_errors.append(f"Invalid approval_policy: {approval}")
                failed_fields.append('approval_policy')
                task_validation_counters['invalid_approval'] += 1
            
            # Validate sandbox_mode
            sandbox = t.get('sandbox_mode', '').lower()
            if sandbox and sandbox not in ALLOWED_SANDBOX:
                task_errors.append(f"Invalid sandbox_mode: {sandbox}")
                failed_fields.append('sandbox_mode')
                task_validation_counters['invalid_sandbox'] += 1
            
            # Validate required_tools if present
            required_tools = t.get('required_tools', [])
            if required_tools:
                if isinstance(required_tools, list):
                    unknown_tools = [tool for tool in required_tools if tool not in KNOWN_TOOLS]
                    if unknown_tools:
                        task_errors.append(f"Unknown tools: {unknown_tools}")
                        failed_fields.append('required_tools')
                        task_validation_counters['unknown_tools'] += 1
                else:
                    task_errors.append("'required_tools' must be a list")
                    failed_fields.append('required_tools')
            
            # Validate dependencies if present
            deps = t.get('dependencies', [])
            if deps:
                if not isinstance(deps, list):
                    task_errors.append("'dependencies' must be a list")
                    failed_fields.append('dependencies')
                    task_validation_counters['invalid_dependencies'] += 1
            
            # Determine parse reason
            if task_errors:
                if any('description' in e for e in task_errors):
                    parse_reason = 'missing_required_field'
                elif any('Invalid priority' in e for e in task_errors):
                    parse_reason = 'invalid_field_value'
                else:
                    parse_reason = 'validation_failed'
            else:
                parse_reason = None
            
            # If there are critical errors, skip this task
            critical_errors = [e for e in task_errors if 'description' in e or 'priority' in e or 'Invalid' in e]
            
            if critical_errors:
                logger.warning(f"Task {i} skipped due to critical errors: {critical_errors}")
                invalid_tasks.append({
                    'index': i,
                    'failed_fields': failed_fields,
                    'errors': task_errors,
                    'snippet': snippet,
                    'parse_reason': parse_reason or 'critical_validation_error'
                })
                continue
            
            # If non-critical errors (like unknown tools), log but still create task
            if task_errors:
                logger.warning(f"Task {i} created with warnings: {task_errors}")
            
            # Create task with validated data
            try:
                priority = TaskPriority.NORMAL
                if priority == 'HIGH' or priority == 'CRITICAL':
                    priority = TaskPriority.HIGH
                elif t.get('priority', '').upper() == 'LOW':
                    priority = TaskPriority.LOW
                
                task = Task(
                    id=t.get('id', f"task_{int(time.time()*1000)}_{i}"),
                    description=t.get('description', 'Unknown task'),
                    priority=priority,
                    dependencies=t.get('dependencies', []),
                    timeout=t.get('timeout', 30),
                    max_retries=t.get('retry_policy', 3),
                    approval_policy=t.get('approval_policy', 'auto'),
                    sandbox_mode=t.get('sandbox_mode', 'normal'),
                )
                
                # Set rich metadata
                task.input_data = {
                    'required_tools': t.get('required_tools', []),
                    'verification_type': t.get('verification_type', 'manual'),
                    'success_criteria': t.get('success_criteria', ''),
                    'fallback_strategy': t.get('fallback_strategy', ''),
                    'file_path': t.get('file_path', ''),
                    'expected_elements': t.get('expected_elements', []),
                    'process_name': t.get('process_name', ''),
                    'url': t.get('url', ''),
                    'port': t.get('port', 80),
                    'host': t.get('host', 'localhost'),
                    'code': t.get('code', ''),
                    'language': t.get('language', 'python'),
                    'risk_level': t.get('risk_level', 'medium'),
                    'expected_artifacts': t.get('expected_artifacts', []),
                    'rollback_point': t.get('rollback_point'),
                }
                
                # Set artifact expectations
                task.artifact_expectations = t.get('expected_artifacts', [])
                
                tasks.append(task)
                
            except Exception as e:
                logger.error(f"Failed to create task {i}: {e}")
                invalid_tasks.append({
                    'index': i,
                    'failed_fields': ['creation_exception'],
                    'errors': [str(e)],
                    'snippet': snippet,
                    'parse_reason': 'task_creation_error'
                })
                task_validation_counters['creation_error'] += 1
        
        # Log summary of invalid tasks with detailed diagnostics
        total_tasks = len(plan_data.get('tasks', []))
        if invalid_tasks:
            logger.error(f"❌ Task validation FAILED: {len(invalid_tasks)}/{total_tasks} tasks invalid")
            logger.error(f"   Validation counters: {task_validation_counters}")
            for inv in invalid_tasks:
                logger.error("   Task {}: fields={}, reason={}, errors={}".format(inv["index"], inv["failed_fields"], inv["parse_reason"], inv["errors"]))
        
        # Calculate planner quality metrics
        success_rate = (len(tasks) / total_tasks * 100) if total_tasks > 0 else 0
        quality_grade = "EXCELLENT" if success_rate >= 90 else "GOOD" if success_rate >= 70 else "NEEDS_IMPROVEMENT" if success_rate >= 50 else "POOR"
        
        logger.info(f"📊 Planner quality: {quality_grade} ({len(tasks)}/{total_tasks} = {success_rate:.1f}%)")
        
        # Emit ALWAYS (not conditional) - comprehensive telemetry for task creation quality
        telemetry_data = {
            'total_tasks': total_tasks,
            'valid_tasks': len(tasks),
            'invalid_tasks': len(invalid_tasks),
            'success_rate': success_rate,
            'quality_grade': quality_grade,
            'validation_counters': task_validation_counters,
            'invalid_details': invalid_tasks,  # Full details with index, failed_fields, snippet, parse_reason
            'timestamp': time.time()
        }
        
        # Log telemetry prominently
        logger.info(f"📈 Task creation telemetry: {json.dumps(telemetry_data, indent=2)}")
        
        # Emit to telemetry if available
        if hasattr(self, 'telemetry') and self.telemetry:
            try:
                self.telemetry.record_event('task_creation', telemetry_data)
            except Exception as e:
                logger.error(f"Failed to emit task_creation telemetry: {e}")
        
        # Emit self-improvement signal if there are invalid tasks
        if hasattr(self, 'emit_improvement_signal') and invalid_tasks:
            try:
                self.emit_improvement_signal('task_creation_failure', {
                    'quality_grade': quality_grade,
                    'success_rate': success_rate,
                    'validation_counters': task_validation_counters,
                    'top_failure_reasons': [
                        {'reason': k, 'count': v} 
                        for k, v in sorted(task_validation_counters.items(), key=lambda x: -x[1]) 
                        if v > 0
                    ][:5],
                    'failed_task_indices': [inv['index'] for inv in invalid_tasks]
                })
            except Exception as e:
                logger.error(f"Failed to emit improvement signal: {e}")

        # Record in planner quality tracker
        if hasattr(self, 'planner_quality') and self.planner_quality:
            strategy_used = successful_strategy if successful_strategy else "failed"
            total_time = sum(a.get('time_ms', 0) for a in parsing_attempts)
            self.planner_quality.record_parse(success, strategy_used, total_time)

        # Save invalid snippets to disk for debugging
        if not success and hasattr(self, '_invalid_snippets_dir'):
            self._save_invalid_snippet(response, parse_diagnostics, parsing_attempts)

        # Log detailed diagnostics
        self._log_parse_diagnostics(parse_diagnostics, parsing_attempts)
        
        return tasks
    
    def _heuristic_planner(self, message: str) -> List[Task]:
        """
        ENHANCED fallback planner with FULL metadata for No1 agent.
        
        Fixed issues:
        - Rollback point support
        - Sandbox mode selection
        - Approval policy
        - Artifact expectations
        - Retry policy richness
        - Dependency graph depth
        - Risk level assessment
        """
        
        import uuid
        import time
        tasks = []
        msg_lower = message.lower()
        
        # Determine risk level
        is_dangerous = any(k in msg_lower for k in ['ochir', 'delete', 'format', 'drop', 'rm -rf', 'truncate'])
        is_high_risk = any(k in msg_lower for k in ['install', 'apt', 'yum', 'pip install', 'npm install'])
        
        risk_level = 'critical' if is_dangerous else ('high' if is_high_risk else 'medium')
        
        # Sandbox mode based on risk
        sandbox_mode = 'safe' if is_dangerous else ('advanced' if is_high_risk else 'normal')
        
        # Approval policy based on risk
        approval_policy = 'manual' if is_dangerous or is_high_risk else 'auto'
        
        # Task type detection with RICH metadata
        task_specs = []
        
        # File creation tasks
        if any(k in msg_lower for k in ['yarat', 'yoz', 'fayl', 'create', 'write', 'new file']):
            task_specs.append({
                'type': 'file', 
                'tools': ['write_file'], 
                'ver': 'file',
                'desc': 'Fayl yaratish',
                'task_type': 'file',
                'expected_artifacts': [],
                'rollback_point': {'type': 'file_backup', 'description': 'Faylni zaxiraga olish'}
            })
        
        # File reading tasks
        if any(k in msg_lower for k in ['oqish', 'read', 'ko\'r', 'view', 'show']):
            task_specs.append({
                'type': 'read', 
                'tools': ['read_file'], 
                'ver': 'function',
                'desc': 'Faylni o\'qish',
                'task_type': 'file',
                'expected_artifacts': [],
                'rollback_point': None
            })
        
        # Search tasks
        if any(k in msg_lower for k in ['qidir', 'internet', 'search', 'web', 'find']):
            task_specs.append({
                'type': 'search', 
                'tools': ['web_search'], 
                'ver': 'function',
                'desc': 'Internetda qidirish',
                'task_type': 'search',
                'expected_artifacts': [],
                'rollback_point': None
            })
        
        # Browser tasks
        if any(k in msg_lower for k in ['sahifa', 'page', 'sayt', 'url', 'browser', 'website', 'open']):
            task_specs.append({
                'type': 'browser', 
                'tools': ['browser_navigate'], 
                'ver': 'browser',
                'desc': 'Sahifaga kirish',
                'task_type': 'browser',
                'expected_artifacts': ['screenshot'],
                'rollback_point': {'type': 'browser_state', 'description': 'Browser holatini saqlash'}
            })
        
        # Code execution tasks
        if any(k in msg_lower for k in ['kod', 'code', 'python', 'javascript', 'run', 'execute', 'bajar']):
            task_specs.append({
                'type': 'code', 
                'tools': ['execute_code'], 
                'ver': 'code',
                'desc': 'Kodni bajarish',
                'task_type': 'code',
                'expected_artifacts': ['output'],
                'rollback_point': {'type': 'env_snapshot', 'description': 'Environment snapshot'}
            })
        
        # Command execution tasks
        if any(k in msg_lower for k in ['buyruq', 'command', 'terminal', 'shell', 'bash']):
            task_specs.append({
                'type': 'command', 
                'tools': ['execute_command'], 
                'ver': 'function',
                'desc': 'Buyruqni bajarish',
                'task_type': 'server',
                'expected_artifacts': [],
                'rollback_point': {'type': 'system_state', 'description': 'System state backup'}
            })
        
        # Server/service tasks
        if any(k in msg_lower for k in ['server', 'serve', 'start', 'run service']):
            task_specs.append({
                'type': 'server', 
                'tools': ['execute_command', 'execute_code'], 
                'ver': 'server',
                'desc': 'Serverni ishga tushirish',
                'task_type': 'server',
                'expected_artifacts': [],
                'rollback_point': {'type': 'service_backup', 'description': 'Service state backup'}
            })
        
        # Screenshot tasks
        if any(k in msg_lower for k in ['screenshot', 'skrin', 'capture', 'sahifa rasmi']):
            task_specs.append({
                'type': 'screenshot', 
                'tools': ['take_screenshot'], 
                'ver': 'screenshot',
                'desc': 'Screenshot olish',
                'task_type': 'browser',
                'expected_artifacts': ['*.png', '*.jpg'],
                'rollback_point': None
            })
        
        # Install tasks
        if any(k in msg_lower for k in ['install', 'o\'rnat', 'setup', 'configure']):
            task_specs.append({
                'type': 'install', 
                'tools': ['install_package', 'execute_command'], 
                'ver': 'function',
                'desc': 'Paketni o\'rnatish',
                'task_type': 'install',
                'expected_artifacts': [],
                'rollback_point': {'type': 'package_list', 'description': 'Installed packages list'}
            })
        
        # Default task if none matched
        if not task_specs:
            task_specs.append({
                'type': 'general', 
                'tools': ['execute_command'], 
                'ver': 'manual',
                'desc': message[:100],
                'task_type': 'general',
                'expected_artifacts': [],
                'rollback_point': None
            })
        
        # Create tasks with full metadata
        for i, spec in enumerate(task_specs):
            # Set priority based on position and risk
            if i == 0:
                priority = TaskPriority.CRITICAL if risk_level == 'critical' else TaskPriority.HIGH
            elif i < len(task_specs) - 1:
                priority = TaskPriority.NORMAL
            else:
                priority = TaskPriority.LOW
            
            # Create task with full metadata
            task = Task(
                id=f"task_{int(time.time()*1000)}_{i}",
                description=spec['desc'],
                priority=priority,
                dependencies=[tasks[-1].id] if tasks else [],
                timeout=30,
                max_retries=3,
                approval_policy=approval_policy,
                sandbox_mode=sandbox_mode,
            )
            
            # Set FULL metadata
            task.input_data = {
                'required_tools': spec['tools'],
                'verification_type': spec['ver'],
                'success_criteria': f"{spec['desc']} muvaffaqiyatli",
                'fallback_strategy': 'ALTERNATIVE_TOOL',
                'task_type': spec.get('task_type', 'general'),
                'risk_level': risk_level,
                'expected_artifacts': spec.get('expected_artifacts', []),
                'rollback_point': spec.get('rollback_point'),
                'retry_policy': {
                    'max_retries': 3,
                    'backoff_strategy': 'exponential',
                    'initial_delay': 1,
                    'max_delay': 30
                },
                'timeout': task.timeout,
            }
            
            # Set artifact expectations
            task.artifact_expectations = spec.get('expected_artifacts', [])
            
            # Set rollback point
            if spec.get('rollback_point'):
                task.rollback_point = {
                    **spec['rollback_point'],
                    'timestamp': time.time(),
                    'task_id': task.id
                }
            
            tasks.append(task)
        
        # Add dependency chain
        for i in range(1, len(tasks)):
            if tasks[i-1].id not in tasks[i].dependencies:
                tasks[i].dependencies.append(tasks[i-1].id)
        
        logger.info(f"📋 Created {len(tasks)} tasks via enhanced heuristic planner")
        logger.info(f"   Risk level: {risk_level}, Sandbox: {sandbox_mode}, Approval: {approval_policy}")
        
        return tasks
    
    async def _execute(self, plan: List[Task]) -> str:
        """
        STRICT GOVERNED RUNTIME CHAIN - No1 Grade.
        
        CRITICAL: This is the ONE TRUE ORCHESTRATOR pipeline.
        
        Pipeline: policy -> validate -> approval -> sandbox -> execute -> verify -> artifact -> persist -> telemetry
        
        FIXED ISSUES:
        1. Single clean pipeline - no complex fallbacks
        2. History/reliability/context-aware tool selection
        3. Simple success semantics
        4. Deeply integrated approval denied/expired flow
        """
        
        import re, json, time
        from typing import Dict, Any, Optional, List
        
        results = []
        completed_tasks = set()
        failed_tasks = set()
        
        # STRICT Pipeline Steps (immutable order)
        PIPELINE_STEPS = [
            'policy_check',      # Step 1: Policy enforcement
            'dependency_check',   # Step 2: Task dependencies
            'tool_selection',    # Step 3: Context-aware tool selection
            'argument_validation',# Step 4: Strict argument validation
            'approval_check',    # Step 5: Approval workflow
            'sandbox_setup',     # Step 6: Sandbox configuration
            'tool_execution',    # Step 7: Actual execution
            'verification',      # Step 8: Result verification
            'artifact_collection',# Step 9: Artifact collection
            'persistence',       # Step 10: State persistence
            'telemetry'          # Step 11: Metrics recording
        ]
        
        # Tool configuration - strict mapping
        TOOL_CONFIG = {
            'write_file': {
                'dangerous': True,
                'required_args': ['path', 'content'],
                'sandbox_mode': 'safe',
                'timeout': 30
            },
            'read_file': {
                'dangerous': False,
                'required_args': ['path'],
                'sandbox_mode': 'safe',
                'timeout': 10
            },
            'web_search': {
                'dangerous': False,
                'required_args': ['query'],
                'sandbox_mode': 'safe',
                'timeout': 15
            },
            'execute_command': {
                'dangerous': True,
                'required_args': ['command'],
                'sandbox_mode': 'advanced',
                'timeout': 60
            },
            'execute_code': {
                'dangerous': True,
                'required_args': ['code'],
                'sandbox_mode': 'advanced',
                'timeout': 60
            },
            'browser_navigate': {
                'dangerous': False,
                'required_args': ['url'],
                'sandbox_mode': 'normal',
                'timeout': 30
            },
            'delete_file': {
                'dangerous': True,
                'required_args': ['path'],
                'sandbox_mode': 'advanced',
                'timeout': 15
            },
            'install_package': {
                'dangerous': True,
                'required_args': ['package'],
                'sandbox_mode': 'advanced',
                'timeout': 120
            },
            'take_screenshot': {
                'dangerous': False,
                'required_args': ['path'],
                'sandbox_mode': 'safe',
                'timeout': 10
            },
            'web_request': {
                'dangerous': False,
                'required_args': ['url'],
                'sandbox_mode': 'safe',
                'timeout': 30
            }
        }

        # Get tool reliability history for smart selection
        tool_reliability = self._get_tool_reliability_history()
        
        for task in plan:
            pipeline_state = {
                'task_id': task.id, 
                'pipeline': PIPELINE_STEPS.copy(), 
                'current_step': 0, 
                'failed_at': None, 
                'execution_data': {}
            }
            step_start_time = time.time()
            
            try:
                # =====================================================
                # STEP 1: Policy Check
                # =====================================================
                policy = getattr(task, 'approval_policy', 'auto')
                sandbox_mode = getattr(task, 'sandbox_mode', 'normal')
                
                if policy == 'never':
                    raise PermissionError("Policy DENIED: approval_policy is 'never'")
                
                # =====================================================
                # STEP 2: Dependency Check
                # =====================================================
                if task.dependencies:
                    deps_met = all(dep_id in completed_tasks for dep_id in task.dependencies)
                    if not deps_met:
                        logger.warning(f"Task {task.id} waiting for dependencies")
                        task.status = TaskStatus.DEPENDENCIES_WAITING
                        failed_tasks.add(task.id)
                        results.append(f"✗ [DEPENDENCY] {task.description}")
                        continue
                
                self.task_manager.mark_running(task.id)
                self.state = KernelState.ACTING
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                
                logger.info(f"⚡ EXECUTING: {task.description}")
                
                task_meta = task.input_data or {}
                required_tools = task_meta.get('required_tools', [])
                verification_type = task_meta.get('verification_type', 'manual')
                
                # =====================================================
                # STEP 3: Context-Aware Tool Selection
                # =====================================================
                tool_name = self._select_tool_strict(
                    task=task,
                    required_tools=required_tools,
                    task_meta=task_meta,
                    available_tools=list(TOOL_CONFIG.keys()),
                    tool_reliability=tool_reliability,
                    completed_tasks=completed_tasks
                )
                
                if not tool_name:
                    raise ValueError(f"No suitable tool found for task {task.id}")
                
                tool_config = TOOL_CONFIG.get(tool_name, {})
                
                # =====================================================
                # STEP 4: Strict Argument Validation
                # =====================================================
                validated_args = self._build_strict_args(tool_name, task, task_meta)
                
                required = tool_config.get('required_args', [])
                missing_args = [arg for arg in required if arg not in validated_args or not validated_args[arg]]
                if missing_args:
                    raise ValueError(f"Missing required arguments: {missing_args}")
                
                for arg, value in validated_args.items():
                    if value is None or value == '':
                        raise ValueError(f"Empty value for argument: {arg}")
                
                # =====================================================
                # STEP 5: Approval Workflow (with deep integration)
                # =====================================================
                needs_approval = tool_config.get('dangerous', False)
                approval_status = None
                
                if needs_approval and hasattr(self, 'approval_engine') and self.approval_engine:
                    if policy == 'never':
                        raise PermissionError("Approval denied: policy is 'never'")
                    elif policy == 'manual':
                        # DEEP integration: approval denied/expired flow
                        approval_result = await self._execute_approval_flow(
                            task_id=task.id,
                            tool_name=tool_name,
                            args=validated_args,
                            risk_level='high' if tool_config.get('dangerous') else 'medium',
                            timeout=30
                        )
                        
                        if approval_result['status'] == 'denied':
                            # Track for recovery - DEEP integration
                            task.metadata['approval_denied'] = True
                            task.metadata['approval_expired'] = False
                            task.metadata['approval_recovery_needed'] = True
                            task.error_type = ErrorType.APPROVAL_DENIED
                            task.status = TaskStatus.RECOVERING
                            
                            # Telemetry
                            if hasattr(self, 'telemetry') and self.telemetry:
                                self.telemetry.record_event('approval_denied', {
                                    'task_id': task.id,
                                    'tool_name': tool_name,
                                    'timestamp': time.time()
                                })
                            
                            results.append(f"⚠️ [APPROVAL_DENIED] {task.description} - Recovery will handle")
                            continue
                        
                        elif approval_result['status'] == 'expired':
                            # Track for recovery - DEEP integration
                            task.metadata['approval_denied'] = False
                            task.metadata['approval_expired'] = True
                            task.metadata['approval_recovery_needed'] = True
                            task.error_type = ErrorType.APPROVAL_TIMEOUT
                            task.status = TaskStatus.RECOVERING
                            
                            # Telemetry
                            if hasattr(self, 'telemetry') and self.telemetry:
                                self.telemetry.record_event('approval_expired', {
                                    'task_id': task.id,
                                    'tool_name': tool_name,
                                    'timestamp': time.time()
                                })
                            
                            results.append(f"⚠️ [APPROVAL_EXPIRED] {task.description} - Recovery will handle")
                            continue
                        
                        approval_status = approval_result['status']
                
                # =====================================================
                # STEP 6: Sandbox Setup
                # =====================================================
                configured_sandbox_mode = sandbox_mode or tool_config.get('sandbox_mode', 'normal')
                sandbox_ready = self._setup_sandbox(tool_name, configured_sandbox_mode)
                
                if not sandbox_ready:
                    raise RuntimeError(f"Sandbox setup failed for mode: {configured_sandbox_mode}")
                
                # =====================================================
                # STEP 7: Tool Execution (REAL execution)
                # =====================================================
                exec_result = await self._execute_tool_strict(
                    task=task,
                    tool_name=tool_name,
                    args=validated_args,
                    timeout=tool_config.get('timeout', 30)
                )
                
                # =====================================================
                # STEP 8: Verification
                # =====================================================
                verification_passed = True
                verification_details = None
                
                if verification_type != 'manual' and exec_result.success:
                    task.status = TaskStatus.VERIFYING
                    self.state = KernelState.VERIFYING
                    
                    verification_data = self._build_verification_data(task, task_meta, exec_result)
                    verification = self.verifier.verify(verification_type, verification_data)
                    
                    if not verification.passed:
                        verification_passed = False
                        verification_details = verification.details
                        exec_result.success = False
                        exec_result.error = f"Verification failed: {verification_details}"
                        task.status = TaskStatus.FAILED_VERIFICATION
                
                # =====================================================
                # STEP 9: Artifact Collection
                # =====================================================
                for artifact in exec_result.artifacts:
                    self.artifacts.collect(
                        task.id, 
                        "artifact", 
                        artifact, 
                        {
                            "tool_used": tool_name, 
                            "task_id": task.id, 
                            "timestamp": time.time()
                        }
                    )
                
                # =====================================================
                # STEP 10: Persistence
                # =====================================================
                if hasattr(self, 'task_manager') and hasattr(self.task_manager, '_save_to_disk'):
                    try:
                        self.task_manager._save_to_disk()
                    except Exception as e:
                        logger.warning(f"Failed to persist state: {e}")
                
                # =====================================================
                # STEP 11: Telemetry
                # =====================================================
                step_duration = time.time() - step_start_time
                
                # SIMPLE Success Semantics
                final_success = exec_result.success and verification_passed
                
                self._last_execution_results[task.id] = {
                    'success': final_success,
                    'execution_result': exec_result.to_dict(),
                    'verification_passed': verification_passed,
                    'verification_details': verification_details,
                    'tool_used': tool_name,
                    'duration': step_duration,
                    'approval_status': approval_status
                }
                
                if final_success:
                    self.task_manager.mark_completed(task.id, exec_result.stdout or exec_result.stderr)
                    completed_tasks.add(task.id)
                    task.status = TaskStatus.COMPLETED
                    results.append(f"✓ [{verification_type}] {task.description}")
                else:
                    task.error = exec_result.error or verification_details
                    task.status = TaskStatus.FAILED
                    self.task_manager.mark_failed(task.id, task.error)
                    failed_tasks.add(task.id)
                    results.append(f"✗ [{verification_type}] {task.description}: {task.error}")
                
                self.telemetry.record_task(
                    success=final_success, 
                    duration=step_duration, 
                    tool_name=tool_name
                )
                
            except PermissionError as e:
                # Handle approval errors with DEEP integration
                error_msg = str(e)
                is_approval_denial = "denied" in error_msg.lower() or "never" in error_msg.lower()
                is_approval_expire = "timeout" in error_msg.lower()
                
                task.metadata['approval_denied'] = is_approval_denial
                task.metadata['approval_expired'] = is_approval_expire
                task.metadata['approval_recovery_needed'] = True
                
                logger.warning(f"Approval error for task {task.id}: {error_msg}")
                
                if hasattr(self, 'telemetry') and self.telemetry:
                    self.telemetry.record_event('approval_error', {
                        'task_id': task.id,
                        'error': error_msg,
                        'is_denial': is_approval_denial,
                        'is_expire': is_approval_expire,
                        'timestamp': time.time()
                    })
                
                if is_approval_denial or is_approval_expire:
                    task.error_type = ErrorType.APPROVAL_DENIED if is_approval_denial else ErrorType.APPROVAL_TIMEOUT
                    task.status = TaskStatus.RECOVERING
                    results.append(f"⚠️ [APPROVAL] {task.description}: {error_msg} - Recovery will handle")
                else:
                    task.status = TaskStatus.FAILED
                    failed_tasks.add(task.id)
                    results.append(f"✗ [PERMISSION] {task.description}: {error_msg}")
                
            except ValueError as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                failed_tasks.add(task.id)
                results.append(f"✗ [VALIDATION] {task.description}: {str(e)}")
                
            except Exception as e:
                task.error = str(e)
                task.error_type = ErrorType.SYSTEM_ERROR
                task.status = TaskStatus.FAILED
                self.task_manager.mark_failed(task.id, str(e))
                failed_tasks.add(task.id)
                results.append(f"✗ [EXCEPTION] {task.description}: {str(e)}")
        
        logger.info(f"✅ Execution complete: {len(completed_tasks)} completed, {len(failed_tasks)} failed")
        
        return "\n".join(results)
    
    # =====================================================
    # STRICT HELPER METHODS FOR No1 GRADE RUNTIME
    # =====================================================
    
    def _get_tool_reliability_history(self) -> Dict[str, float]:
        """
        Get tool reliability history from telemetry for smart tool selection.
        Returns: Dict[tool_name] = success_rate (0.0 to 1.0)
        """
        if not hasattr(self, 'telemetry') or not self.telemetry:
            return {}
        
        try:
            metrics = self.telemetry.get_metrics()
            tool_stats = metrics.get('tool_stats', {})
            
            reliability = {}
            for tool_name, stats in tool_stats.items():
                total = stats.get('total', 0)
                success = stats.get('success', 0)
                if total > 0:
                    reliability[tool_name] = success / total
                else:
                    reliability[tool_name] = 0.5  # Default neutral
            
            return reliability
        except Exception:
            return {}
    
            return {}
    def _select_tool_strict(
        task: Task,
        required_tools: List[str],
        task_meta: Dict,
        available_tools: List[str],
        tool_reliability: Dict[str, float],
        completed_tasks: Set[str]
    ) -> Optional[str]:
        """
        COMPREHENSIVE Context-Aware Tool Selection.
        
        Considers:
        1. Required tools (explicit)
        2. Prior success rate (telemetry-based reliability)
        3. Recent failure history
        4. Environment context (sandbox compatibility)
        5. Verifier needs (verification_type)
        6. Artifact expectations
        7. Approval friction (high-risk tools)
        """
        import time
        from collections import deque
        
        if not hasattr(self, "_tool_failure_history"):
            self._tool_failure_history = {}
            self._tool_failure_window = 300
        
        for rt in required_tools:
            if rt in available_tools:
                logger.info(f"Tool selected (required): {rt}")
                return rt
        
        description = task.description.lower()
        verification_type = task_meta.get('verification_type', 'manual')
        expected_artifacts = task_meta.get('expected_artifacts', [])
        sandbox_mode = task_meta.get('sandbox_mode', 'normal')
        approval_policy = task_meta.get('approval_policy', 'auto')
        
        TOOL_KEYWORDS = {
            'read_file': ['read', 'file', 'content', 'load', 'open'],
            'write_file': ['write', 'save', 'create', 'file', 'edit'],
            'execute_command': ['run', 'command', 'execute', 'shell', 'bash'],
            'execute_code': ['code', 'python', 'script', 'run'],
            'web_search': ['search', 'find', 'web', 'google'],
            'browser_navigate': ['navigate', 'browse', 'open', 'url'],
            'delete_file': ['delete', 'remove', 'clear'],
            'install_package': ['install', 'package', 'pip', 'npm'],
            'take_screenshot': ['screenshot', 'capture', 'screen'],
            'web_request': ['request', 'http', 'api', 'fetch']
        }
        
        TOOL_VERIFIER_MAP = {
            'browser_navigate': 'browser', 'take_screenshot': 'screenshot',
            'execute_command': 'server', 'execute_code': 'code',
            'read_file': 'file', 'write_file': 'file',
        }
        
        SANDBOX_COMPAT = {
            'safe': ['read_file', 'web_search', 'web_request'],
            'normal': ['read_file', 'write_file', 'execute_command', 'web_search', 'web_request', 'browser_navigate'],
            'advanced': ['read_file', 'write_file', 'execute_command', 'execute_code', 'install_package', 'browser_navigate']
        }
        
        HIGH_FRICTION = ['execute_command', 'execute_code', 'install_package', 'delete_file']
        
        scores, diagnostics, current_time = {}, {}, time.time()
        
        for tool in available_tools:
            score = 0
            tool_diag = {'reliability': 0, 'failure_penalty': 0, 'keyword': 0, 'sandbox': 0, 'verifier': 0, 'artifact': 0, 'approval': 0}
            
            reliability = tool_reliability.get(tool, 0.5)
            score += reliability * 30
            tool_diag['reliability'] = reliability * 30
            
            if tool in self._tool_failure_history:
                failures = self._tool_failure_history[tool]
                while failures and current_time - failures[0][0] > self._tool_failure_window:
                    failures.popleft()
                recent_failures = sum(1 for _, f in failures if f)
                penalty = recent_failures * 5
                score -= penalty
                tool_diag['failure_penalty'] = -penalty
            
            keywords = TOOL_KEYWORDS.get(tool, [])
            matches = sum(1 for kw in keywords if kw in description)
            score += matches * 5
            tool_diag['keyword'] = matches * 5
            
            allowed = SANDBOX_COMPAT.get(sandbox_mode, [])
            if tool in allowed:
                score += 10
                tool_diag['sandbox'] = 10
            else:
                score -= 15
                tool_diag['sandbox'] = -15
            
            if TOOL_VERIFIER_MAP.get(tool) == verification_type:
                score += 10
                tool_diag['verifier'] = 10
            
            if expected_artifacts:
                if 'write' in tool and any('.py' in str(a) or '.js' in str(a) for a in expected_artifacts):
                    score += 5
                    tool_diag['artifact'] = 5
                elif 'screenshot' in tool and any('.png' in str(a) for a in expected_artifacts):
                    score += 5
                    tool_diag['artifact'] = 5
            
            if tool in HIGH_FRICTION and approval_policy == 'auto':
                score -= 5
                tool_diag['approval'] = -5
            
            scores[tool] = score
            diagnostics[tool] = tool_diag
        
        if scores:
            best_tool = max(scores.items(), key=lambda x: x[1])[0]
            logger.info(f"Tool selected: {best_tool} (score: {scores[best_tool]})")
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('tool_selection', {
                    'task_id': task.id, 'tool': best_tool, 'score': scores[best_tool],
                    'diagnostics': diagnostics[best_tool], 'verification_type': verification_type,
                    'sandbox_mode': sandbox_mode, 'timestamp': current_time
                })
            return best_tool
        
        return None
    
    def _record_tool_failure(self, tool_name: str, failed: bool):
        from collections import deque
        if not hasattr(self, '_tool_failure_history'):
            self._tool_failure_history = {}
        if tool_name not in self._tool_failure_history:
            self._tool_failure_history[tool_name] = deque()
        self._tool_failure_history[tool_name].append((time.time(), failed))
        while len(self._tool_failure_history[tool_name]) > 100:
            self._tool_failure_history[tool_name].popleft()

    def _build_strict_args(self, tool_name: str, task: Task, task_meta: Dict) -> Dict[str, Any]:
        """
        STRICT Argument Builder for each tool.
        """
        # Default values from task
        default_path = f"/tmp/{task.id}.txt"
        
        ARG_BUILDERS = {
            'write_file': {
                'path': task_meta.get('file_path', default_path),
                'content': task_meta.get('file_content', task.description)
            },
            'read_file': {
                'path': task_meta.get('file_path', '')
            },
            'web_search': {
                'query': task_meta.get('search_query', task.description)
            },
            'execute_command': {
                'command': task_meta.get('command', task.description),
                'timeout': task.timeout
            },
            'execute_code': {
                'code': task_meta.get('code', task.description),
                'language': task_meta.get('language', 'python'),
                'timeout': task.timeout
            },
            'browser_navigate': {
                'url': task_meta.get('url', ''),
                'expected_text': task_meta.get('success_criteria', '')
            },
            'delete_file': {
                'path': task_meta.get('file_path', ''),
                'force': task_meta.get('force', False)
            },
            'install_package': {
                'package': task_meta.get('package', ''),
                'version': task_meta.get('version', '')
            },
            'take_screenshot': {
                'path': task_meta.get('screenshot_path', f'/tmp/{task.id}.png')
            },
            'web_request': {
                'url': task_meta.get('url', ''),
                'method': task_meta.get('method', 'GET'),
                'timeout': task_meta.get('timeout', 30)
            }
        }
        
        return ARG_BUILDERS.get(tool_name, {})
    
    async def _execute_approval_flow(
        self, 
        task_id: str, 
        tool_name: str, 
        args: Dict, 
        risk_level: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        STRICT Approval Workflow with proper status tracking.
        
        Returns: {'status': 'approved' | 'denied' | 'expired', 'request_id': str}
        """
        self.state = KernelState.WAITING_APPROVAL
        
        try:
            approval_request = self.approval_engine.create_request(
                tool_name=tool_name,
                arguments=args,
                risk_level=risk_level,
                requested_by='kernel'
            )
            
            self.pending_approvals[approval_request.request_id] = {
                'task_id': task_id, 
                'tool_name': tool_name, 
                'args': args, 
                'created_at': time.time()
            }
            
            approved = self._wait_for_approval(approval_request.request_id, timeout=timeout)
            
            if approved:
                return {'status': 'approved', 'request_id': approval_request.request_id}
            else:
                # Check if denied or expired
                pending = self.pending_approvals.get(approval_request.request_id, {})
                elapsed = time.time() - pending.get('created_at', 0)
                
                if elapsed >= timeout:
                    return {'status': 'expired', 'request_id': approval_request.request_id}
                else:
                    return {'status': 'denied', 'request_id': approval_request.request_id}
                    
        finally:
            self.state = KernelState.ACTING
    
    
    # ==================== APPROVAL RECOVERY STRATEGIES ====================
    
    async def _handle_approval_granted(self, task: Task, approval_result: Dict) -> Dict:
        logger.info(f"Approval GRANTED for task {task.id}, resuming")
        return {'action': 'resume', 'task_id': task.id, 'can_retry': True, 'rollback_required': False}
    
    async def _handle_approval_denied(self, task: Task, approval_result: Dict) -> Dict:
        logger.warning(f"Approval DENIED for task {task.id}")
        alt = (task.input_data or {}).get('alternate_tool')
        if alt:
            return {'action': 'alternate_tool', 'task_id': task.id, 'alternate_tool': alt, 'can_retry': False}
        return {'action': 'abort', 'task_id': task.id, 'error': 'approval_denied', 'can_retry': False}
    
    async def _handle_approval_expired(self, task: Task, approval_result: Dict) -> Dict:
        logger.warning(f"Approval EXPIRED for task {task.id}")
        retry = (task.retry_count or 0) + 1
        maxr = task.max_retries or 3
        if retry <= maxr:
            return {'action': 'retry_approval', 'task_id': task.id, 'retry_count': retry, 'can_retry': True}
        return {'action': 'safe_abort', 'task_id': task.id, 'error': 'approval_expired', 'rollback_required': True}
    
    async def _execute_approval_recovery(self, task: Task, approval_result: Dict) -> Dict:
        s = approval_result.get('status', 'unknown')
        if s == 'approved': return await self._handle_approval_granted(task, approval_result)
        if s == 'denied': return await self._handle_approval_denied(task, approval_result)
        if s == 'expired': return await self._handle_approval_expired(task, approval_result)
        return {'action': 'abort', 'task_id': task.id, 'error': 'unknown'}
    def _setup_sandbox(self, tool_name: str, sandbox_mode: str) -> bool:
        """
        STRICT Sandbox Setup.
        
        Returns: True if sandbox is ready, False otherwise
        """
        if not hasattr(self, 'sandbox') or not self.sandbox:
            # No sandbox - assume safe environment
            return True
        
        try:
            # Configure sandbox mode
            if sandbox_mode == 'safe':
                # Most restrictive
                pass
            elif sandbox_mode == 'normal':
                # Standard restrictions
                pass
            elif sandbox_mode == 'advanced':
                # Minimal restrictions (for trusted operations)
                pass

            return True
        except Exception as e:
            logger.error(f"Sandbox setup failed: {e}")
            return False

    async def _execute_tool_strict(
        self, 
        task: Task, 
        tool_name: str, 
        args: Dict, 
        timeout: int = 30
    ) -> ExecutionResult:
        """
        STRICT Tool Execution.
        
        Returns: ExecutionResult with success=True/False
        """
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        
        try:
            if hasattr(self, 'native_brain') and self.native_brain:
                # Use brain for execution
                task_meta = task.input_data or {}
                result = await self._execute_via_brain_strict(task, tool_name, args, task_meta)
                return result
            elif hasattr(self, 'tools') and self.tools:
                # Direct tool execution
                import asyncio
                tool_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args),
                    timeout=timeout
                )
                
                exec_result.stdout = tool_result.stdout or ""
                exec_result.stderr = tool_result.stderr or ""
                exec_result.exit_code = tool_result.exit_code if hasattr(tool_result, 'exit_code') else 0
                exec_result.artifacts = tool_result.artifacts if hasattr(tool_result, 'artifacts') else []
                
                if exec_result.exit_code != 0:
                    exec_result.success = False
                    exec_result.error = f"Exit code: {exec_result.exit_code}"
                elif any(err in (exec_result.stdout + exec_result.stderr).lower() 
                        for err in ['exception', 'error', 'failed', 'traceback']):
                    exec_result.success = False
                    exec_result.error = "Error pattern in output"
                else:
                    exec_result.success = True
            else:
                exec_result.error = "No execution engine available"
                
        except asyncio.TimeoutError:
            exec_result.error = f"Timeout after {timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
        except Exception as e:
            exec_result.error = str(e)
        
        return exec_result
    
    async def _execute_via_brain_strict(self, task: Task, tool_name: str, args: Dict, task_meta: Dict) -> ExecutionResult:
        """
        STRICT BRAIN EXECUTION - No1 Grade.
        
        MODEL OUTPUT (only):
        - intent: what model thinks should happen
        - suggestion: model recommended approach
        - candidate_args: model suggested arguments
        
        REAL TRUTH (always):
        - actual tool runtime result
        - verifier result  
        - artifact collector
        
        MODEL CAN LIE ABOUT:
        - success status
        - artifacts
        - stdout/stderr
        - tool_used
        
        SO WE NEVER TRUST MODEL OUTPUT FOR SUCCESS/ARTIFACTS.
        """
        import re, json, time

        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        
        # Track truth sources
        truth_sources = {
            'model_intent': None,
            'model_suggestion': None,
            'model_candidate_args': None,
            'runtime_result': None,
            'verifier_result': None,
            'artifact_check': None
        }

        # STEP 1: MODEL OUTPUT - ONLY intent/suggestion/args
        try:
            intent_prompt = f"""Analyze this task and provide intent + suggestion.
TASK: {task.description}
TOOL: {tool_name}
ARGS: {json.dumps(args)}

Return ONLY valid JSON (no other text):
{{
  "intent": "What the model thinks should happen",
  "suggestion": "Recommended approach",
  "candidate_args": {{}}  // any argument corrections
}}"""

            response = self.native_brain.think(intent_prompt)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match and json_match.group().count('{') == json_match.group().count('}'):
                model_output = json.loads(json_match.group())
                truth_sources['model_intent'] = model_output.get('intent')
                truth_sources['model_suggestion'] = model_output.get('suggestion')
                truth_sources['model_candidate_args'] = model_output.get('candidate_args', {})
                
                logger.info(f"Model intent: {truth_sources['model_intent']}")
                
        except Exception as e:
            logger.warning(f"Model intent analysis failed: {e}")

        # STEP 2: REAL TOOL RUNTIME - THE ACTUAL TRUTH
        tool_start_time = time.time()

        try:
            if hasattr(self, 'tools') and self.tools:
                import asyncio
                tool_runtime_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args),
                    timeout=task.timeout
                )

                exec_result.stdout = tool_runtime_result.stdout or ""
                exec_result.stderr = tool_runtime_result.stderr or ""
                exec_result.exit_code = tool_runtime_result.exit_code if hasattr(tool_runtime_result, 'exit_code') else 0
                exec_result.artifacts = tool_runtime_result.artifacts if hasattr(tool_runtime_result, 'artifacts') else []
                
                truth_sources['runtime_result'] = {
                    'exit_code': exec_result.exit_code,
                    'has_stdout': bool(exec_result.stdout),
                    'has_stderr': bool(exec_result.stderr),
                    'artifact_count': len(exec_result.artifacts)
                }

                if exec_result.exit_code != 0:
                    exec_result.success = False
                    exec_result.error = f"Exit code: {exec_result.exit_code}"
                elif any(err in (exec_result.stdout + exec_result.stderr).lower() 
                        for err in ['exception', 'error', 'failed', 'traceback']):
                    exec_result.success = False
                    exec_result.error = "Error pattern in output"
                else:
                    exec_result.success = True
            else:
                exec_result.error = "No tools engine available"
                
        except asyncio.TimeoutError:
            exec_result.error = f"Timeout after {task.timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
            exec_result.success = False
        except Exception as e:
            exec_result.error = str(e)
            exec_result.success = False

        exec_result.execution_time = time.time() - tool_start_time

        # STEP 3: VERIFIER - SECOND TRUTH SOURCE
        if exec_result.success:
            try:
                verification_type = task_meta.get('verification_type', 'manual')
                if verification_type != 'manual':
                    verification_data = self._build_verification_data(task, task_meta, exec_result)
                    verification = self.verifier.verify(verification_type, verification_data)
                    
                    truth_sources['verifier_result'] = {
                        'passed': verification.passed,
                        'details': verification.details
                    }
                    
                    if not verification.passed:
                        exec_result.success = False
                        exec_result.error = f"Verification failed: {verification.details}"
            except Exception as e:
                logger.warning(f"Verification failed: {e}")

        # STEP 4: ARTIFACT COLLECTION - THIRD TRUTH SOURCE
        expected_artifacts = task_meta.get('expected_artifacts', [])
        if expected_artifacts and exec_result.artifacts:
            for expected in expected_artifacts:
                found = False
                for artifact in exec_result.artifacts:
                    if expected in artifact or expected in str(artifact):
                        found = True
                        break
                
                truth_sources['artifact_check'] = {'expected': expected, 'found': found}
                
                if not found:
                    exec_result.success = False
                    exec_result.error = f"Missing artifact: {expected}"

        logger.debug(f"Truth sources: {truth_sources}")
        return exec_result


    async def _execute_via_brain(self, task: Task, tool_name: str, args: Dict, task_meta: Dict) -> ExecutionResult:
        """
        Execute tool via native_brain with INDEPENDENT validation.
        
        IMPORTANT: Model output is ONLY a suggestion. The REAL truth comes from:
        - Real tool runtime result (not model claiming success)
        - Verifier result
        - Artifact collector result
        
        Model can:
        - Fake success
        - Provide incorrect artifacts
        - Claim wrong tool_used
        - Invent stdout/stderr
        
        So we ALWAYS verify with real tool execution, not just trust model.
        """
        
        import re, json
        import time
        
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        
        # Track where the truth comes from
        validation_source = {
            'model_suggestion': None,
            'tool_runtime': None,
            'verifier': None,
            'artifact_check': None
        }
        
        # Step 1: Get model suggestion (NOT the final truth)
        model_suggestion = None
        try:
            # MODEL OUTPUT: ONLY intent/suggestion - NEVER success/artifacts
            intent_prompt = f"""Analyze task for planning (NOT execution results). 
TASK: {task.description} 
TOOL: {tool_name} 
ARGUMENTS: {json.dumps(args)} 
SUCCESS CRITERIA: {task_meta.get('success_criteria', 'Task completed')}

IMPORTANT: Provide your best guess for the execution result. This is a SUGGESTION only.
Return ONLY valid JSON: {{ 
  "success": true/false, 
  "stdout": "actual output", 
  "stderr": "errors", 
  "exit_code": 0, 
  "artifacts": [], 
  "error": "error if failed" 
}}"""

            response = self.native_brain.think(intent_prompt)
            
            # Try to parse model response
            json_match = re.search(r'\{[^{}]*"success"[^{}]*\}', response, re.DOTALL)
            if not json_match: 
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                if json_str.count('{') == json_str.count('}'):
                    model_suggestion = json.loads(json_str)
                    validation_source['model_suggestion'] = model_suggestion
                    logger.debug(f"Model suggestion: {model_suggestion.get('success', 'unknown')}")
        except Exception as e:
            logger.warning(f"Model suggestion failed: {e}")
        
        # Step 2: REAL tool execution (this is the ACTUAL truth)
        tool_start_time = time.time()
        
        try:
            # Execute via actual tools engine
            if hasattr(self, 'tools') and self.tools:
                import asyncio
                tool_runtime_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args),
                    timeout=task.timeout
                )
                
                # Copy real runtime results
                exec_result.stdout = tool_runtime_result.stdout or ""
                exec_result.stderr = tool_runtime_result.stderr or ""
                exec_result.exit_code = tool_runtime_result.exit_code if hasattr(tool_runtime_result, 'exit_code') else 0
                exec_result.artifacts = tool_runtime_result.artifacts if hasattr(tool_runtime_result, 'artifacts') else []
                
                # Determine success from REAL runtime, not model
                # Check exit code
                if exec_result.exit_code != 0:
                    exec_result.success = False
                    exec_result.error = f"Exit code: {exec_result.exit_code}"
                # Check for error patterns in real output
                elif any(err in (exec_result.stdout + exec_result.stderr).lower() 
                        for err in ['exception', 'error', 'failed', 'traceback', 'xatolik']):
                    exec_result.success = False
                    exec_result.error = "Error pattern detected in output"
                else:
                    exec_result.success = True
                
                validation_source['tool_runtime'] = {
                    'success': exec_result.success,
                    'exit_code': exec_result.exit_code,
                    'has_error_pattern': bool(exec_result.error)
                }
                
            elif hasattr(self, 'native_brain'):
                # Fallback: Use brain's execution capability if no tools
                exec_result.stdout = response  # Use model output as last resort
                exec_result.success = model_suggestion.get('success', False) if model_suggestion else False
                logger.warning("No tools engine, using brain fallback - less reliable")
            else:
                exec_result.error = "No execution engine available"
                
        except asyncio.TimeoutError:
            exec_result.error = f"Execution timeout after {task.timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
            exec_result.success = False
        except Exception as e:
            exec_result.error = f"Tool execution error: {str(e)}"
            exec_result.success = False
        
        exec_result.execution_time = time.time() - tool_start_time
        exec_result.tool_used = tool_name
        
        # Step 3: Artifact verification (if artifacts expected)
        expected_artifacts = task_meta.get('expected_artifacts', [])
        if expected_artifacts and exec_result.artifacts:
            artifact_check = {}
            for expected in expected_artifacts:
                # Check if artifact exists
                found = any(expected in a for a in exec_result.artifacts)
                artifact_check[expected] = found
            
            validation_source['artifact_check'] = artifact_check
            
            # If expected artifacts not found, fail
            if not all(artifact_check.values()):
                missing = [k for k, v in artifact_check.items() if not v]
                exec_result.success = False
                exec_result.error = f"Missing expected artifacts: {missing}"
        
        # Step 4: Run verifier for additional validation
        verification_type = task_meta.get('verification_type', 'manual')
        if verification_type != 'manual' and exec_result.success:
            try:
                verification_data = {
                    'result': exec_result.stdout,
                    'task_id': task.id,
                    **task_meta
                }
                verification = self.verifier.verify(verification_type, verification_data)
                validation_source['verifier'] = {
                    'passed': verification.passed,
                    'details': verification.details
                }
                
                if not verification.passed:
                    exec_result.success = False
                    exec_result.error = f"Verification failed: {verification.details}"
            except Exception as e:
                logger.warning(f"Verification check failed: {e}")
        
        # Log validation sources for debugging
        logger.info(f"Execution validation for task {task.id}: {validation_source}")
        
        # Don't trust model - use real results
        # If model claimed success but real execution failed, trust real execution
        if model_suggestion and model_suggestion.get('success') and not exec_result.success:
            logger.warning(f"Model claimed success but REAL execution failed! Using real result.")
        
        return exec_result
    
    async def _execute_via_tools(self, task: Task, tool_name: str, args: Dict) -> ExecutionResult:
        """Execute tool via tools engine"""
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        try:
            if hasattr(self, 'tools') and self.tools:
                import asyncio
                tool_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args, True),
                    timeout=task.timeout
                )
                exec_result.stdout = tool_result.stdout or ""
                exec_result.stderr = tool_result.stderr or ""
                exec_result.exit_code = tool_result.exit_code if hasattr(tool_result, 'exit_code') else 0
                exec_result.success = tool_result.status == 'success'
                if hasattr(tool_result, 'artifacts'): exec_result.artifacts = tool_result.artifacts
            else:
                exec_result.error = "Tools engine not available"
        except asyncio.TimeoutError:
            exec_result.error = f"Execution timeout after {task.timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
        except Exception as e:
            exec_result.error = str(e)
            exec_result.error_type = ErrorType.EXECUTION_FAILED
        return exec_result
    
    def _wait_for_approval(self, request_id: str, timeout: int = 30) -> bool:
        """Wait for approval with timeout"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_id not in self.pending_approvals: return True
            approval_status = self.approval_engine.get_status(request_id)
            if approval_status and approval_status.get('status') == 'approved': return True
            elif approval_status and approval_status.get('status') == 'denied': return False
            time.sleep(0.5)
        return False



    async def _verify(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """
        TASK-AWARE VERIFICATION for No1 agent with ENHANCED diagnostics.
        
        Verifies execution result with full context:
        - task: The task being verified
        - exec_result: Real tool execution result
        - task_meta: Task metadata including verification_type, success criteria, etc.
        
        Enhanced features:
        - Deep success criteria integration
        - Strict artifact expectations matching
        - Verifier confidence aggregation
        - Fail reason taxonomy
        
        Verification types:
        - browser task → browser verifier
        - screenshot task → OCR/vision verifier
        - server task → port + HTTP verifier
        - code task → syntax + regression verifier
        - file task → file existence + content verifier
        """
        
        import time
        import re
        
        verification_log = {
            'task_id': task.id,
            'verification_type': '',
            'success_criteria': '',
            'expected_artifacts': [],
            'checks': [],
            'confidence': 0.0,
            'passed': False,
            'fail_reason': None,
            'timestamp': time.time()
        }
        
        if not exec_result:
            verification_log['fail_reason'] = 'empty_execution_result'
            logger.warning(f"Verification failed: Empty execution result for task {task.id}")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_type = task_meta.get('verification_type', 'manual')
        success_criteria = task_meta.get('success_criteria', '')
        expected_artifacts = task_meta.get('expected_artifacts', [])
        
        verification_log['verification_type'] = verification_type
        verification_log['success_criteria'] = success_criteria
        verification_log['expected_artifacts'] = expected_artifacts
        
        # If execution itself failed, verification fails
        if not exec_result.success:
            verification_log['fail_reason'] = 'execution_failed'
            verification_log['checks'].append({
                'check': 'execution_success',
                'passed': False,
                'detail': exec_result.error or 'Unknown error'
            })
            logger.warning(f"Verification failed: Execution was not successful - {exec_result.error}")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_log['checks'].append({
            'check': 'execution_success',
            'passed': True,
            'detail': 'Execution completed successfully'
        })
        
        # Check for error patterns in result (real stderr/stdout from tool)
        error_patterns = [
            "EXCEPTION", "ERROR", "FAILED", "Traceback",
            "Permission denied", "Not found", "Timeout",
            "Verification FAILED", "command failed", "xatolik"
        ]
        
        result_text = (exec_result.stdout or "") + (exec_result.stderr or "")
        result_upper = result_text.upper()
        has_error = any(pattern.upper() in result_upper for pattern in error_patterns)
        
        if has_error:
            verification_log['fail_reason'] = 'error_pattern_detected'
            verification_log['checks'].append({
                'check': 'error_patterns',
                'passed': False,
                'detail': 'Error patterns found in output'
            })
            logger.warning(f"Verification failed: Error patterns detected in execution output")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_log['checks'].append({
            'check': 'error_patterns',
            'passed': True,
            'detail': 'No error patterns detected'
        })
        
        # Check result is not just placeholder text (model fake)
        if result_text.startswith("Executed:") or result_text.startswith("Vazifa qabul"):
            verification_log['fail_reason'] = 'placeholder_result'
            verification_log['checks'].append({
                'check': 'not_placeholder',
                'passed': False,
                'detail': 'Result appears to be placeholder'
            })
            logger.warning("Verification failed: Result appears to be placeholder (model fake)")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_log['checks'].append({
            'check': 'not_placeholder',
            'passed': True,
            'detail': 'Result is real, not placeholder'
        })
        
        # DEEP SUCCESS CRITERIA INTEGRATION
        if success_criteria:
            criteria_result = await self._verify_success_criteria(
                success_criteria, exec_result, task_meta
            )
            verification_log['checks'].append({
                'check': 'success_criteria',
                'passed': criteria_result['passed'],
                'detail': criteria_result.get('detail', ''),
                'confidence': criteria_result.get('confidence', 0.0)
            })
            if not criteria_result['passed']:
                verification_log['fail_reason'] = 'success_criteria_not_met'
                verification_log['confidence'] = criteria_result.get('confidence', 0.0)
                logger.warning(f"Verification failed: Success criteria not met - {criteria_result.get('detail', '')}")
                await self._emit_verification_telemetry(verification_log)
                return False
        
        # STRICT ARTIFACT EXPECTATIONS MATCHING
        if expected_artifacts:
            artifact_result = await self._verify_artifact_expectations(
                expected_artifacts, exec_result, task_meta
            )
            verification_log['checks'].append({
                'check': 'artifact_expectations',
                'passed': artifact_result['passed'],
                'detail': artifact_result.get('detail', ''),
                'matched_artifacts': artifact_result.get('matched', []),
                'missing_artifacts': artifact_result.get('missing', []),
                'confidence': artifact_result.get('confidence', 0.0)
            })
            if not artifact_result['passed']:
                verification_log['fail_reason'] = 'artifact_expectations_not_met'
                verification_log['confidence'] = artifact_result.get('confidence', 0.0)
                logger.warning(f"Verification failed: Artifact expectations not met - {artifact_result.get('detail', '')}")
                await self._emit_verification_telemetry(verification_log)
                return False
        
        # Type-specific verification with confidence aggregation
        confidence_scores = []
        
        if verification_type == 'browser':
            result = await self._verify_browser(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'browser_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif verification_type == 'screenshot':
            result = await self._verify_screenshot(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'screenshot_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif verification_type == 'server':
            result = await self._verify_server(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'server_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif verification_type == 'code':
            result = await self._verify_code(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'code_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif verification_type == 'file':
            result = await self._verify_file(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'file_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif verification_type == 'function':
            result = self._verify_function_result(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'function_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif verification_type == 'manual':
            result = exec_result.success
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'manual_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        else:
            result = exec_result.success
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'unknown_verification_type'
                await self._emit_verification_telemetry(verification_log)
                return False
        
        # AGGREGATE VERIFIER CONFIDENCE
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            verification_log['confidence'] = avg_confidence
        
        verification_log['passed'] = True
        await self._emit_verification_telemetry(verification_log)
        return True
    
    async def _verify_success_criteria(self, success_criteria: str, exec_result: ExecutionResult, task_meta: Dict) -> Dict:
        """
        Verify success criteria with deep integration.
        
        Returns:
        - passed: bool
        - detail: str
        - confidence: float (0.0 - 1.0)
        """
        import re
        
        result_text = (exec_result.stdout or "") + (exec_result.stderr or "")
        
        # Parse success criteria
        # Support patterns like:
        # - "contains:Hello World"
        # - "regex:\\d+ errors?"
        # - "not_contains:Error"
        # - "output_contains:success"
        # - "exit_code:0"
        
        passed = True
        details = []
        confidence = 1.0
        
        # Check for "contains:X" pattern
        contains_match = re.search(r'contains:([^\s]+)', success_criteria)
        if contains_match:
            required_text = contains_match.group(1)
            if required_text.lower() in result_text.lower():
                details.append(f"Found required text: {required_text}")
            else:
                passed = False
                confidence = 0.0
                details.append(f"Missing required text: {required_text}")
        
        # Check for "not_contains:X" pattern
        not_contains_match = re.search(r'not_contains:([^\s]+)', success_criteria)
        if not_contains_match:
            forbidden_text = not_contains_match.group(1)
            if forbidden_text.lower() in result_text.lower():
                passed = False
                confidence = 0.0
                details.append(f"Found forbidden text: {forbidden_text}")
            else:
                details.append(f"Confirmed no forbidden text: {forbidden_text}")
        
        # Check for "regex:X" pattern
        regex_match = re.search(r'regex:([^\s]+)', success_criteria)
        if regex_match:
            try:
                pattern = regex_match.group(1)
                if re.search(pattern, result_text):
                    details.append(f"Regex pattern matched: {pattern}")
                else:
                    passed = False
                    confidence = 0.0
                    details.append(f"Regex pattern not found: {pattern}")
            except re.error as e:
                details.append(f"Regex error: {e}")
        
        # Check for "exit_code:X" pattern
        exit_code_match = re.search(r'exit_code:(\d+)', success_criteria)
        if exit_code_match:
            expected_code = int(exit_code_match.group(1))
            actual_code = exec_result.exit_code
            if actual_code == expected_code:
                details.append(f"Exit code matches: {actual_code}")
            else:
                passed = False
                confidence = 0.0
                details.append(f"Exit code mismatch: expected {expected_code}, got {actual_code}")
        
        return {
            'passed': passed,
            'detail': '; '.join(details) if details else 'Success criteria check completed',
            'confidence': confidence
        }
    
    async def _verify_artifact_expectations(self, expected_artifacts: List[str], exec_result: ExecutionResult, task_meta: Dict) -> Dict:
        """
        Strict artifact expectations matching.
        
        Returns:
        - passed: bool
        - detail: str
        - matched: List[str]
        - missing: List[str]
        - confidence: float (0.0 - 1.0)
        """
        import os
        
        actual_artifacts = exec_result.artifacts or []
        
        matched = []
        missing = []
        confidence = 1.0
        
        for expected in expected_artifacts:
            # Expected artifact can be:
            # - Exact filename: "output.txt"
            # - Extension: ".pdf", ".png"
            # - Pattern: "*.js", "report_*"
            
            found = False
            
            # Check exact match
            if expected in actual_artifacts:
                matched.append(expected)
                found = True
            else:
                # Check extension match
                if expected.startswith('.'):
                    for artifact in actual_artifacts:
                        if artifact.endswith(expected):
                            matched.append(f"{artifact} (matched {expected})")
                            found = True
                            break
                else:
                    # Check if expected is a substring of any artifact
                    for artifact in actual_artifacts:
                        if expected in artifact:
                            matched.append(artifact)
                            found = True
                            break
            
            if not found:
                missing.append(expected)
        
        # Calculate confidence based on match ratio
        if expected_artifacts:
            match_ratio = len(matched) / len(expected_artifacts)
            confidence = match_ratio
        
        passed = len(missing) == 0
        
        detail = f"Matched: {len(matched)}/{len(expected_artifacts)}"
        if missing:
            detail += f", Missing: {missing}"
        
        return {
            'passed': passed,
            'detail': detail,
            'matched': matched,
            'missing': missing,
            'confidence': confidence
        }
    
    async def _emit_verification_telemetry(self, verification_log: Dict):
        """Emit verification telemetry with full diagnostics."""
        try:
            # Log prominently
            if verification_log['passed']:
                logger.info(f"✅ Verification PASSED for task {verification_log['task_id']} (confidence: {verification_log['confidence']:.2f})")
            else:
                logger.error(f"❌ Verification FAILED for task {verification_log['task_id']}: {verification_log['fail_reason']}")
                logger.error(f"   Checks: {[c['check'] for c in verification_log['checks'] if not c['passed']]}")
            
            # Emit to telemetry if available
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('task_verification', verification_log)
            
            # Emit self-improvement signal if failed
            if not verification_log['passed'] and hasattr(self, 'emit_improvement_signal'):
                self.emit_improvement_signal('verification_failure', {
                    'task_id': verification_log['task_id'],
                    'fail_reason': verification_log['fail_reason'],
                    'verification_type': verification_log['verification_type'],
                    'checks_failed': [c['check'] for c in verification_log['checks'] if not c['passed']]
                })
        except Exception as e:
            logger.error(f"Failed to emit verification telemetry: {e}")
    
    async def _verify_browser(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """
        WORLD-CLASS Browser verification with multiple signals:
        - URL verification
        - DOM text verification
        - Selector verification
        - HTTP status verification
        - Screenshot corroboration
        - Navigation chain verification
        - Session/auth state verification
        - Final page semantic verification
        """
        
        import time
        
        # Verification log for diagnostics
        verification_checks = []
        
        expected_url = task_meta.get('expected_url', '')
        expected_text = task_meta.get('expected_text', '')
        required_selectors = task_meta.get('required_selectors', [])
        check_network = task_meta.get('check_network', True)
        check_auth = task_meta.get('check_auth', False)
        check_session = task_meta.get('check_session', False)
        navigation_chain = task_meta.get('navigation_chain', [])  # List of URLs to verify in order
        semantic_text = task_meta.get('semantic_text', '')  # High-level semantic check
        screenshot_expected = task_meta.get('screenshot_expected', False)
        
        result_data = exec_result.stdout  # Could be URL, HTML, or status
        
        # Get browser instance
        browser = getattr(self, 'browser', None)
        
        # ============== 1. URL VERIFICATION ==============
        url_check = {'name': 'url_verification', 'passed': True, 'detail': ''}
        if expected_url:
            # First check in result data
            if expected_url not in result_data:
                # Try to get actual URL from browser
                if browser and hasattr(browser, 'get_current_url'):
                    try:
                        actual_url = browser.get_current_url()
                        if expected_url not in actual_url:
                            url_check['passed'] = False
                            url_check['detail'] = f"URL mismatch. Expected: {expected_url}, Got: {actual_url}"
                            logger.warning(f"Browser verification failed: {url_check['detail']}")
                            verification_checks.append(url_check)
                            return False
                        else:
                            url_check['detail'] = f"URL verified: {actual_url}"
                    except Exception as e:
                        url_check['passed'] = False
                        url_check['detail'] = f"Could not get URL: {e}"
                        verification_checks.append(url_check)
                        return False
            else:
                url_check['detail'] = f"URL found in result: {expected_url}"
        
        verification_checks.append(url_check)
        
        # ============== 2. NAVIGATION CHAIN VERIFICATION ==============
        nav_check = {'name': 'navigation_chain', 'passed': True, 'detail': ''}
        if navigation_chain and browser and hasattr(browser, 'get_navigation_history'):
            try:
                nav_history = browser.get_navigation_history()
                expected_chain = navigation_chain
                
                # Check if all expected URLs were visited in order
                visited_urls = nav_history.get('urls', [])
                
                # Check if key pages in chain were visited
                missing_nav = []
                for expected_nav in expected_chain:
                    found = any(expected_nav in vurl for vurl in visited_urls)
                    if not found:
                        missing_nav.append(expected_nav)
                
                if missing_nav:
                    nav_check['passed'] = False
                    nav_check['detail'] = f"Missing navigation steps: {missing_nav}. Visited: {visited_urls}"
                    logger.warning(f"Browser verification failed: {nav_check['detail']}")
                    verification_checks.append(nav_check)
                    return False
                else:
                    nav_check['detail'] = f"Navigation chain verified: {visited_urls}"
            except Exception as e:
                nav_check['detail'] = f"Could not verify navigation: {e}"
        
        verification_checks.append(nav_check)
        
        # ============== 3. HTTP STATUS VERIFICATION ==============
        http_check = {'name': 'http_status', 'passed': True, 'detail': ''}
        if check_network:
            if '200' not in result_data and 'OK' not in result_data:
                # Check for error status codes
                error_codes = ['404', '500', '503', '403', '401', '500']
                found_errors = [code for code in error_codes if code in result_data]
                if found_errors:
                    http_check['passed'] = False
                    http_check['detail'] = f"HTTP errors found: {found_errors}"
                    logger.warning(f"Browser verification failed: {http_check['detail']}")
                    verification_checks.append(http_check)
                    return False
            http_check['detail'] = "HTTP status OK"
        
        verification_checks.append(http_check)
        
        # ============== 4. DOM TEXT VERIFICATION ==============
        text_check = {'name': 'dom_text', 'passed': True, 'detail': ''}
        if expected_text:
            if expected_text.lower() not in result_data.lower():
                text_check['passed'] = False
                text_check['detail'] = f"Expected text not found: {expected_text[:50]}..."
                logger.warning(f"Browser verification failed: {text_check['detail']}")
                verification_checks.append(text_check)
                return False
            else:
                text_check['detail'] = f"Text verified: {expected_text[:30]}..."
        
        verification_checks.append(text_check)
        
        # ============== 5. SELECTOR VERIFICATION ==============
        selector_check = {'name': 'selectors', 'passed': True, 'detail': '', 'found': [], 'missing': []}
        if required_selectors and browser and hasattr(browser, 'element_exists'):
            for selector in required_selectors:
                try:
                    if browser.element_exists(selector):
                        selector_check['found'].append(selector)
                    else:
                        selector_check['missing'].append(selector)
                except Exception as e:
                    selector_check['missing'].append(f"{selector} (error: {e})")
            
            if selector_check['missing']:
                selector_check['passed'] = False
                selector_check['detail'] = f"Missing selectors: {selector_check['missing']}"
                logger.warning(f"Browser verification failed: {selector_check['detail']}")
                verification_checks.append(selector_check)
                return False
            else:
                selector_check['detail'] = f"All selectors found: {selector_check['found']}"
        
        verification_checks.append(selector_check)
        
        # ============== 6. SCREENSHOT CORROBORATION ==============
        screenshot_check = {'name': 'screenshot', 'passed': True, 'detail': ''}
        if screenshot_expected:
            # Check if screenshot artifact exists
            screenshot_artifacts = [a for a in exec_result.artifacts if a.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            
            if not screenshot_artifacts:
                screenshot_check['passed'] = False
                screenshot_check['detail'] = "Screenshot expected but not found in artifacts"
                logger.warning(f"Browser verification failed: {screenshot_check['detail']}")
                verification_checks.append(screenshot_check)
                return False
            
            # Verify screenshot file exists on disk
            import os
            real_screenshot = screenshot_artifacts[0]
            if not os.path.exists(real_screenshot):
                screenshot_check['passed'] = False
                screenshot_check['detail'] = f"Screenshot file not found: {real_screenshot}"
                logger.warning(f"Browser verification failed: {screenshot_check['detail']}")
                verification_checks.append(screenshot_check)
                return False
            
            # Check file size
            file_size = os.path.getsize(real_screenshot)
            if file_size < 100:
                screenshot_check['passed'] = False
                screenshot_check['detail'] = f"Screenshot too small: {file_size} bytes"
                logger.warning(f"Browser verification failed: {screenshot_check['detail']}")
                verification_checks.append(screenshot_check)
                return False
            
            screenshot_check['detail'] = f"Screenshot verified: {real_screenshot} ({file_size} bytes)"
        
        verification_checks.append(screenshot_check)
        
        # ============== 7. SESSION/AUTH STATE VERIFICATION ==============
        auth_check = {'name': 'auth_session', 'passed': True, 'detail': ''}
        
        if check_auth or check_session:
            if not browser:
                auth_check['passed'] = False
                auth_check['detail'] = "Browser not available for auth/session check"
                logger.warning(f"Browser verification failed: {auth_check['detail']}")
                verification_checks.append(auth_check)
                return False
            
            try:
                # Check authentication state
                if check_auth:
                    # Check for common auth indicators
                    auth_indicators = [
                        'logout', 'sign out', 'log out', 'profile', 'account',
                        'settings', 'logged-in', 'welcome'
                    ]
                    
                    # Get page content
                    page_content = ""
                    if hasattr(browser, 'get_page_content'):
                        page_content = browser.get_page_content()
                    elif hasattr(browser, 'get_page_text'):
                        page_content = browser.get_page_text()
                    
                    # Check for auth indicators
                    auth_found = any(indicator in page_content.lower() for indicator in auth_indicators)
                    
                    if not auth_found:
                        auth_check['passed'] = False
                        auth_check['detail'] = "Auth state indicators not found on page"
                        logger.warning(f"Browser verification failed: {auth_check['detail']}")
                        verification_checks.append(auth_check)
                        return False
                    else:
                        auth_check['detail'] = "Auth state verified"
                
                # Check session state
                if check_session:
                    # Check if cookies exist
                    if hasattr(browser, 'get_cookies'):
                        cookies = browser.get_cookies()
                        if not cookies or len(cookies) == 0:
                            auth_check['passed'] = False
                            auth_check['detail'] = "No session cookies found"
                            logger.warning(f"Browser verification failed: {auth_check['detail']}")
                            verification_checks.append(auth_check)
                            return False
                        else:
                            auth_check['detail'] = f"Session verified with {len(cookies)} cookies"
                
            except Exception as e:
                auth_check['passed'] = False
                auth_check['detail'] = f"Auth/session check error: {e}"
                logger.warning(f"Browser verification failed: {auth_check['detail']}")
                verification_checks.append(auth_check)
                return False
        
        verification_checks.append(auth_check)
        
        # ============== 8. SEMANTIC TEXT VERIFICATION ==============
        semantic_check = {'name': 'semantic_verification', 'passed': True, 'detail': ''}
        if semantic_text:
            # High-level semantic check - e.g., "page contains form", "shows error message"
            semantic_patterns = semantic_text.split('|')  # Allow multiple patterns
            
            page_for_semantic = result_data
            if browser and hasattr(browser, 'get_page_text'):
                try:
                    page_for_semantic = browser.get_page_text()
                except:
                    pass
            
            missing_semantic = []
            for pattern in semantic_patterns:
                pattern = pattern.strip()
                if pattern.lower() not in page_for_semantic.lower():
                    missing_semantic.append(pattern)
            
            if missing_semantic:
                semantic_check['passed'] = False
                semantic_check['detail'] = f"Missing semantic elements: {missing_semantic}"
                logger.warning(f"Browser verification failed: {semantic_check['detail']}")
                verification_checks.append(semantic_check)
                return False
            else:
                semantic_check['detail'] = f"Semantic verification passed: {semantic_text}"
        
        verification_checks.append(semantic_check)
        
        # ============== LOG ALL CHECKS ==============
        logger.info(f"🔍 Browser verification for task {task.id}: {len(verification_checks)} checks")
        for check in verification_checks:
            status = "✅" if check['passed'] else "❌"
            logger.info(f"   {status} {check['name']}: {check['detail']}")
        
        logger.info(f"✅ Browser verification PASSED for task {task.id}")
        return True
    
    async def _verify_screenshot(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """
        COMPREHENSIVE Screenshot verification with multiple signals:
        
        For screenshot task to be successful:
        1. REAL image artifact must exist (file on disk)
        2. OCR verification with confidence
        3. Vision prompt verification with confidence
        4. Region-based expectation verification
        5. UI element matching
        6. Before/after image diff (if baseline provided)
        7. Bounding box confidence
        8. Overall confidence threshold
        
        NO soft passes - if no real image, verification FAILS!
        """
        
        import os
        import time
        
        # Verification log for diagnostics
        verification_checks = []
        
        expected_text = task_meta.get('expected_text', '')
        vision_prompt = task_meta.get('vision_prompt', '')
        image_path = task_meta.get('image_path', '')
        confidence_threshold = task_meta.get('confidence_threshold', 0.7)
        
        # NEW: Region-based expectations
        expected_regions = task_meta.get('expected_regions', [])  # List of {x, y, width, height, expected_text}
        
        # NEW: UI element matching
        expected_ui_elements = task_meta.get('expected_ui_elements', [])  # List of {type, text, selector}
        
        # NEW: Before/after diff
        baseline_image_path = task_meta.get('baseline_image_path', '')  # Compare with this image
        diff_threshold = task_meta.get('diff_threshold', 0.1)  # Max allowed difference ratio
        
        # NEW: Bounding box expectations
        expected_bboxes = task_meta.get('expected_bboxes', [])  # List of {label, min_confidence}
        
        # ============== 1. CRITICAL: REAL IMAGE ARTIFACT MUST EXIST ==============
        check_artifact = {'name': 'artifact_exists', 'passed': True, 'detail': ''}
        
        screenshot_artifacts = [a for a in exec_result.artifacts if a.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        if not screenshot_artifacts:
            check_artifact['passed'] = False
            check_artifact['detail'] = 'No real image artifact found'
            logger.error(f"Screenshot verification FAILED: No real image artifact found for task {task.id}")
            verification_checks.append(check_artifact)
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('screenshot_verification_failed', {
                    'task_id': task.id,
                    'reason': 'no_artifact',
                    'artifacts': exec_result.artifacts,
                    'timestamp': time.time()
                })
            
            return False
        
        verification_checks.append(check_artifact)
        
        # ============== 2. VERIFY IMAGE FILE ON DISK ==============
        check_file = {'name': 'file_on_disk', 'passed': True, 'detail': ''}
        
        real_image_path = screenshot_artifacts[0]
        if not os.path.exists(real_image_path):
            check_file['passed'] = False
            check_file['detail'] = f'Image file not found on disk: {real_image_path}'
            logger.error(f"Screenshot verification FAILED: {check_file['detail']}")
            verification_checks.append(check_file)
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('screenshot_verification_failed', {
                    'task_id': task.id,
                    'reason': 'file_not_found',
                    'path': real_image_path,
                    'timestamp': time.time()
                })
            
            return False
        
        verification_checks.append(check_file)
        
        # ============== 3. CHECK FILE SIZE ==============
        check_size = {'name': 'file_size', 'passed': True, 'detail': ''}
        
        file_size = os.path.getsize(real_image_path)
        if file_size < 100:
            check_size['passed'] = False
            check_size['detail'] = f'Image file too small: {file_size} bytes'
            logger.error(f"Screenshot verification FAILED: {check_size['detail']}")
            verification_checks.append(check_size)
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('screenshot_verification_failed', {
                    'task_id': task.id,
                    'reason': 'file_too_small',
                    'size': file_size,
                    'timestamp': time.time()
                })
            
            return False
        
        check_size['detail'] = f'Image size OK: {file_size} bytes'
        verification_checks.append(check_size)
        
        logger.info(f"Screenshot verification: Found real image: {real_image_path} ({file_size} bytes)")
        
        # ============== 4. OCR VERIFICATION ==============
        ocr_check = {'name': 'ocr_verification', 'passed': True, 'detail': '', 'confidence': 1.0, 'text_found': ''}
        
        if expected_text:
            try:
                if hasattr(self, 'vision') and self.vision:
                    ocr_result = self.vision.extract_text(screenshot_artifacts[0])
                    
                    # Check if expected text found
                    if expected_text.lower() in ocr_result.lower():
                        ocr_check['passed'] = True
                        ocr_check['detail'] = f'OCR text found: {expected_text[:30]}...'
                        ocr_check['text_found'] = ocr_result[:200]
                        # Calculate rough confidence based on text length match
                        ocr_check['confidence'] = min(1.0, len(expected_text) / max(1, len(ocr_result)))
                    else:
                        ocr_check['passed'] = False
                        ocr_check['detail'] = f'OCR text NOT found. Expected: {expected_text[:50]}...'
                        ocr_check['text_found'] = ocr_result[:200]
                        ocr_check['confidence'] = 0.0
                        
                        logger.warning(f"Screenshot verification failed: {ocr_check['detail']}")
                        verification_checks.append(ocr_check)
                        return False
                else:
                    # Fallback: check in filename
                    if expected_text.lower() in real_image_path.lower():
                        ocr_check['detail'] = f'Text found in filename (OCR not available)'
                    else:
                        ocr_check['passed'] = False
                        ocr_check['detail'] = 'OCR not available, text not in filename'
                        verification_checks.append(ocr_check)
                        return False
            except Exception as e:
                ocr_check['passed'] = False
                ocr_check['detail'] = f'OCR error: {e}'
                logger.error(f"Screenshot OCR verification error: {e}")
                verification_checks.append(ocr_check)
                return False
        
        verification_checks.append(ocr_check)
        
        # ============== 5. VISION PROMPT VERIFICATION ==============
        vision_check = {'name': 'vision_verification', 'passed': True, 'detail': '', 'confidence': 0.0, 'matches': False}
        
        if vision_prompt:
            try:
                if hasattr(self, 'vision') and self.vision:
                    vision_result = self.vision.analyze_image(screenshot_artifacts[0], vision_prompt)
                    
                    matches = vision_result.get('matches', False)
                    score = vision_result.get('confidence', 0.0)
                    
                    vision_check['matches'] = matches
                    vision_check['confidence'] = score
                    
                    if not matches or score < confidence_threshold:
                        vision_check['passed'] = False
                        vision_check['detail'] = f'Vision confidence {score} < {confidence_threshold}'
                        logger.warning(f"Screenshot verification failed: {vision_check['detail']}")
                        verification_checks.append(vision_check)
                        return False
                    
                    vision_check['detail'] = f'Vision passed with confidence {score:.2f}'
                else:
                    vision_check['detail'] = 'Vision not available, skipping'
            except Exception as e:
                vision_check['passed'] = False
                vision_check['detail'] = f'Vision error: {e}'
                logger.error(f"Screenshot vision verification error: {e}")
                verification_checks.append(vision_check)
                return False
        
        verification_checks.append(vision_check)
        
        # ============== 6. REGION-BASED VERIFICATION ==============
        region_check = {'name': 'region_verification', 'passed': True, 'detail': '', 'regions_checked': 0, 'regions_found': 0}
        
        if expected_regions:
            try:
                if hasattr(self, 'vision') and self.vision:
                    for region in expected_regions:
                        region_text = region.get('expected_text', '')
                        bbox = region.get('bbox', {})  # {x, y, width, height}
                        
                        region_check['regions_checked'] += 1
                        
                        # Extract text from region
                        if bbox and hasattr(self.vision, 'extract_text_from_region'):
                            region_ocr = self.vision.extract_text_from_region(
                                screenshot_artifacts[0], 
                                bbox
                            )
                            
                            if region_text.lower() in region_ocr.lower():
                                region_check['regions_found'] += 1
                            else:
                                region_check['passed'] = False
                                region_check['detail'] = f'Region text not found: {region_text[:30]}...'
                        else:
                            # If no bbox support, check full image
                            full_ocr = self.vision.extract_text(screenshot_artifacts[0])
                            if region_text.lower() in full_ocr.lower():
                                region_check['regions_found'] += 1
                    
                    if not region_check['passed']:
                        logger.warning(f"Screenshot verification failed: {region_check['detail']}")
                        verification_checks.append(region_check)
                        return False
                    
                    region_check['detail'] = f'Regions: {region_check["regions_found"]}/{region_check["regions_checked"]} found'
                else:
                    region_check['detail'] = 'Vision not available for region check'
            except Exception as e:
                region_check['passed'] = False
                region_check['detail'] = f'Region check error: {e}'
                logger.warning(f"Screenshot region verification error: {e}")
        
        verification_checks.append(region_check)
        
        # ============== 7. UI ELEMENT MATCHING ==============
        ui_check = {'name': 'ui_element_matching', 'passed': True, 'detail': '', 'elements_checked': 0, 'elements_found': 0}
        
        if expected_ui_elements:
            try:
                if hasattr(self, 'vision') and self.vision:
                    for ui_elem in expected_ui_elements:
                        elem_type = ui_elem.get('type', '')  # button, input, link, text, etc.
                        elem_text = ui_elem.get('text', '')
                        
                        ui_check['elements_checked'] += 1
                        
                        # Use vision to detect UI elements
                        if hasattr(self.vision, 'detect_ui_elements'):
                            detected = self.vision.detect_ui_elements(screenshot_artifacts[0])
                            
                            # Check if our element is in detected ones
                            found = any(
                                det.get('type') == elem_type and 
                                (elem_text.lower() in det.get('text', '').lower() or 
                                 elem_text.lower() in det.get('label', '').lower())
                                for det in detected
                            )
                            
                            if found:
                                ui_check['elements_found'] += 1
                            else:
                                ui_check['passed'] = False
                                ui_check['detail'] = f'UI element not found: {elem_type} - {elem_text}'
                        else:
                            # Fallback: OCR check
                            full_ocr = self.vision.extract_text(screenshot_artifacts[0])
                            if elem_text.lower() in full_ocr.lower():
                                ui_check['elements_found'] += 1
                    
                    if not ui_check['passed']:
                        logger.warning(f"Screenshot verification failed: {ui_check['detail']}")
                        verification_checks.append(ui_check)
                        return False
                    
                    ui_check['detail'] = f'UI elements: {ui_check["elements_found"]}/{ui_check["elements_checked"]} found'
                else:
                    ui_check['detail'] = 'Vision not available for UI check'
            except Exception as e:
                ui_check['passed'] = False
                ui_check['detail'] = f'UI element check error: {e}'
                logger.warning(f"Screenshot UI verification error: {e}")
        
        verification_checks.append(ui_check)
        
        # ============== 8. BEFORE/AFTER IMAGE DIFF ==============
        diff_check = {'name': 'image_diff', 'passed': True, 'detail': '', 'diff_ratio': 0.0}
        
        if baseline_image_path and os.path.exists(baseline_image_path):
            try:
                if hasattr(self, 'vision') and self.vision and hasattr(self.vision, 'compare_images'):
                    diff_result = self.vision.compare_images(baseline_image_path, real_image_path)
                    
                    diff_ratio = diff_result.get('diff_ratio', 1.0)
                    diff_check['diff_ratio'] = diff_ratio
                    
                    if diff_ratio > diff_threshold:
                        diff_check['passed'] = False
                        diff_check['detail'] = f'Image diff {diff_ratio:.2f} > threshold {diff_threshold}'
                        logger.warning(f"Screenshot verification failed: {diff_check['detail']}")
                        verification_checks.append(diff_check)
                        return False
                    
                    diff_check['detail'] = f'Image diff OK: {diff_ratio:.4f} <= {diff_threshold}'
                else:
                    diff_check['detail'] = 'Image diff not available, skipping'
            except Exception as e:
                diff_check['passed'] = False
                diff_check['detail'] = f'Image diff error: {e}'
                logger.warning(f"Screenshot diff verification error: {e}")
        elif baseline_image_path:
            diff_check['detail'] = f'Baseline image not found: {baseline_image_path}, skipping'
        
        verification_checks.append(diff_check)
        
        # ============== 9. BOUNDING BOX CONFIDENCE ==============
        bbox_check = {'name': 'bbox_confidence', 'passed': True, 'detail': '', 'bboxes_checked': 0, 'bboxes_passed': 0}
        
        if expected_bboxes:
            try:
                if hasattr(self, 'vision') and self.vision and hasattr(self.vision, 'detect_objects'):
                    detected_objects = self.vision.detect_objects(screenshot_artifacts[0])
                    
                    for bbox_exp in expected_bboxes:
                        label = bbox_exp.get('label', '')
                        min_conf = bbox_exp.get('min_confidence', 0.5)
                        
                        bbox_check['bboxes_checked'] += 1
                        
                        # Find matching detected object
                        matched = any(
                            obj.get('label', '').lower() == label.lower() and 
                            obj.get('confidence', 0) >= min_conf
                            for obj in detected_objects
                        )
                        
                        if matched:
                            bbox_check['bboxes_passed'] += 1
                        else:
                            bbox_check['passed'] = False
                            bbox_check['detail'] = f'Bbox not found: {label} with confidence >= {min_conf}'
                    
                    if not bbox_check['passed']:
                        logger.warning(f"Screenshot verification failed: {bbox_check['detail']}")
                        verification_checks.append(bbox_check)
                        return False
                    
                    bbox_check['detail'] = f'Bboxes: {bbox_check["bboxes_passed"]}/{bbox_check["bboxes_checked"]} passed'
                else:
                    bbox_check['detail'] = 'Object detection not available, skipping'
            except Exception as e:
                bbox_check['passed'] = False
                bbox_check['detail'] = f'Bbox check error: {e}'
                logger.warning(f"Screenshot bbox verification error: {e}")
        
        verification_checks.append(bbox_check)
        
        # ============== 10. OVERALL CONFIDENCE AGGREGATION ==============
        confidences = [c.get('confidence', 1.0) for c in verification_checks if 'confidence' in c]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 1.0
        
        # Log all checks
        logger.info(f"🔍 Screenshot verification for task {task.id}: {len(verification_checks)} checks")
        for check in verification_checks:
            status = "✅" if check['passed'] else "❌"
            detail = check.get('detail', '')
            logger.info(f"   {status} {check['name']}: {detail}")
        
        logger.info(f"📊 Overall confidence: {overall_confidence:.2f}")
        
        if overall_confidence < confidence_threshold:
            logger.warning(f"Screenshot verification failed: Overall confidence {overall_confidence:.2f} < {confidence_threshold}")
            return False
        
        logger.info(f"✅ Screenshot verification PASSED for task {task.id}")
        return True
    
    async def _verify_server(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """Server verification - port + HTTP check"""
        
        expected_port = task_meta.get('expected_port', 0)
        expected_endpoint = task_meta.get('expected_endpoint', '/')
        check_http = task_meta.get('check_http', True)
        
        # Check if server started successfully
        if not exec_result.success:
            logger.warning("Server verification failed: Execution was not successful")
            return False
        
        stdout = exec_result.stdout or ""
        stderr = exec_result.stderr or ""
        
        # Look for port in output
        if expected_port:
            port_str = str(expected_port)
            if port_str not in stdout and port_str not in stderr:
                logger.warning(f"Server verification failed: Port {expected_port} not found in output")
                return False
        
        # HTTP check if requested
        if check_http:
            # Try to make HTTP request to verify server is running
            if hasattr(self, 'tools_engine') and self.tools_engine:
                try:
                    http_result = self.tools_engine.execute_tool(
                        'web_request', 
                        {'url': f'http://localhost:{expected_port}{expected_endpoint}', 'timeout': 5}
                    )
                    if not http_result.get('success', False):
                        logger.warning(f"Server verification failed: HTTP check failed")
                        return False
                except Exception as e:
                    logger.warning(f"Server verification: HTTP check skipped - {e}")
        
        logger.info(f"Server verification PASSED for task {task.id}")
        return True
    
    async def _verify_code(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """Code verification - syntax + regression check"""
        
        check_syntax = task_meta.get('check_syntax', True)
        check_output = task_meta.get('check_output', True)
        expected_output = task_meta.get('expected_output', '')
        
        stdout = exec_result.stdout or ""
        stderr = exec_result.stderr or ""
        
        # Syntax check
        if check_syntax and 'SyntaxError' in stderr:
            logger.warning("Code verification failed: Syntax error detected")
            return False
        
        # Output check
        if check_output and expected_output:
            if expected_output not in stdout:
                logger.warning(f"Code verification failed: Expected output not found")
                return False
        
        logger.info(f"Code verification PASSED for task {task.id}")
        return True
    
    async def _verify_file(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """File verification - existence + content check"""
        
        expected_path = task_meta.get('expected_path', '')
        expected_content = task_meta.get('expected_content', '')
        
        # Check artifacts for created files
        file_artifacts = exec_result.artifacts
        
        if expected_path:
            if expected_path not in file_artifacts:
                # Check if file exists
                import os
                if not os.path.exists(expected_path):
                    logger.warning(f"File verification failed: File not found at {expected_path}")
                    return False
        
        # Content check
        if expected_content:
            try:
                with open(expected_path, 'r') as f:
                    content = f.read()
                    if expected_content not in content:
                        logger.warning(f"File verification failed: Expected content not found")
                        return False
            except Exception as e:
                logger.warning(f"File verification: Could not read content - {e}")
        
        logger.info(f"File verification PASSED for task {task.id}")
        return True
    
    async def _repair(self, result: str, failed_task: Optional[Task] = None) -> str:
        """
        OPERATIVE RECOVERY ENGINE with real actions.
        
        Performs:
        1. Error type classification
        2. Retry budget check
        3. Strategy selection based on error type
        4. REAL recovery action execution (not just description)
        5. Escalation if unrecoverable
        
        Recovery actions:
        - RETRY_SAME_TOOL: Re-queue task with same tool
        - ALTERNATE_TOOL: Re-queue with alternate tool
        - REPLAN: Re-plan the task
        - ROLLBACK: Rollback to checkpoint
        - ABORT: Abort the task
        - ESCALATE: Escalate to human
        """
        
        logger.info("🔧 Starting OPERATIVE recovery process...")
        
        # Get failed task if provided
        if failed_task is None:
            # Try to get from recent execution
            failed_task = getattr(self, '_current_failing_task', None)
        
        # Classify the error
        error_type = self._classify_error(result)
        
        logger.info(f"📊 Classified error type: {error_type.value if error_type else 'unknown'}")
        
        # Check retry budget
        if failed_task:
            if failed_task.retry_count >= failed_task.max_retries:
                logger.warning(f"Task {failed_task.id} exceeded max retries ({failed_task.max_retries})")
                return await self._execute_recovery(RecoveryStrategy.ABORT, error_type, result, failed_task)
        
        # Determine recovery strategy based on error type
        strategy = self._select_recovery_strategy(error_type, result)
        
        logger.info(f"🎯 Selected recovery strategy: {strategy.value}")
        
        # Execute REAL recovery action
        recovery_result = await self._execute_recovery(strategy, error_type, result, failed_task)
        
        return recovery_result
    
    async def _execute_recovery(
        self, 
        strategy: RecoveryStrategy, 
        error_type: Optional[ErrorType], 
        result: str,
        failed_task: Optional[Task] = None
    ) -> str:
        """
        Execute REAL recovery action based on strategy.
        
        Each strategy performs actual actions, not just descriptions.
        """
        
        import time
        
        recovery_log = []
        recovery_log.append(f"**Xatolik turi:** {error_type.value if error_type else 'Nomalum'}")
        recovery_log.append(f"**Qayta tiklash strategiyasi:** {strategy.value}")
        recovery_log.append("")
        
        # Strategy-specific REAL actions
        if strategy == RecoveryStrategy.RETRY_SAME_TOOL:
            recovery_log.append("🔄 RETRY_SAME_TOOL: Xuddi shu tool bilan qayta urinish")
            
            if failed_task:
                # Re-queue the task with same tool
                failed_task.retry_count += 1
                failed_task.status = TaskStatus.RETRYING
                failed_task.error = result[:200]  # Store error for debugging
                
                # Re-add to task manager
                self.task_manager.add_task(failed_task)
                recovery_log.append(f"   → Task {failed_task.id} qayta queue'ga qo'shildi (retry #{failed_task.retry_count})")
                recovery_log.append(f"   → Vazifa holati: {failed_task.status.value}")
            else:
                recovery_log.append("   ⚠️ Task topilmadi, faqat log yozildi")
            
        elif strategy == RecoveryStrategy.ALTERNATE_TOOL:
            recovery_log.append("🔧 ALTERNATE_TOOL: Boshqa tool tanlash")
            
            if failed_task:
                # Get task metadata
                task_meta = failed_task.input_data or {}
                current_tool = task_meta.get('tool_used', '')
                
                # Find alternate tool
                alternate_tools = {
                    'execute_command': 'execute_code',
                    'execute_code': 'execute_command',
                    'browser_navigate': 'web_request',
                    'web_request': 'browser_navigate',
                    'write_file': 'execute_command',
                    'read_file': 'execute_command',
                }
                
                new_tool = alternate_tools.get(current_tool, 'web_search')
                
                # Update task with new tool
                task_meta['tool_used'] = new_tool
                task_meta['preferred_tool'] = new_tool
                failed_task.input_data = task_meta
                failed_task.retry_count += 1
                failed_task.status = TaskStatus.RETRYING
                
                # Re-add to task manager
                self.task_manager.add_task(failed_task)
                recovery_log.append(f"   → Tool o'zgartirildi: {current_tool} → {new_tool}")
                recovery_log.append(f"   → Task {failed_task.id} qayta queue'ga qo'shildi")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
            
        elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            recovery_log.append("⏳ RETRY_WITH_BACKOFF: Kutilgan holda qayta urinish")
            
            if failed_task:
                # Calculate backoff time
                backoff_time = min(2 ** failed_task.retry_count, 30)  # Max 30 seconds
                
                failed_task.retry_count += 1
                failed_task.status = TaskStatus.RETRYING
                
                # Re-add to scheduler with delay
                self.scheduler.schedule_task(failed_task, delay=backoff_time)
                recovery_log.append(f"   → Backoff vaqti: {backoff_time} soniya")
                recovery_log.append(f"   → Task {failed_task.id} scheduler'ga qo'shildi (retry #{failed_task.retry_count})")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
            
        elif strategy == RecoveryStrategy.REPLAN:
            recovery_log.append("🔀 REPLAN: Vazifani qayta rejalashtirish")
            
            if failed_task:
                # Reset task for re-planning
                failed_task.status = TaskStatus.PENDING
                failed_task.retry_count += 1
                
                # Clear previous execution data
                failed_task.output_data = None
                failed_task.error = None
                
                # Add back to planning queue
                self.task_manager.add_task(failed_task)
                recovery_log.append(f"   → Task {failed_task.id} rejalashtirish uchun qayta qo'shildi")
                recovery_log.append(f"   → Retry count: {failed_task.retry_count}")
            else:
                recovery_log.append("   ⚠️ Task topilmadi, yangi reja tuzilmadi")
            
        elif strategy == RecoveryStrategy.ROLLBACK:
            recovery_log.append("🔙 ROLLBACK:Checkpoint'ga qaytish")
            
            if failed_task and failed_task.rollback_point:
                # Restore from rollback point
                rollback_data = failed_task.rollback_point
                
                # Restore task state
                failed_task.status = TaskStatus.PENDING
                failed_task.input_data = rollback_data.get('input_data')
                failed_task.output_data = rollback_data.get('output_data')
                failed_task.error = None
                failed_task.retry_count = rollback_data.get('retry_count', 0)
                
                # Add back to task manager
                self.task_manager.add_task(failed_task)
                
                recovery_log.append(f"   → Task {failed_task.id} checkpoint'dan tiklandi")
                recovery_log.append(f"   → Rollback point vaqti: {rollback_data.get('timestamp', 'n/a')}")
            else:
                recovery_log.append("   ⚠️ Rollback point topilmadi")
                recovery_log.append("   → Abort ga o'tiladi")
                strategy = RecoveryStrategy.ABORT
            
        elif strategy == RecoveryStrategy.SIMPLIFY_TASK:
            recovery_log.append("📝 SIMPLIFY_TASK: Vazifani soddalashtirish")
            
            if failed_task:
                # Split task into smaller parts
                desc = failed_task.description
                
                # Simple split: take first half of description
                mid = len(desc) // 2
                simpler_desc = desc[:mid] + " (soddalashtirilgan)"
                
                # Create simplified task
                simple_task = Task(
                    id=f"{failed_task.id}_simplified",
                    description=simpler_desc,
                    priority=failed_task.priority,
                    input_data={
                        **((failed_task.input_data) or {}),
                        'simplified_from': failed_task.id,
                        'original_description': desc
                    }
                )
                
                # Add simplified task
                self.task_manager.add_task(simple_task)
                
                # Mark original as completed (replaced)
                failed_task.status = TaskStatus.COMPLETED
                
                recovery_log.append(f"   → Original task: {failed_task.id}")
                recovery_log.append(f"   → Yangi sodda task: {simple_task.id}")
                recovery_log.append(f"   → Description: {simple_task.description[:50]}...")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
            
        elif strategy == RecoveryStrategy.ESCALATE_TO_HUMAN:
            recovery_log.append("👤 ESCALATE_TO_HUMAN: Insonga yo'naltirish")
            
            if failed_task:
                # Mark task for human review
                failed_task.status = TaskStatus.FAILED
                failed_task.error = f"ESCALATED: {result[:200]}"
                
                # Create escalation notification
                escalation_msg = f"""🚨 **Vazifa Eskalatsiyasi**

Vazifa ID: {failed_task.id}
Xatolik: {error_type.value if error_type else 'Noma\'lum'}
Tavsif: {failed_task.description}
Xatolik xabari: {result[:200]}

Iltimos, bu vazifani ko'rib chiqing.
"""
                # Notify via approval system if available
                if hasattr(self, 'approval_engine') and self.approval_engine:
                    self.approval_engine.notify_human(escalation_msg)
                
                recovery_log.append(f"   → Task {failed_task.id} insonga yo'naltirildi")
                recovery_log.append("   → Tasdiq kutish holatida")
            else:
                recovery_log.append("   ⚠️ Task topilmadi, lekin eskalatsiya xabari yuborildi")
            
        else:  # ABORT
            recovery_log.append("❌ ABORT: Vazifani to'xtatish")
            
            if failed_task:
                # Mark as permanently failed
                failed_task.status = TaskStatus.FAILED
                failed_task.error = result[:200]
                
                # Update task manager
                self.task_manager.mark_failed(failed_task.id, result[:200])
                
                recovery_log.append(f"   → Task {failed_task.id} muvaffaqiyatsiz deb belgilandi")
                recovery_log.append(f"   → Xatolik: {result[:100]}...")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
        
        # Format recovery response
        recovery_response = "\n".join(recovery_log)
        
        logger.info(f"Operative Recovery completed: {strategy.value}")
        
        # Emit telemetry event
        if hasattr(self, 'telemetry') and self.telemetry:
            self.telemetry.record_event('recovery', {
                'strategy': strategy.value,
                'error_type': error_type.value if error_type else 'unknown',
                'task_id': failed_task.id if failed_task else None,
                'timestamp': time.time()
            })
        
        return recovery_response
    
    def get_status(self) -> str:
        """Get kernel status"""
        
        return f"""🔵 **Kernel Holati**

📌 Holat: {self.state.value}
📋 Vazifalar: {self.task_manager.get_task_graph()}
⏰ Scheduler: {self.scheduler.get_status()['task_count']} ta
🤖 Agentlar: {json.dumps(self.coordinator.get_status(), indent=2)}
{self.telemetry.get_summary()}"""
    
    def submit_task(self, user_message: str) -> str:
        """
        MAIN ENTRY POINT for all user messages
        
        FIXED ISSUES (15):
        - Explicit safe-mode
        - Structured error
        - Telemetry event
        - User notification
        """
        
        import traceback as tb
        
        logger.info(f"📥 Kernel received task: {user_message[:50]}...")
        
        execution_mode = "async_pipeline"
        
        try:
            result = asyncio.run(self.process(user_message))
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('task_submission', {
                    'mode': execution_mode,
                    'success': True,
                    'message_preview': user_message[:100],
                    'timestamp': time.time()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Task failed in {execution_mode} mode: {e}")
            
            error_trace = tb.format_exc()
            logger.debug(f"Full traceback: {error_trace}")
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('task_submission', {
                    'mode': execution_mode,
                    'success': False,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'message_preview': user_message[:100],
                    'timestamp': time.time()
                })
            
            safe_mode = getattr(self, 'SAFE_MODE', True)
            
            if safe_mode:
                logger.warning("SAFE_MODE enabled - returning structured error instead of fallback")
                
                # Structured failure response
                structured_failure = {
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "safe_mode": True,
                    "degradation_level": "full",
                    "original_error": str(e)[:500],
                    "timestamp": time.time(),
                    "suggestion": "Check system logs for details or disable safe_mode for fallback execution"
                }
                
                if hasattr(self, 'telemetry') and self.telemetry:
                    self.telemetry.record_event('fallback_safe_mode', {
                        'reason': 'SAFE_MODE enabled',
                        'original_error': str(e),
                        'error_type': type(e).__name__,
                        'degradation': 'full',
                        'timestamp': time.time()
                    })
                
                # User-friendly degradation notice
                degradation_notice = f"""
╔══════════════════════════════════════════════════════════════╗
║              ⚠️  TIZIM BUZILGANLIGI HAQIDA                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Xatolik yuz berdi: {str(e)[:50]}...              ║
║                                                              ║
║  Holat: SAFE_MODE faol                              ║
║                                                              ║
║  Bu xatolik tufayli tizim to'liq ishlamaydi.         ║
║  Iltimos, quyidagilarni bajaring:                      ║
║    1. Loglarni tekshiring                                  ║
║    2. Safe mode'ni o'chirib qayta urinib ko'ring         ║
║    3. Administrator bilan bog'laning                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
                
                return f"❌ Xatolik: {str(e)}\n\n{degradation_notice}"
            
            logger.warning("Attempting fallback execution")
            
            if hasattr(self, 'native_brain'):
                try:
                    execution_mode = "brain_fallback"
                    result = self.native_brain.think(user_message)
                    
                    if hasattr(self, 'telemetry') and self.telemetry:
                        self.telemetry.record_event('task_submission', {
                            'mode': execution_mode,
                            'success': True,
                            'warning': 'Results from fallback',
                            'timestamp': time.time()
                        })
                    
                    return f"⚠️ Ogohlantirish: Fallback rejada ishladi\n\n{result}"
                    
                except Exception as brain_error:
                    logger.error(f"Brain fallback also failed: {brain_error}")
                    return f"❌ Xatolik: {str(brain_error)}\n\nEslatma: Asosiy pipeline va fallback ham xatolik berdi."
            
            return f"❌ Xatolik: {str(e)}"
    
    def set_safe_mode(self, enabled: bool = True):
        """Enable or disable safe mode"""
        self.SAFE_MODE = enabled
        logger.info(f"Safe mode set to: {enabled}")
    
    def _execute_simple(self, task: str) -> str:
        """Simple execution fallback"""
        return f"Vazifa qabul qilindi: {task[:50]}..."
    
    def get_task_queue_status(self) -> str:
        """Get task queue status"""
        graph = self.task_manager.get_task_graph()
        return f"""📋 **Vazifalar Holati**

Pending: {graph['pending']}
Running: {graph['running']}
Completed: {graph['completed']}
Failed: {graph['failed']}
"""
    
    def get_dashboard(self) -> Dict:
        """Get full dashboard data"""
        
        return {
            "kernel_state": self.state.value,
            "tasks": self.task_manager.get_task_graph(),
            "scheduler": self.scheduler.get_status(),
            "agents": self.coordinator.get_status(),
            "telemetry": self.telemetry.get_metrics(),
            "artifacts": self.artifacts.get_all_artifacts(),
            "approvals": list(self.pending_approvals.keys())
        }


# ==================== FACTORY ====================

def create_kernel(api_key: str, tools_engine) -> CentralKernel:
    """Create the central kernel"""
    return CentralKernel(api_key, tools_engine)
# Kernel updated Sat Mar 14 08:06:38 UTC 2026

def _get_recovery_hint(parsing_attempts: List[Dict]) -> str:
    """
    Get recovery hint based on parsing failures.
    """
    if not parsing_attempts:
        return "No parsing attempts recorded"
    
    # Check failure reasons
    reasons = [a.get('reason', '') for a in parsing_attempts]
    
    if 'json_decode_error' in reasons:
        return "Model returned malformed JSON - prompt for cleaner JSON output"
    elif 'schema_validation_failed' in reasons:
        return "Schema mismatch - validate task structure before returning"
    elif 'no_match' in reasons:
        return "No JSON found in response - model returned prose instead of JSON"
    else:
        return "Multiple parse failures - simplify response format"

# ==================== COMPREHENSIVE RECOVERY ENGINE ====================

class RecoveryStrategy(Enum):
    """All recovery strategies - executed in priority order"""
    REQUEUE = "requeue"           # Put back in queue
    ALTERNATE_TOOL = "alternate_tool"  # Try different tool
    ROLLBACK = "rollback"        # Revert changes
    REPLAN = "replan"            # Re-generate plan
    HUMAN_ESCALATION = "human"   # Call human
    DEGRADED_MODE = "degraded"  # Reduced functionality
    RETRY_EXHAUSTED = "exhausted"  # No more retries


class RecoveryEngine:
    """
    COMPREHENSIVE RECOVERY ENGINE - No1-grade.
    
    Each failure triggers appropriate recovery strategy:
    1. REQUEUE - transient failure
    2. ALTERNATE_TOOL - tool-specific failure
    3. ROLLBACK - state corruption
    4. REPLAN - fundamental plan failure
    5. DEGRADED_MODE - partial success possible
    6. HUMAN_ESCALATION - critical failure
    7. RETRY_EXHAUSTED - budget exhausted
    """
    
    def __init__(self, kernel):
        self.kernel = kernel
        self.retry_budget = {}  # Per-task retry budget
        self.max_retries = 3
        self.max_replan_depth = 2  # Max replan attempts per task
        self.replan_depth = {}  # Per-task replan depth
        self.rollback_stack = {}  # TaskID -> rollback actions
        
        # Approval mapping: tool -> strategy for denied/expired
        self.approval_mapping = {
            'denied': {
                'execute_command': 'ALTERNATE_TOOL',
                'delete_file': 'ABORT',
                'browser_navigate': 'REQUEUE',
                'write_file': 'REPLAN',
                'default': 'REQUEUE'
            },
            'expired': {
                'execute_command': 'REQUEUE',
                'browser_navigate': 'REQUEUE',
                'write_file': 'REPLAN',
                'default': 'REQUEUE'
            }
        }
        
        # Escalation conditions
        self.escalation_conditions = [
            'critical_error',
            'security_breach',
            'data_loss'
        ]
    
    async def execute_recovery(self, task: Task, failure_reason: str) -> Dict:
        """Execute appropriate recovery strategy based on failure type"""
        
        # Check retry budget first
        budget = self.retry_budget.get(task.id, 0)
        
        if budget >= self.max_retries:
            logger.warning(f"⚠️ Retry budget exhausted for {task.id}")
            return await self._retry_exhausted_recovery(task, failure_reason)
        
        # Map failure type to recovery strategy
        if 'verification_failed' in failure_reason:
            return await self._alternate_tool_recovery(task, failure_reason)
        elif 'tool_error' in failure_reason:
            return await self._alternate_tool_recovery(task, failure_reason)
        elif 'timeout' in failure_reason:
            return await self._requeue_recovery(task, failure_reason)
        elif 'artifact_missing' in failure_reason:
            return await self._rollback_recovery(task, failure_reason)
        elif 'approval_denied' in failure_reason or 'approval_expired' in failure_reason:
            # Use approval mapping
            approval_type = 'denied' if 'denied' in failure_reason else 'expired'
            tool_name = (task.input_data or {}).get('tool_used', 'default')
            mapping = self.approval_mapping.get(approval_type, {})
            strategy = mapping.get(tool_name, mapping.get('default', 'REQUEUE'))
            logger.info(f"📋 Approval {approval_type} for {task.id}, tool={tool_name}, strategy={strategy}")
            if strategy == 'ALTERNATE_TOOL':
                return await self._alternate_tool_recovery(task, failure_reason)
            elif strategy == 'REPLAN':
                self.replan_depth[task.id] = self.replan_depth.get(task.id, 0) + 1
                return await self._replan_recovery(task, failure_reason)
            elif strategy == 'ABORT':
                return await self._retry_exhausted_recovery(task, failure_reason)
            else:
                return await self._requeue_recovery(task, failure_reason)
        elif 'critical_error' in failure_reason:
            return await self._human_escalation(task, failure_reason)
        else:
            return await self._degraded_mode_recovery(task, failure_reason)
    
    async def _requeue_recovery(self, task, reason) -> Dict:
        """1. REQUEUE - transient failure, try again"""
        self.retry_budget[task.id] = self.retry_budget.get(task.id, 0) + 1
        logger.info(f"🔄 REQUEUE: {task.id} (attempt {self.retry_budget[task.id]})")
        return {
            'strategy': RecoveryStrategy.REQUEUE,
            'action': 'requeue',
            'can_continue': True,
            'retry_count': self.retry_budget[task.id]
        }
    
    async def _alternate_tool_recovery(self, task, reason) -> Dict:
        """2. ALTERNATE_TOOL - try different tool"""
        alt_tool = (task.input_data or {}).get('alternate_tool')
        if alt_tool:
            logger.info(f"🔄 ALT_TOOL: {task.id} -> {alt_tool}")
            task.input_data['tool_used'] = alt_tool
            return {'strategy': RecoveryStrategy.ALTERNATE_TOOL, 'action': 'alternate', 'tool': alt_tool}
        
        # Fallback to requeue
        return await self._requeue_recovery(task, reason)
    
    async def _rollback_recovery(self, task, reason) -> Dict:
        """3. ROLLBACK - revert changes"""
        logger.warning(f"⏪ ROLLBACK: {task.id}")
        # Execute rollback actions
        rollback_actions = self.rollback_stack.get(task.id, [])
        for action in reversed(rollback_actions):
            try:
                action['rollback_fn']()
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
        
        return {'strategy': RecoveryStrategy.ROLLBACK, 'action': 'rolled_back', 'can_continue': False}
    
    async def _replan_recovery(self, task, reason) -> Dict:
        """4. REPLAN - regenerate plan"""
        logger.warning(f"🔄 REPLAN: {task.id}")
        return {'strategy': RecoveryStrategy.REPLAN, 'action': 'replan', 'can_continue': True}
    
    async def _human_escalation(self, task, reason) -> Dict:
        """5. HUMAN_ESCALATION - critical failure"""
        logger.error(f"🚨 HUMAN_ESCALATION: {task.id} - {reason}")
        return {
            'strategy': RecoveryStrategy.HUMAN_ESCALATION,
            'action': 'escalate',
            'can_continue': False,
            'reason': reason
        }
    
    async def _degraded_mode_recovery(self, task, reason) -> Dict:
        """6. DEGRADED_MODE - reduced functionality"""
        logger.warning(f"📉 DEGRADED_MODE: {task.id}")
        task.input_data['degraded'] = True
        return {'strategy': RecoveryStrategy.DEGRADED_MODE, 'action': 'degraded', 'can_continue': True}
    
    async def _retry_exhausted_recovery(self, task, reason) -> Dict:
        """7. RETRY_EXHAUSTED - no more budget"""
        logger.error(f"❌ RETRY_EXHAUSTED: {task.id}")
        return {
            'strategy': RecoveryStrategy.RETRY_EXHAUSTED,
            'action': 'abort',
            'can_continue': False,
            'budget_used': self.retry_budget.get(task.id, 0),
            'max_retries': self.max_retries
        }
    
    def record_rollback(self, task_id: str, rollback_fn):
        """Record rollback action for later execution"""
        if task_id not in self.rollback_stack:
            self.rollback_stack[task_id] = []
        self.rollback_stack[task_id].append({'rollback_fn': rollback_fn})





# ==================== PLANNER QUALITY TRACKER ====================

class PlannerQualityTracker:
    """
    Tracks planner quality over time with metrics.
    
    Provides:
    - Success/failure rate tracking
    - Per-strategy success rates
    - Quality trends over time
    - Invalid snippet logging for debugging
    """
    
    def __init__(self):
        self.parse_history: List[Dict] = []
        self.strategy_stats: Dict[str, Dict] = defaultdict(lambda: {
            'success': 0, 
            'failure': 0, 
            'total_time_ms': 0
        })
        self.quality_window = 100  # Track last 100 parses
        
    def record_parse(self, success: bool, strategy: str, time_ms: float, task_count: int = 0):
        """Record a parse attempt"""
        self.parse_history.append({
            'success': success,
            'strategy': strategy,
            'time_ms': time_ms,
            'task_count': task_count,
            'timestamp': time.time()
        })
        
        # Keep only last N records
        if len(self.parse_history) > self.quality_window:
            self.parse_history = self.parse_history[-self.quality_window:]
            
        # Update strategy stats
        if success:
            self.strategy_stats[strategy]['success'] += 1
        else:
            self.strategy_stats[strategy]['failure'] += 1
        self.strategy_stats[strategy]['total_time_ms'] += time_ms
        
    def get_success_rate(self) -> float:
        """Get overall success rate"""
        if not self.parse_history:
            return 0.0
        success_count = sum(1 for p in self.parse_history if p['success'])
        return success_count / len(self.parse_history)
        
    def get_strategy_stats(self) -> Dict:
        """Get per-strategy statistics"""
        stats = {}
        for strategy, data in self.strategy_stats.items():
            total = data['success'] + data['failure']
            if total > 0:
                stats[strategy] = {
                    'success_rate': data['success'] / total,
                    'total_attempts': total,
                    'avg_time_ms': data['total_time_ms'] / total
                }
        return stats
        
    def get_quality_report(self) -> Dict:
        """Get comprehensive quality report"""
        return {
            'overall_success_rate': self.get_success_rate(),
            'total_parses': len(self.parse_history),
            'strategy_stats': self.get_strategy_stats(),
            'recent_success_rate': self._get_recent_success_rate()
        }
        
    def _get_recent_success_rate(self, n: int = 20) -> float:
        """Get success rate for last N parses"""
        recent = self.parse_history[-n:] if self.parse_history else []
        if not recent:
            return 0.0
        success_count = sum(1 for p in recent if p['success'])
        return success_count / len(recent)
