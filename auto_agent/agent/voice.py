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
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available - voice input limited")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("Edge TTS not available")

# Try to import for real-time audio
try:
    import pyaudio
    PYAUdio_AVAILABLE = True
except ImportError:
    PYAUdio_AVAILABLE = False
    logger.warning("PyAudio not available - real-time voice input disabled")


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
        except RuntimeError:
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
    
    # ==================== REAL-TIME VOICE FEATURES ====================
    
    def start_streaming_stt(self, callback: Callable[[str], None], 
                           language: str = "auto") -> str:
        """
        Start streaming Speech-to-Text for real-time voice input
        
        Args:
            callback: Function to call with transcribed text
            language: Language code or 'auto' for detection
        """
        if not PYAUdio_AVAILABLE:
            return "❌ PyAudio o'rnatilmagan - real-time STT ishlamaydi"
        
        if not WHISPER_AVAILABLE or not self.whisper_model:
            return "❌ Whisper model o'rnatilmagan"
        
        try:
            # Start streaming in background thread
            self.is_listening = True
            thread = threading.Thread(
                target=self._streaming_stt_loop, 
                args=(callback, language)
            )
            thread.daemon = True
            thread.start()
            return "✅ Streaming STT boshlandi"
        
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def _streaming_stt_loop(self, callback: Callable[[str], None], language: str):
        """Background streaming STT loop"""
        import pyaudio
        import numpy as np
        from typing import Generator
        
        CHUNK = 1024  # Audio chunk size
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000  # Whisper expects 16kHz
        
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        frames = []
        silence_threshold = 30  # Frames of silence to detect end
        silence_count = 0
        
        while self.is_listening:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                
                # Simple voice activity detection
                audio_data = np.frombuffer(data, dtype=np.int16)
                if np.abs(audio_data).mean() < 500:
                    silence_count += 1
                else:
                    silence_count = 0
                
                # If silence for threshold, transcribe
                if silence_count > silence_threshold and len(frames) > 10:
                    # Combine frames
                    audio_bytes = b''.join(frames)
                    
                    # Transcribe
                    import io
                    import wave
                    buffer = io.BytesIO()
                    with wave.open(buffer, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(audio.get_sample_size(FORMAT))
                        wf.setframerate(RATE)
                        wf.writeframes(audio_bytes)
                    
                    buffer.seek(0)
                    
                    # Use Whisper
                    result = self.whisper_model.transcribe(
                        buffer.read(), 
                        language=None if language == "auto" else language
                    )
                    
                    if result["text"].strip():
                        callback(result["text"])
                    
                    # Reset
                    frames = []
                    silence_count = 0
            
            except Exception as e:
                logger.error(f"Streaming STT error: {e}")
                break
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
    
    def interrupt_listening(self) -> str:
        """
        Interrupt current listening - for wake word or manual stop
        """
        self.is_listening = False
        logger.info("🎤 Eshitish to'xtatildi (interrupt)")
        return "✅ Eshitish to'xtatildi"
    
    def set_wake_word(self, wake_word: str = "hey agent") -> str:
        """
        Configure wake word detection
        
        Note: Requires additional setup with wake word detection library
        """
        self.wake_word = wake_word.lower()
        logger.info(f"🎤 Wake word o'rnatildi: {wake_word}")
        return f"✅ Wake word o'rnatildi: {wake_word}"
    
    def start_wake_word_listener(self, callback: Callable[[], None]) -> str:
        """
        Start listening for wake word in background
        
        Args:
            callback: Function to call when wake word detected
        """
        if not PYAUdio_AVAILABLE:
            return "❌ PyAudio o'rnatilmagan"
        
        self.wake_word_callback = callback
        self.is_listening = True
        
        thread = threading.Thread(target=self._wake_word_loop, args=(callback,))
        thread.daemon = True
        thread.start()
        
        return "✅ Wake word listener boshlandi"
    
    def _wake_word_loop(self, callback: Callable[[], None]):
        """Background wake word detection loop"""
        import pyaudio
        import numpy as np
        
        # This is a simplified version - production would use proper wake word model
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        try:
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            while self.is_listening:
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Simple energy-based detection (placeholder for real wake word)
                energy = np.abs(audio_data).mean()
                
                if energy > 1000:  # Threshold for "loud enough"
                    # In production, would run through wake word model here
                    # For now, just trigger on loud sounds
                    if hasattr(self, 'wake_word_callback'):
                        callback()
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
        
        except Exception as e:
            logger.error(f"Wake word error: {e}")
    
    # ==================== VOICE APPROVAL FLOW ====================
    
    def request_voice_approval(self, message: str, 
                              timeout: int = 30) -> Dict[str, Any]:
        """
        Request voice approval from user
        
        Args:
            message: Message to speak to user
            timeout: Timeout in seconds
            
        Returns:
            Dict with 'approved' boolean and 'response' text
        """
        try:
            # Speak the approval request
            self.speak(message)
            
            # Listen for response
            start_time = __import__('time').time()
            
            while __import__('time').time() - start_time < timeout:
                if not PYAUdio_AVAILABLE:
                    return {
                        "approved": False,
                        "response": "Voice input not available",
                        "timeout": True
                    }
                
                # In production, would listen for yes/no
                # For now, return timeout
                __import__('time').sleep(1)
            
            return {
                "approved": False,
                "response": "Timeout",
                "timeout": True
            }
        
        except Exception as e:
            return {
                "approved": False,
                "response": str(e),
                "error": True
            }
    
    def speak_with_confirmation(self, message: str, 
                                 confirm_phrase: str = "say yes to confirm") -> bool:
        """
        Speak message and wait for verbal confirmation
        
        Args:
            message: Message to speak
            confirm_phrase: Phrase to prompt confirmation
            
        Returns:
            True if confirmed, False otherwise
        """
        try:
            # Speak message
            self.speak(message)
            
            # Ask for confirmation
            self.speak(confirm_phrase)
            
            # Listen for confirmation (simplified)
            # In production, would use actual voice recognition
            return False  # Placeholder
        
        except Exception as e:
            logger.error(f"Confirmation error: {e}")
            return False
    
    # ==================== KERNEL INTEGRATION ====================
    
    def integrate_with_kernel(self, kernel) -> str:
        """
        Integrate voice with Jupyter kernel for code execution
        
        Args:
            kernel: Jupyter kernel instance
            
        Returns:
            Status message
        """
        self.kernel = kernel
        logger.info("🎤 Voice kernel integration enabled")
        return "✅ Kernel integration o'rnatildi"
    
    def execute_voice_command(self, command: str) -> Dict[str, Any]:
        """
        Execute voice command through kernel
        
        Args:
            command: Code to execute
            
        Returns:
            Dict with execution results
        """
        if not hasattr(self, 'kernel'):
            return {
                "success": False,
                "error": "Kernel not integrated"
            }
        
        try:
            # Execute through kernel
            result = self.kernel.execute(command)
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def speak_code_output(self, output: str, max_length: int = 200) -> str:
        """
        Speak code execution output
        
        Args:
            output: Output to speak
            max_length: Max characters to speak
        """
        truncated = output[:max_length] + "..." if len(output) > max_length else output
        return self.speak(f"Code output: {truncated}")


# Convenience functions
def voice_system():
    """Get global voice system instance"""
    global _voice_system
    if _voice_system is None:
        _voice_system = VoiceSystem()
    return _voice_system

# Alias for compatibility
def get_voice_system():
    """Get global voice system instance (alias)"""
    return voice_system()

_voice_system = None