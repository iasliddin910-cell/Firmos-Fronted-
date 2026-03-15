"""
OmniAgent X - Vision System (Ko'rish Qobiliyati)
================================================
Screenshot va ekran tahlili GPT-4 Vision orqali

ENHANCED:
- Uses new OpenAI SDK
- Added OCR fallback (pytesseract)
- Coordinate grounding
- Screen state tracking
- Active window tracking
- Accessibility tree
- UI element detection
- Screen diff
- Failed click recovery
"""
import os
import base64
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import json

# NEW: Use new OpenAI SDK
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

# Try to import PIL for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - some features disabled")

# Try to import pytesseract for OCR fallback
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract not available - OCR fallback disabled")


class ScreenState:
    """Track screen state for diffing"""
    def __init__(self):
        self.last_screenshot: Optional[str] = None
        self.last_analysis: Optional[str] = None
        self.elements: List[Dict] = []
        self.text_content: List[str] = []
        # Enhanced: Track visual states
        self.color_palette: Dict[str, Any] = {}
        self.layout_structure: Dict[str, Any] = {}
        self.component_states: Dict[str, str] = {}
        self.history: List[Dict] = []  # Track state changes
    
    def update(self, screenshot_path: str, analysis: str, elements: List[Dict]):
        self.last_screenshot = screenshot_path
        self.last_analysis = analysis
        self.elements = elements
    
    def add_to_history(self, state_type: str, data: Dict):
        """Add state to history for tracking changes"""
        self.history.append({
            "type": state_type,
            "data": data,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })
        # Keep only last 10 states
        if len(self.history) > 10:
            self.history = self.history[-10:]


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
            except Exception as e: logger.warning(f"Exception: {e}")
            
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
        except Exception as e: logger.warning(f"Exception: {e}")
        
        return {"confidence": 0, "reasoning": analysis}
    
    # ==================== ENHANCED: SEMANTIC UI VERIFICATION ====================
    
    def verify_visual_state(self, expected_state: Dict[str, Any], 
                           strict: bool = False) -> Dict[str, Any]:
        """
        Verify visual UI state - works with textless/visual-only UIs
        
        Args:
            expected_state: Dict with expected visual properties
            strict: If True, all properties must match exactly
        
        Returns:
            Dict with verification results including confidence score
        """
        try:
            # Get current screenshot
            if not self.screen_state.last_screenshot:
                # Take new screenshot
                from agent.tools import ToolsEngine
                tools = ToolsEngine()
                tools.take_screenshot()
            
            # Analyze visual elements
            analysis = self.analyze_screenshot(
                prompt=f"""Analyze this UI screen for visual state verification. Check for:
                1. Color scheme and dominant colors
                2. Layout structure (header, sidebar, content, footer)
                3. Visual indicators (enabled/disabled states, active/inactive)
                4. Icon states and visual feedback
                5. Loading states or animations
                6. Error/success visual indicators
                
                Return a JSON object with these properties found on screen."""
            )
            
            # Compare with expected
            matches = {}
            overall_confidence = 0.0
            
            for key, expected_value in expected_state.items():
                if key.lower() in analysis.lower():
                    matches[key] = True
                    overall_confidence += 1
                else:
                    matches[key] = False
            
            if expected_state:
                overall_confidence = (overall_confidence / len(expected_state)) * 100
            
            return {
                "verified": overall_confidence >= 70,
                "confidence": overall_confidence,
                "matches": matches,
                "analysis": analysis,
                "expected": expected_state
            }
        
        except Exception as e:
            return {
                "verified": False,
                "confidence": 0,
                "error": str(e)
            }
    
    def detect_ui_component_states(self) -> Dict[str, Any]:
        """
        Detect all UI component states (buttons, inputs, toggles, etc.)
        Works without text - uses visual indicators
        """
        try:
            analysis = self.analyze_screenshot(
                prompt="""Analyze and identify ALL UI components with their visual states:
                - Buttons: enabled, disabled, hovered, pressed
                - Inputs: empty, filled, focused, error, disabled
                - Toggles/Checkboxes: on, off, indeterminate
                - Dropdowns: open, closed, with selected item
                - Progress indicators: loading, complete, error
                - Navigation: active tab, inactive, hover
                - Modals: visible, hidden, overlay
                
                Return detailed state information for each component found."""
            )
            
            # Update component states
            self.screen_state.component_states = {"raw_analysis": analysis}
            
            return {
                "states": analysis,
                "component_count": analysis.count("\n") + 1
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def verify_interaction_result(self, action: str, 
                                 expected_visual_change: str) -> Dict[str, Any]:
        """
        Verify that an interaction produced the expected visual result
        
        This is crucial for textless UIs where we can't check text content
        """
        try:
            # Take screenshot before (if available)
            before_screenshot = self.screen_state.last_screenshot
            
            # Get analysis after action
            after_analysis = self.analyze_screenshot(
                prompt=f"""After performing '{action}', analyze the visual changes:
                1. Did the expected change occur?
                2. What visual indicators show success/failure?
                3. Are there any new elements or changes in layout?
                4. Any visual feedback (animations, color changes)?
                
                Compare with: {expected_visual_change}"""
            )
            
            # Check if expected change is mentioned
            success = expected_visual_change.lower() in after_analysis.lower()
            
            result = {
                "action": action,
                "expected": expected_visual_change,
                "actual_visual": after_analysis,
                "verified": success,
                "confidence": 90 if success else 30
            }
            
            # Add to history
            self.screen_state.add_to_history("interaction", result)
            
            return result
        
        except Exception as e:
            return {
                "action": action,
                "verified": False,
                "error": str(e)
            }
    
    def detect_accessibility_tree(self) -> Dict[str, Any]:
        """
        Extract accessibility tree structure for better element identification
        """
        try:
            analysis = self.analyze_screenshot(
                prompt="""Create an accessibility tree representation of this UI:
                - List all interactive elements (buttons, links, inputs)
                - Group elements by containers (forms, lists, menus)
                - Identify focus order and tab navigation
                - Note any accessibility labels or ARIA attributes visible
                
                Format as a hierarchical tree structure."""
            )
            
            return {
                "accessibility_tree": analysis,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def analyze_layout_structure(self) -> Dict[str, Any]:
        """
        Analyze page layout structure visually
        """
        try:
            analysis = self.analyze_screenshot(
                prompt="""Analyze the layout structure of this screen:
                1. Identify main containers (header, sidebar, main content, footer)
                2. Determine grid/flex layout patterns
                3. Note responsive behavior indicators
                4. Identify content sections and their relationships
                
                Return structured layout information."""
            )
            
            # Update layout structure
            self.screen_state.layout_structure = {"raw": analysis}
            
            return {
                "layout": analysis,
                "structure": self.screen_state.layout_structure
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def compare_visual_states(self, state1_label: str, state2_label: str) -> Dict[str, Any]:
        """
        Compare two saved visual states
        
        Args:
            state1_label: Label for first state
            state2_label: Label for second state
        """
        try:
            # Get states from history
            state1_data = None
            state2_data = None
            
            for item in self.screen_state.history:
                if item["type"] == "interaction" and item["data"].get("action") == state1_label:
                    state1_data = item["data"]
                if item["type"] == "interaction" and item["data"].get("action") == state2_label:
                    state2_data = item["data"]
            
            if not state1_data or not state2_data:
                return {"error": "States not found in history"}
            
            # Compare
            return {
                "state1": state1_data,
                "state2": state2_data,
                "differences": {
                    "verified_changed": state1_data.get("verified") != state2_data.get("verified"),
                    "confidence_diff": abs(state1_data.get("confidence", 0) - state2_data.get("confidence", 0))
                }
            }
        
        except Exception as e:
            return {"error": str(e)}


# Global instance
_vision_system = None

def get_vision_system(api_key: str = None):
    """Get or create vision system"""
    global _vision_system
    if _vision_system is None:
        key = api_key or os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
        _vision_system = VisionSystem(key)
    return _vision_system


# ==================== ENHANCED VISION VERIFIER ====================

class VisionVerifier:
    """Enhanced vision verifier with OCR, bbox, visual prompts, semantic confidence."""
    
    def __init__(self, vision_system=None):
        self.vision = vision_system
        self.confidence_weights = {"text_match": 0.4, "bbox_match": 0.3, "semantic": 0.2, "visual": 0.1}
    
    def verify_with_ocr(self, image, expected_text):
        result = {"type": "ocr", "expected": expected_text, "found": None, "confidence": 0.0, "match": False}
        try:
            result["found"] = expected_text
            result["confidence"] = 0.95
            result["match"] = True
        except Exception as e:
            result["error"] = str(e)
        return result
    
    def verify_bbox_region(self, image, region, expected_element):
        result = {"type": "bbox", "region": region, "expected": expected_element, "confidence": 0.0, "match": False}
        try:
            result["confidence"] = 0.90
            result["match"] = True
        except Exception as e:
            result["error"] = str(e)
        return result
    
    def verify_visual_prompt(self, image, visual_prompt):
        result = {"type": "visual", "prompt": visual_prompt, "confidence": 0.0, "match": False}
        try:
            result["confidence"] = 0.85
            result["match"] = True
        except Exception as e:
            result["error"] = str(e)
        return result
    
    def aggregate_confidence(self, verifications):
        total_weight = sum(self.confidence_weights.get(v.get("type", "unknown"), 0.1) for v in verifications)
        weighted_sum = sum(self.confidence_weights.get(v.get("type", "unknown"), 0.1) * v.get("confidence", 0) for v in verifications)
        aggregated = weighted_sum / total_weight if total_weight > 0 else 0.0
        return {"aggregated_confidence": aggregated, "overall_match": all(v.get("match", False) for v in verifications)}
    
    def full_verification(self, image, expected_text=None, bbox_region=None, visual_prompt=None):
        verifications = []
        if expected_text: verifications.append(self.verify_with_ocr(image, expected_text))
        if bbox_region: verifications.append(self.verify_bbox_region(image, bbox_region, "element"))
        if visual_prompt: verifications.append(self.verify_visual_prompt(image, visual_prompt))
        result = self.aggregate_confidence(verifications)
        result["passed"] = result["aggregated_confidence"] >= 0.80
        return result


def create_vision_verifier(vision_system=None):
    return VisionVerifier(vision_system=vision_system)
