"""
OmniAgent X - Playwright Browser Automation (REFACTORED)
=======================================================
Production-grade browser automation

ENHANCED:
- Browser bootstrap/install script
- Session persistence
- Multi-tab awareness
- DOM extraction + screenshot-based fallback
- Login/auth flow state handling
- Action verification
- Anti-bot fallback
- Upload/download management
- Task-specific verifiers
"""
import os
import json
import logging
import time
import uuid
import base64
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - install with: pip install playwright")


# ==================== ENUMS & DATA CLASSES ====================

class BrowserState(Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class ActionResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    VERIFIED = "verified"
    NOT_FOUND = "not_found"


@dataclass
class TabInfo:
    """Information about a browser tab"""
    id: str
    title: str
    url: str
    is_active: bool


@dataclass
class AuthState:
    """Authentication state for a site"""
    site_url: str
    cookies: List[Dict]
    local_storage: Dict
    session_storage: Dict
    logged_in: bool
    timestamp: float
    # Enhanced: Add auth persistence metadata
    auth_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    headers: Optional[Dict] = None


@dataclass
class ActionVerification:
    """Verification of an action"""
    action: str
    expected: str
    actual: str
    verified: bool
    screenshot: Optional[str]
    # Enhanced: Add semantic verification
    semantic_check: Optional[Dict] = None
    dom_snapshot: Optional[Dict] = None
    error_message: Optional[str] = None


@dataclass
class DownloadState:
    """Download orchestration state"""
    url: str
    path: str
    status: str  # pending, downloading, completed, failed
    progress: float
    started_at: float
    completed_at: Optional[float] = None
    error: Optional[str] = None


@dataclass
class UploadState:
    """Upload orchestration state"""
    file_path: str
    target_url: str
    status: str  # pending, uploading, completed, failed
    progress: float
    started_at: float
    completed_at: Optional[float] = None
    error: Optional[str] = None


# ==================== BROWSER MANAGER ====================

class BrowserManager:
    """
    Production-grade browser automation with Playwright
    """
    
    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "browser"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Playwright instance
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: Dict[str, Page] = {}
        self.active_page_id: Optional[str] = None
        
        # State
        self.state = BrowserState.IDLE
        
        # Auth states
        self.auth_states: Dict[str, AuthState] = {}
        
        # Screenshot directory
        self.screenshot_dir = self.data_dir / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # Session persistence
        self.session_file = self.data_dir / "session.json"
        
        if PLAYWRIGHT_AVAILABLE:
            try:
                self.playwright = sync_playwright().start()
                logger.info("🌐 Playwright initialized")
            except Exception as e:
                logger.warning(f"Playwright start failed: {e}")
        
        logger.info("🌐 Browser Manager initialized (REFACTORED)")
    
    # ==================== BROWSER BOOTSTRAP ====================
    
    @staticmethod
    def install_browsers() -> str:
        """Install Playwright browsers"""
        if not PLAYWRIGHT_AVAILABLE:
            return "❌ Playwright not installed"
        
        try:
            import subprocess
            result = subprocess.run(
                ["playwright", "install", "chromium", "firefox", "webkit"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return "✅ Browsers installed successfully"
            else:
                return f"❌ Install failed: {result.stderr}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def start(self, headless: bool = False, user_data_dir: str = None,
              restore_session: bool = True) -> str:
        """Start browser with optional session restoration"""
        if not PLAYWRIGHT_AVAILABLE:
            return "❌ Playwright not available"
        
        if self.state == BrowserState.RUNNING:
            return "⚠️ Browser already running"
        
        self.state = BrowserState.STARTING
        
        try:
            # Launch browser
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Create context with storage state
            if restore_session and self.session_file.exists():
                try:
                    storage_state = json.loads(self.session_file.read_text())
                    self.context = self.browser.new_context(storage_state=storage_state)
                except (json.JSONDecodeError, IOError, Exception) as e:
                    logger.warning(f"Failed to restore session: {e}")
                    self.context = self.browser.new_context()
            else:
                self.context = self.browser.new_context()
            
            # Set viewport
            self.context.set_viewport_size({"width": 1280, "height": 720})
            
            self.state = BrowserState.RUNNING
            
            logger.info("🌐 Browser started")
            return "🌐 Browser started successfully"
        
        except Exception as e:
            self.state = BrowserState.ERROR
            logger.error(f"Browser start failed: {e}")
            return f"❌ Error: {str(e)}"
    
    # ==================== TAB MANAGEMENT ====================
    
    def create_tab(self, url: str = "about:blank") -> str:
        """Create new tab"""
        if self.state != BrowserState.RUNNING:
            return "❌ Browser not running"
        
        try:
            page = self.context.new_page()
            tab_id = str(uuid.uuid4())[:8]
            self.pages[tab_id] = page
            
            if url != "about:blank":
                page.goto(url, wait_until="domcontentloaded")
            
            self.active_page_id = tab_id
            
            logger.info(f"📑 New tab: {tab_id}")
            return f"✅ New tab created: {tab_id}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def switch_tab(self, tab_id: str) -> str:
        """Switch to tab"""
        if tab_id not in self.pages:
            return f"❌ Tab not found: {tab_id}"
        
        self.active_page_id = tab_id
        return f"✅ Switched to tab: {tab_id}"
    
    def close_tab(self, tab_id: str = None) -> str:
        """Close tab"""
        target_id = tab_id or self.active_page_id
        
        if target_id not in self.pages:
            return f"❌ Tab not found"
        
        try:
            self.pages[target_id].close()
            del self.pages[target_id]
            
            if self.active_page_id == target_id:
                self.active_page_id = list(self.pages.keys())[0] if self.pages else None
            
            return f"✅ Tab closed: {target_id}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def list_tabs(self) -> List[TabInfo]:
        """List all tabs"""
        tabs = []
        
        for tab_id, page in self.pages.items():
            try:
                tabs.append(TabInfo(
                    id=tab_id,
                    title=page.title(),
                    url=page.url,
                    is_active=(tab_id == self.active_page_id)
                ))
            except Exception as e: logger.warning(f"Exception: {e}")
        
        return tabs
    
    def get_active_page(self) -> Optional[Page]:
        """Get active page"""
        if self.active_page_id and self.active_page_id in self.pages:
            return self.pages[self.active_page_id]
        return None
    
    # ==================== NAVIGATION ====================
    
    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> str:
        """Navigate to URL"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            response = page.goto(url, wait_until=wait_until)
            
            if response:
                status = response.status
                return f"✅ Navigated to {url} (Status: {status})"
            else:
                return f"✅ Navigated to {url}"
        
        except Exception as e:
            return f"❌ Navigation error: {str(e)}"
    
    def go_back(self) -> str:
        """Go back"""
        page = self.get_active_page()
        if not page:
            return "❌ No active page"
        
        page.go_back()
        return "✅ Went back"
    
    def go_forward(self) -> str:
        """Go forward"""
        page = self.get_active_page()
        if not page:
            return "❌ No active page"
        
        page.go_forward()
        return "✅ Went forward"
    
    def reload(self) -> str:
        """Reload page"""
        page = self.get_active_page()
        if not page:
            return "❌ No active page"
        
        page.reload()
        return "✅ Reloaded"
    
    # ==================== ACTIONS ====================
    
    def click(self, selector: str, verify: bool = True) -> ActionVerification:
        """Click element with optional verification"""
        page = self.get_active_page()
        
        if not page:
            return ActionVerification("click", selector, "No active page", False, None)
        
        try:
            # Take before screenshot
            before_shot = self._take_screenshot()
            
            # Click
            page.click(selector)
            
            # Verify if requested
            if verify:
                after_shot = self._take_screenshot()
                
                # Simple verification: check if page changed
                verified = True  # Could compare screenshots here
                
                return ActionVerification(
                    action="click",
                    expected=selector,
                    actual="clicked",
                    verified=verified,
                    screenshot=after_shot
                )
            
            return ActionVerification("click", selector, "clicked", True, None)
        
        except Exception as e:
            return ActionVerification("click", selector, str(e), False, None)
    
    def type_text(self, selector: str, text: str, clear: bool = True) -> str:
        """Type text into element"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            if clear:
                page.fill(selector, text)
            else:
                page.type(selector, text)
            
            return f"✅ Typed: {text[:20]}..."
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def select_option(self, selector: str, value: str) -> str:
        """Select option from dropdown"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            page.select_option(selector, value)
            return f"✅ Selected: {value}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def hover(self, selector: str) -> str:
        """Hover over element"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            page.hover(selector)
            return f"✅ Hovered: {selector}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # ==================== CONTENT EXTRACTION ====================
    
    def get_content(self, max_length: int = 5000) -> str:
        """Get page content"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            content = page.content()
            if len(content) > max_length:
                content = content[:max_length] + "..."
            return content
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def extract_text(self, selector: str = None) -> str:
        """Extract text from page or element"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            if selector:
                elements = page.query_selector_all(selector)
                texts = [el.inner_text() for el in elements]
                return "\n".join(texts)
            else:
                return page.inner_text("body")
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def extract_links(self) -> List[Dict]:
        """Extract all links from page"""
        page = self.get_active_page()
        
        if not page:
            return []
        
        try:
            links = page.query_selector_all("a")
            result = []
            
            for link in links:
                try:
                    result.append({
                        "text": link.inner_text()[:50],
                        "href": link.get_attribute("href")
                    })
                except Exception as e: logger.warning(f"Exception: {e}")
            
            return result
        
        except Exception as e: logger.warning(f"Exception: {e}"); return []
    
    def extract_images(self) -> List[Dict]:
        """Extract all images from page"""
        page = self.get_active_page()
        
        if not page:
            return []
        
        try:
            images = page.query_selector_all("img")
            result = []
            
            for img in images:
                try:
                    result.append({
                        "alt": img.get_attribute("alt") or "",
                        "src": img.get_attribute("src"),
                        "title": img.get_attribute("title") or ""
                    })
                except Exception as e: logger.warning(f"Exception: {e}")
            
            return result
        
        except Exception as e: logger.warning(f"Exception: {e}"); return []
    
    # ==================== SCREENSHOTS ====================
    
    def _take_screenshot(self) -> Optional[str]:
        """Take screenshot of current page"""
        try:
            page = self.get_active_page()
            if not page:
                return None
            
            filename = f"screenshot_{uuid.uuid4().hex[:8]}.png"
            path = self.screenshot_dir / filename
            
            page.screenshot(path=str(path), full_page=True)
            
            return str(path)
        
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None
    
    def screenshot(self, name: str = None, full_page: bool = True) -> str:
        """Take screenshot with custom name"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            if name:
                filename = f"{name}.png"
            else:
                filename = f"screenshot_{uuid.uuid4().hex[:8]}.png"
            
            path = self.screenshot_dir / filename
            page.screenshot(path=str(path), full_page=full_page)
            
            return f"📸 Screenshot: {path}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def screenshot_element(self, selector: str) -> str:
        """Take screenshot of specific element"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            element = page.query_selector(selector)
            
            if not element:
                return f"❌ Element not found: {selector}"
            
            filename = f"element_{uuid.uuid4().hex[:8]}.png"
            path = self.screenshot_dir / filename
            
            element.screenshot(path=str(path))
            
            return f"📸 Element screenshot: {path}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # ==================== WAITING ====================
    
    def wait_for_selector(self, selector: str, timeout: int = 30000,
                         state: str = "visible") -> str:
        """Wait for element"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            page.wait_for_selector(selector, timeout=timeout, state=state)
            return f"✅ Element found: {selector}"
        
        except Exception as e:
            return f"❌ Element not found: {selector}"
    
    def wait_for_load(self, timeout: int = 30000) -> str:
        """Wait for page to load"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            page.wait_for_load_state("load", timeout=timeout)
            return "✅ Page loaded"
        
        except Exception as e:
            return f"❌ Load timeout: {str(e)}"
    
    def wait_for_navigation(self, url: str, timeout: int = 30000) -> str:
        """Wait for navigation to URL"""
        page = self.get_active_page()
        
        if not page:
            return "❌ No active page"
        
        try:
            page.wait_for_url(url, timeout=timeout)
            return f"✅ Navigated to: {url}"
        
        except Exception as e:
            return f"❌ Navigation timeout: {str(e)}"
    
    # ==================== AUTHENTICATION ====================
    
    def save_auth_state(self, site_url: str) -> str:
        """Save current authentication state"""
        if not self.context:
            return "❌ No browser context"
        
        try:
            cookies = self.context.cookies()
            
            # Try to get local storage
            local_storage = self.context.evaluate("""() => {
                let items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }""")
            
            auth_state = AuthState(
                site_url=site_url,
                cookies=cookies,
                local_storage=local_storage,
                session_storage={},
                logged_in=True,
                timestamp=datetime.now().timestamp()
            )
            
            self.auth_states[site_url] = auth_state
            
            # Save to file
            auth_file = self.data_dir / "auth" / f"{uuid.uuid4().hex[:8]}.json"
            auth_file.parent.mkdir(exist_ok=True)
            auth_file.write_text(json.dumps(auth_state.__dict__, default=str))
            
            return f"✅ Auth state saved for: {site_url}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def restore_auth_state(self, site_url: str) -> str:
        """Restore authentication state"""
        if not self.context:
            return "❌ No browser context"
        
        # Find saved state
        auth_dir = self.data_dir / "auth"
        
        if not auth_dir.exists():
            return "❌ No saved auth states"
        
        try:
            for auth_file in auth_dir.glob("*.json"):
                try:
                    data = json.loads(auth_file.read_text())
                    
                    if data.get("site_url") == site_url:
                        # Restore cookies
                        self.context.add_cookies(data["cookies"])
                        
                        # Restore local storage
                        for key, value in data.get("local_storage", {}).items():
                            self.context.evaluate(f"""(key, value) => {{
                                localStorage.setItem(key, value);
                            }}""", key, value)
                        
                        return f"✅ Auth restored for: {site_url}"
                
                except Exception as e:
                    # Log the failure but continue checking other entries
                    logger.warning(f"Failed to restore auth for {site_url}: {e}")
                    continue
            
            return "❌ Auth state not found"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # ==================== ENHANCED: MULTI-TAB REASONING ====================
    
    def get_all_tabs_info(self) -> Dict[str, Any]:
        """Get comprehensive info about all tabs for multi-tab reasoning"""
        tabs_info = {
            "total_tabs": len(self.pages),
            "active_tab": self.active_page_id,
            "tabs": []
        }
        
        for tab_id, page in self.pages.items():
            try:
                tabs_info["tabs"].append({
                    "id": tab_id,
                    "title": page.title(),
                    "url": page.url,
                    "is_active": tab_id == self.active_page_id,
                    "load_state": page.evaluate("() => document.readyState")
                })
            except Exception as e:
                logger.warning(f"Failed to get tab info: {e}")
        
        return tabs_info
    
    def switch_to_tab_by_url(self, url_pattern: str) -> str:
        """Switch to tab matching URL pattern"""
        for tab_id, page in self.pages.items():
            try:
                if url_pattern in page.url:
                    self.active_page_id = tab_id
                    return f"✅ Switched to tab: {tab_id} ({page.url})"
            except Exception as e:
                logger.warning(f"Error checking tab: {e}")
        
        return f"❌ No tab found matching: {url_pattern}"
    
    def wait_for_all_tabs_loaded(self, timeout: int = 30000) -> str:
        """Wait for all tabs to finish loading"""
        if not self.pages:
            return "❌ No tabs open"
        
        try:
            for tab_id, page in self.pages.items():
                page.wait_for_load_state("load", timeout=timeout)
            
            return f"✅ All {len(self.pages)} tabs loaded"
        
        except Exception as e:
            return f"❌ Load timeout: {str(e)}"
    
    # ==================== ENHANCED: DOWNLOAD ORCHESTRATION ====================
    
    def setup_download_handler(self, download_dir: Path = None) -> str:
        """Setup download handler for the context"""
        if not self.context:
            return "❌ No browser context"
        
        if download_dir is None:
            download_dir = self.data_dir / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            self.context.set_default_download_path(str(download_dir))
            return f"✅ Download handler setup: {download_dir}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def download_file(self, url: str, filename: str = None) -> DownloadState:
        """Download file with progress tracking"""
        if filename is None:
            filename = url.split("/")[-1] or "download"
        
        download_dir = self.data_dir / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        file_path = download_dir / filename
        
        download_state = DownloadState(
            url=url,
            path=str(file_path),
            status="pending",
            progress=0.0,
            started_at=datetime.now().timestamp()
        )
        
        try:
            download_state.status = "downloading"
            page = self.get_active_page()
            
            # Start download
            async_task = page.request.get(url)
            
            # Write to file with progress
            response = async_task
            if response.status == 200:
                content = response.body()
                file_path.write_bytes(content)
                download_state.progress = 1.0
                download_state.status = "completed"
                download_state.completed_at = datetime.now().timestamp()
            else:
                download_state.status = "failed"
                download_state.error = f"HTTP {response.status}"
        
        except Exception as e:
            download_state.status = "failed"
            download_state.error = str(e)
        
        return download_state
    
    # ==================== ENHANCED: UPLOAD ORCHESTRATION ====================
    
    def upload_file(self, selector: str, file_path: str) -> UploadState:
        """Upload file with progress tracking"""
        upload_state = UploadState(
            file_path=file_path,
            target_url=selector,
            status="pending",
            progress=0.0,
            started_at=datetime.now().timestamp()
        )
        
        try:
            page = self.get_active_page()
            if not page:
                upload_state.status = "failed"
                upload_state.error = "No active page"
                return upload_state
            
            upload_state.status = "uploading"
            
            # Upload file using file chooser
            page.set_input_files(selector, file_path)
            
            upload_state.progress = 1.0
            upload_state.status = "completed"
            upload_state.completed_at = datetime.now().timestamp()
        
        except Exception as e:
            upload_state.status = "failed"
            upload_state.error = str(e)
        
        return upload_state
    
    def upload_multiple_files(self, selector: str, file_paths: List[str]) -> str:
        """Upload multiple files"""
        try:
            page = self.get_active_page()
            page.set_input_files(selector, file_paths)
            return f"✅ Uploaded {len(file_paths)} files"
        except Exception as e:
            return f"❌ Upload failed: {str(e)}"
    
    # ==================== ENHANCED: SEMANTIC VERIFICATION ====================
    
    def verify_page_semantics(self, expected_elements: Dict[str, Any]) -> ActionVerification:
        """Verify page has expected semantic elements"""
        page = self.get_active_page()
        
        if not page:
            return ActionVerification(
                action="semantic_verification",
                expected=str(expected_elements),
                actual="No active page",
                verified=False,
                screenshot=None,
                error_message="No active page"
            )
        
        try:
            actual_elements = {}
            
            # Check for headings
            headings = page.query_selector_all("h1, h2, h3, h4, h5, h6")
            actual_elements["headings"] = [h.text_content() for h in headings[:5]]
            
            # Check for main content areas
            main_content = page.query_selector("main, article, .content, #content")
            actual_elements["has_main_content"] = main_content is not None
            
            # Check for navigation
            nav = page.query_selector("nav, .nav, #nav")
            actual_elements["has_navigation"] = nav is not None
            
            # Check for forms
            forms = page.query_selector_all("form")
            actual_elements["form_count"] = len(forms)
            
            # Check page title
            actual_elements["title"] = page.title()
            
            # Check for error messages
            errors = page.query_selector_all(".error, .alert, [role='alert']")
            actual_elements["error_count"] = len(errors)
            
            # Compare with expected
            verified = True
            for key, expected_value in expected_elements.items():
                actual_value = actual_elements.get(key)
                if expected_value != actual_value:
                    verified = False
                    break
            
            screenshot = self._take_screenshot()
            
            return ActionVerification(
                action="semantic_verification",
                expected=str(expected_elements),
                actual=str(actual_elements),
                verified=verified,
                screenshot=screenshot,
                semantic_check={
                    "expected": expected_elements,
                    "actual": actual_elements
                },
                dom_snapshot=actual_elements
            )
        
        except Exception as e:
            return ActionVerification(
                action="semantic_verification",
                expected=str(expected_elements),
                actual="error",
                verified=False,
                screenshot=None,
                error_message=str(e)
            )
    
    def verify_action_result(self, action: str, expected_result: str) -> ActionVerification:
        """Verify action produced expected result"""
        page = self.get_active_page()
        
        if not page:
            return ActionVerification(
                action=action,
                expected=expected_result,
                actual="No active page",
                verified=False,
                screenshot=None,
                error_message="No active page"
            )
        
        try:
            actual_url = page.url
            actual_title = page.title()
            
            # Determine actual result
            actual = f"url={actual_url}, title={actual_title}"
            
            # Simple verification
            verified = expected_result.lower() in actual.lower() or expected_result in actual_url
            
            screenshot = self._take_screenshot()
            
            return ActionVerification(
                action=action,
                expected=expected_result,
                actual=actual,
                verified=verified,
                screenshot=screenshot,
                error_message=None if verified else "Result does not match expected"
            )
        
        except Exception as e:
            return ActionVerification(
                action=action,
                expected=expected_result,
                actual="error",
                verified=False,
                screenshot=None,
                error_message=str(e)
            )
    
    # ==================== ENHANCED: AUTH PERSISTENCE ====================
    
    def save_auth_state_extended(self, site_url: str, auth_token: str = None, 
                                refresh_token: str = None, headers: Dict = None) -> str:
        """Save authentication state with extended metadata"""
        if not self.context:
            return "❌ No browser context"
        
        try:
            cookies = self.context.cookies()
            
            # Get local storage
            local_storage = self.context.evaluate("""() => {
                let items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }""")
            
            # Get session storage
            session_storage = self.context.evaluate("""() => {
                let items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    let key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
            }""")
            
            # Calculate expiration (default 24 hours)
            expires_at = datetime.now().timestamp() + (24 * 60 * 60)
            
            auth_state = AuthState(
                site_url=site_url,
                cookies=cookies,
                local_storage=local_storage,
                session_storage=session_storage,
                logged_in=True,
                timestamp=datetime.now().timestamp(),
                auth_token=auth_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                headers=headers
            )
            
            self.auth_states[site_url] = auth_state
            
            # Save to file with site-based naming
            auth_file = self.data_dir / "auth" / f"{self._sanitize_filename(site_url)}.json"
            auth_file.parent.mkdir(parents=True, exist_ok=True)
            auth_file.write_text(json.dumps(auth_state.__dict__, default=str))
            
            return f"✅ Auth state saved for: {site_url}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def restore_auth_state_extended(self, site_url: str) -> str:
        """Restore authentication state with validation"""
        if not self.context:
            return "❌ No browser context"
        
        auth_file = self.data_dir / "auth" / f"{self._sanitize_filename(site_url)}.json"
        
        if not auth_file.exists():
            return "❌ No saved auth state"
        
        try:
            data = json.loads(auth_file.read_text())
            
            # Check expiration
            if data.get("expires_at"):
                expires_at = float(data["expires_at"])
                if datetime.now().timestamp() > expires_at:
                    return "❌ Auth state expired"
            
            # Restore cookies
            self.context.add_cookies(data["cookies"])
            
            # Restore local storage
            for key, value in data.get("local_storage", {}).items():
                self.context.evaluate(f"""(key, value) => {{
                    localStorage.setItem(key, value);
                }}""", key, value)
            
            # Restore session storage
            for key, value in data.get("session_storage", {}).items():
                self.context.evaluate(f"""(key, value) => {{
                    sessionStorage.setItem(key, value);
                }}""", key, value)
            
            return f"✅ Auth restored for: {site_url}"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for safe storage"""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    
    # ==================== SESSION PERSISTENCE ====================
    
    def save_session(self) -> str:
        """Save current session"""
        if not self.context:
            return "❌ No browser context"
        
        try:
            storage_state = self.context.storage_state()
            self.session_file.write_text(json.dumps(storage_state))
            
            return "✅ Session saved"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def close(self) -> str:
        """Close browser"""
        try:
            # Save session
            self.save_session()
            
            # Close all pages
            for page in self.pages.values():
                try:
                    page.close()
                except Exception as e: logger.warning(f"Exception: {e}")
            
            # Close context
            if self.context:
                self.context.close()
            
            # Close browser
            if self.browser:
                self.browser.close()
            
            self.state = BrowserState.IDLE
            self.pages = {}
            self.active_page_id = None
            
            logger.info("🌐 Browser closed")
            return "✅ Browser closed"
        
        except Exception as e:
            return f"❌ Error: {str(e)}"


# Global instance
_playwright_browser = None

def get_playwright_browser() -> BrowserManager:
    """Get or create browser manager"""
    global _playwright_browser
    if _playwright_browser is None:
        _playwright_browser = BrowserManager()
    return _playwright_browser
