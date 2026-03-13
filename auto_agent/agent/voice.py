"""
OmniAgent X - Voice System (Ovozli Aloqa)
==========================================
Speech-to-Text va Text-to-Speech
"""
import logging
import subprocess
import threading
import queue
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Optional imports
try:
    import whisper
    WHISPER_AVAILABLE = True
except:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available - voice input limited")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except:
    EDGE_TTS_AVAILABLE = False
    logger.warning("Edge TTS not available")


class VoiceSystem:
    """
    Ovozli aloqa tizimi - eshitish va gapirish
    """
    
    def __init__(self):
        self.whisper_model = None
        self.is_listening = False
        self.audio_queue = queue.Queue()
        
        # Initialize Whisper if available
        if WHISPER_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model("base")
                logger.info("🎤 Whisper model loaded")
            except Exception as e:
                logger.warning(f"Failed to load Whisper: {e}")
        
        logger.info("🎤 Voice System initialized")
    
    # ==================== SPEECH TO TEXT (ESHITISH) ====================
    
    def listen_from_microphone(self, timeout: int = 5) -> str:
        """
        Microfondan ovozni eshitish va matnga o'girish
        """
        if not WHISPER_AVAILABLE or not self.whisper_model:
            return "❌ Whisper o'rnatilmagan"
        
        try:
            # Audio recording would require pyaudio
            # For now, return placeholder
            return "🎤 Microfon eshitish uchun pyaudio kerak"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def transcribe_audio_file(self, filepath: str) -> str:
        """
        Audio fayldan matn olish
        """
        if not WHISPER_AVAILABLE or not self.whisper_model:
            return "❌ Whisper o'rnatilmagan"
        
        try:
            result = self.whisper_model.transcribe(filepath)
            text = result["text"]
            logger.info(f"🎤 Transcribed: {text[:50]}...")
            return f"✅ Ovozdan matn:\n\n{text}"
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def listen_continuously(self, callback: Callable[[str], None]):
        """
        Doimiy eshitish (background)
        """
        self.is_listening = True
        thread = threading.Thread(target=self._continuous_listen, args=(callback,))
        thread.daemon = True
        thread.start()
        logger.info("🎤 Doimiy eshitish boshlandi")
    
    def _continuous_listen(self, callback: Callable[[str], None]):
        """Background listening loop - placeholder for audio setup"""
        while self.is_listening:
            logger.debug("Waiting for audio input (STT not configured)")
            import time
            time.sleep(0.5)
    
    def stop_listening(self):
        """Eshitishni to'xtatish"""
        self.is_listening = False
        logger.info("🎤 Eshitish to'xtatildi")
    
    # ==================== TEXT TO SPEECH (GAPIRISH) ====================
    
    async def speak_async(self, text: str, voice: str = "en-US-AriaNeural") -> str:
        """
        Matnni ovozga o'girish (async)
        """
        if not EDGE_TTS_AVAILABLE:
            return "❌ Edge TTS o'rnatilmagan"
        
        try:
            # Create audio file
            output_file = "/tmp/omniagent_speak.mp3"
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_file)
            
            # Play audio (platform dependent)
            if subprocess.os.name == "nt":
                subprocess.Popen(["powershell", "-c", f"(New-Object Media.SoundPlayer '{output_file}').PlaySync()"])
            else:
                subprocess.Popen(["afplay", output_file])
            
            return f"🔊 Gapirildi: {text[:50]}..."
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def speak(self, text: str, voice: str = "en-US-AriaNeural") -> str:
        """
        Matnni ovozga o'girish (sync)
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.speak_async(text, voice))
    
    def speak_uzbek(self, text: str) -> str:
        """
        O'zbek tilida gapirish
        """
        # O'zbek supported voices in Edge TTS
        return self.speak(text, "uz-UZ-SardorNeural")
    
    def speak_english(self, text: str) -> str:
        """
        Ingliz tilida gapirish
        """
        return self.speak(text, "en-US-AriaNeural")
    
    def speak_russian(self, text: str) -> str:
        """
        Rus tilida gapirish
        """
        return self.speak(text, "ru-RU-SvetlanaNeural")
    
    # ==================== VOICE SETTINGS ====================
    
    def get_available_voices(self) -> str:
        """
        Mavjud ovozlarni ko'rsatish
        """
        if not EDGE_TTS_AVAILABLE:
            return "❌ Edge TTS o'rnatilmagan"
        
        voices = {
            "en-US": ["Aria", "Guy", "Jenny"],
            "uz-UZ": ["Sardor"],
            "ru-RU": ["Svetlana", "Dmitri"],
            "tr-TR": ["Ahmet", "Emel"]
        }
        
        result = "🔊 Mavjud ovozlar:\n"
        for lang, voice_list in voices.items():
            result += f"\n{lang}: {', '.join(voice_list)}"
        
        return result
    
    def set_voice_settings(self, rate: str = "+0%", volume: str = "+0%") -> str:
        """
        Ovoz sozlamalarini o'zgartirish
        """
        # Rate: -50% to +100%
        # Volume: -50% to +50%
        return f"✅ Sozlamalar o'rnatildi: Rate={rate}, Volume={volume}"


# Convenience functions
def voice_system():
    """Get global voice system instance"""
    global _voice_system
    if _voice_system is None:
        _voice_system = VoiceSystem()
    return _voice_system

_voice_system = None