"""
OmniAgent X - Vision System (Ko'rish Qobiliyati)
================================================
Screenshot va ekran tahlili GPT-4 Vision orqali
"""
import os
import base64
import logging
from pathlib import Path
from typing import Optional, Tuple, List
import openai
from config import settings

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False


class VisionSystem:
    """
    Ko'rish tizimi - ekranni ko'rish va tahlil qilish
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
        logger.info("👁️ Vision System initialized")
    
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
                prompt = "Describe what's on this screen in detail. Include all visible UI elements, text, buttons, and any important information."
            
            # Send to GPT-4 Vision
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            analysis = response.choices[0].message.content
            logger.info(f"👁️ Screen analyzed successfully")
            
            return f"📸 **Ekranning tahlili:**\n\n{analysis}"
        
        except Exception as e:
            logger.error(f"❌ Vision error: {e}")
            return f"❌ Vision xatosi: {str(e)}\n\nEhtimol GPT-4 Vision API yoqilgan emas"
    
    def describe_screen(self) -> str:
        """
        Ekranni oddiy tarzda tasvirlash
        """
        return self.analyze_screenshot(prompt="Describe this screenshot simply. What applications are open? What is the user doing?")
    
    def find_element_on_screen(self, element_name: str) -> str:
        """
        Ekrandagi elementni topish (button, text, etc)
        """
        return self.analyze_screenshot(
            prompt=f"Find and describe any element related to '{element_name}' on this screen. Include its position, color, and what it does."
        )
    
    def read_screen_text(self) -> str:
        """
        Ekrandagi barcha matnni o'qish
        """
        return self.analyze_screenshot(
            prompt="Extract ALL text visible on this screen. Include every word, button label, menu item, notification, and any other text. List them in order."
        )
    
    def analyze_ui_elements(self) -> str:
        """
        UI elementlarni tahlil qilish
        """
        return self.analyze_screenshot(
            prompt="Analyze the UI elements on this screen. List all buttons, inputs, menus, and interactive elements with their positions and purposes."
        )
    
    def check_for_errors(self) -> str:
        """
        Xatolarni tekshirish
        """
        return self.analyze_screenshot(
            prompt="Look for any error messages, warnings, or unusual UI states on this screen. If there are any errors, describe them in detail."
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
            
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Compare these two screenshots. What changed between them? Describe the differences in detail."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{before_b64}"}},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{after_b64}"}}
                        ]
                    }
                ],
                max_tokens=500
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
        
        return f"📺 {screen_size}\n{mouse_pos}"


# Global instance
_vision_system = None

def get_vision_system(api_key: str = None):
    """Get or create vision system"""
    global _vision_system
    if _vision_system is None:
        key = api_key or os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        _vision_system = VisionSystem(key)
    return _vision_system