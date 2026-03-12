"""
OmniAgent X ULTIMATE - Playwright Browser Automation
======================================================
Full browser control with Playwright
"""
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available")


class PlaywrightBrowser:
    """
    Full browser automation with Playwright
    """
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_running = False
        
        if PLAYWRIGHT_AVAILABLE:
            try:
                self.playwright = sync_playwright().start()
                logger.info("🌐 Playwright initialized")
            except Exception as e:
                logger.warning(f"Playwright start failed: {e}")
    
    def start(self, headless: bool = False) -> str:
        """Start browser"""
        if not PLAYWRIGHT_AVAILABLE:
            return "❌ Playwright o'rnatilmagan. pip install playwright"
        
        try:
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.page = self.browser.new_page()
            self.is_running = True
            return "🌐 Brauzer ishga tushdi (Playwright)"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def navigate(self, url: str) -> str:
        """Navigate to URL"""
        if not self.is_running:
            return "❌ Brauzer ishlamaydi. Avval start() chaqiring"
        
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            return f"✅ {url} ga o'tildi"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def click(self, selector: str) -> str:
        """Click element"""
        try:
            self.page.click(selector)
            return f"✅ Element bosildi: {selector}"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def type(self, selector: str, text: str) -> str:
        """Type text into element"""
        try:
            self.page.fill(selector, text)
            return f"✅ Matn kiritildi: {text}"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def get_content(self) -> str:
        """Get page content"""
        if not self.is_running:
            return "❌ Brauzer ishlamaydi"
        return self.page.content()[:2000]
    
    def screenshot(self, path: str = None) -> str:
        """Take screenshot"""
        if not self.is_running:
            return "❌ Brauzer ishlamaydi"
        
        if not path:
            from datetime import datetime
            path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        try:
            self.page.screenshot(path=path)
            return f"📸 Screenshot saqlandi: {path}"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def evaluate(self, script: str) -> str:
        """Execute JavaScript"""
        if not self.is_running:
            return "❌ Brauzer ishlamaydi"
        
        try:
            result = self.page.evaluate(script)
            return f"JS natija: {str(result)[:500]}"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def wait_for_selector(self, selector: str, timeout: int = 5000) -> str:
        """Wait for element"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return f"✅ Element topildi: {selector}"
        except:
            return f"❌ Element topilmadi: {selector}"
    
    def close(self) -> str:
        """Close browser"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.is_running = False
            return "✅ Brauzer yopildi"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def get_cookies(self) -> str:
        """Get cookies"""
        if not self.is_running:
            return "❌ Brauzer ishlamaydi"
        
        cookies = self.page.context.cookies()
        return f"🍪 Cookie lar: {len(cookies)} ta"


_playwright = None

def get_playwright_browser():
    global _playwright
    if _playwright is None:
        _playwright = PlaywrightBrowser()
    return _playwright