"""
OmniAgent X - Vision System (Ko'rish Qobiliyati)
================================================
Screenshot va ekran tahlili GPT-4 Vision orqali

REFACTORED:
- Uses new OpenAI SDK
- Added OCR fallback (pytesseract)
- Coordinate grounding
- Screen state tracking
"""
import os
import base64
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import json

# NEW: Use new OpenAI SDK
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

# Try to import PIL for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - some features disabled")

# Try to import pytesseract for OCR fallback
try:
    import pytesseract
    OCR_AVAILABLE = True
except:
    OCR_AVAILABLE = False
    logger.warning("pytesseract not available - OCR fallback disabled")


class ScreenState:
    """Track screen state for diffing"""
    def __init__(self):
        self.last_screenshot: Optional[str] = None
        self.last_analysis: Optional[str] = None
        self.elements: List[Dict] = []
        self.text_content: List[str] = []
    
    def update(self, screenshot_path: str, analysis: str, elements: List[Dict]):
        self.last_screenshot = screenshot_path
        self.last_analysis = analysis
        self.elements = elements


class VisionSystem:
    """
    Ko'rish tizimi - ekranni ko'rish va tahlil qilish
    
    REFACTORED: Uses new OpenAI SDK with multimodal support
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # NEW: Use new OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Screen state tracking
        self.screen_state = ScreenState()
        
        # Model - use newer vision model
        self.vision_model = "gpt-4o"  # Latest multimodal model
        
        logger.info("👁️ Vision System initialized (NEW SDK)")
    
    def analyze_screenshot(self, image_path: str = None, prompt: str = None) -> str:
        """
        Screenshot ni tahlil qilish
        """
        try:
            # Take screenshot if path not provided
            if image_path is None:
                from agent.tools import ToolsEngine
                tools = ToolsEngine()
                result = tools.take_screenshot()
                # Extract path from result
                if "saqlandi:" in result:
                    image_path = result.split("saqlandi: ")[1].strip()
                else:
                    return "❌ Screenshot olish muvaffaqiyatsiz"
            
            # Check if file exists
            if not Path(image_path).exists():
                return f"❌ Rasm topilmadi: {image_path}"
            
            # Encode image to base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Default prompt if not provided
            if prompt is None:
                prompt = """Describe what's on this screen in detail. Include:
1. All visible UI elements (buttons, menus, inputs)
2. All text content
3. Colors and layout
4. Any error messages or warnings

Be specific about positions - use coordinates if helpful."""
            
            # NEW: Use new OpenAI SDK with vision
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500
            )
            
            analysis = response.choices[0].message.content
            
            # Update screen state
            self.screen_state.update(image_path, analysis, [])
            
            logger.info(f"👁️ Screen analyzed successfully")
            
            return f"📸 **Ekranning tahlili:**\n\n{analysis}"
        
        except Exception as e:
            logger.error(f"❌ Vision error: {e}")
            # Try OCR fallback if vision fails
            if OCR_AVAILABLE and image_path:
                return self._ocr_fallback(image_path)
            return f"❌ Vision xatosi: {str(e)}\n\nEhtimol GPT-4 Vision API yoqilgan emas"
    
    def _ocr_fallback(self, image_path: str) -> str:
        """OCR fallback using pytesseract"""
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            
            return f"""📸 **OCR Tahlil (Fallback):**

{text if text.strip() else "Matn topilmadi"}

*Note: GPT-4 Vision ishlamaydi, shuning uchun OCR ishlatildi*"""
        except Exception as e:
            return f"❌ OCR ham ishlamadi: {str(e)}"
    
    def get_coordinates(self, element_description: str) -> Optional[Tuple[int, int]]:
        """
        Get coordinates for an element on screen (grounding)
        """
        try:
            # Get current screenshot
            if not self.screen_state.last_screenshot:
                return None
            
            # Ask vision model to find coordinates
            with open(self.screen_state.last_screenshot, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            
            prompt = f"""Find the center coordinates of "{element_description}" on this screen.
If found, return ONLY a JSON object with x and y:
{{"x": number, "y": number}}

If not found, return: {{"found": false}}"""

            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=100
            )
            
            result_text = response.choices[0].message.content
            
            # Try to parse JSON
            try:
                # Extract JSON from response
                if "{" in result_text:
                    json_str = result_text[result_text.find("{"):result_text.rfind("}")+1]
                    data = json.loads(json_str)
                    
                    if "found" in data and not data["found"]:
                        return None
                    
                    return (data.get("x", 0), data.get("y", 0))
            except:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Coordinate grounding error: {e}")
            return None
    
    def describe_screen(self) -> str:
        """
        Ekranni oddiy tarzda tasvirlash
        """
        return self.analyze_screenshot(prompt="Describe this screenshot simply. What applications are open? What is the user doing?")
    
    def find_element_on_screen(self, element_name: str) -> str:
        """
        Ekrandagi elementni topish (button, text, etc)
        """
        # Try to get coordinates
        coords = self.get_coordinates(element_name)
        
        analysis = self.analyze_screenshot(
            prompt=f"Find and describe any element related to '{element_name}' on this screen. Include its position (top/bottom/left/right/center), color, and what it does."
        )
        
        if coords:
            analysis += f"\n\n🎯 **Koordinatalar:** x={coords[0]}, y={coords[1]}"
        
        return analysis
    
    def read_screen_text(self) -> str:
        """
        Ekandagi barcha matnni o'qish
        """
        return self.analyze_screenshot(
            prompt="Extract ALL text visible on this screen. Include every word, button label, menu item, notification, and any other text. List them in order."
        )
    
    def analyze_ui_elements(self) -> str:
        """
        UI elementlarni tahlil qilish
        """
        return self.analyze_screenshot(
            prompt="Analyze the UI elements on this screen. List all buttons, inputs, menus, and interactive elements with their positions and purposes. Format as a structured list."
        )
    
    def check_for_errors(self) -> str:
        """
        Xatolarni tekshirish
        """
        return self.analyze_screenshot(
            prompt="Look for any error messages, warnings, or unusual UI states on this screen. If there are any errors, describe them in detail with their positions."
        )
    
    def compare_screenshots(self, before_path: str, after_path: str) -> str:
        """
        Ikkita screenshot ni solishtirish
        """
        try:
            with open(before_path, "rb") as f:
                before_b64 = base64.b64encode(f.read()).decode('utf-8')
            with open(after_path, "rb") as f:
                after_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Compare these two screenshots. What changed between them? Describe the differences in detail. Be specific about what elements changed, moved, or disappeared."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{before_b64}"}},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{after_b64}"}}
                        ]
                    }
                ],
                max_tokens=800
            )
            
            return f"📸 **Solishtirish natijasi:**\n\n{response.choices[0].message.content}"
        
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def get_screen_info(self) -> str:
        """
        Ekran haqida umumiy ma'lumot
        """
        from agent.tools import ToolsEngine
        tools = ToolsEngine()
        
        screen_size = tools.get_screen_size()
        mouse_pos = tools.get_mouse_position()
        
        info = f"📺 {screen_size}\n{mouse_pos}"
        
        # Add last analysis info
        if self.screen_state.last_analysis:
            info += f"\n\n📝 Oxirgi tahlil: {self.screen_state.last_analysis[:200]}..."
        
        return info
    
    def get_element_confidence(self, element_description: str) -> Dict:
        """
        Get confidence score for element detection
        """
        analysis = self.analyze_screenshot(
            prompt=f"On a scale of 0-100, how confident are you that '{element_description}' exists on screen? Just give a number and brief reason."
        )
        
        # Try to extract confidence
        try:
            # Simple extraction - look for numbers
            import re
            numbers = re.findall(r'\d+', analysis[:100])
            if numbers:
                confidence = int(numbers[0])
                if confidence > 100:
                    confidence = min(confidence, 100)
                return {"confidence": confidence, "reasoning": analysis}
        except:
            pass
        
        return {"confidence": 0, "reasoning": analysis}


# Global instance
_vision_system = None

def get_vision_system(api_key: str = None):
    """Get or create vision system"""
    global _vision_system
    if _vision_system is None:
        key = api_key or os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        _vision_system = VisionSystem(key)
    return _vision_system
