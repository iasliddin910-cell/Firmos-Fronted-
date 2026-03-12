"""
OmniAgent X - User Interface
=============================
Modern dark-themed GUI using CustomTkinter
"""
import customtkinter as ctk
from tkinter import scrolledtext
import threading
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class AgentUI:
    """
    Modern GUI for OmniAgent X
    """
    
    def __init__(self, app_callback: Callable):
        self.app_callback = app_callback
        
        # Configure appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Colors
        self.COLORS = {
            "bg": "#0D1117",
            "panel": "#161B22",
            "accent": "#7C3AED",
            "text": "#E4E4E7",
            "success": "#10B981",
            "error": "#EF4444",
            "user_msg": "#1F2937",
            "ai_msg": "#2D2D44"
        }
        
        # State
        self.is_processing = False
        
        self._create_window()
        logger.info("🎨 UI initialized")
    
    def _create_window(self):
        """Create the main window"""
        self.window = ctk.CTk()
        self.window.title("🦾 OmniAgent X - Super Autonomous AI")
        self.window.geometry("1000x700")
        self.window.configure(fg_color=self.COLORS["bg"])
        
        # Configure grid
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(1, weight=1)
        
        # Create components
        self._create_sidebar()
        self._create_main_area()
        self._create_input_area()
        
        # Welcome message
        self.add_message("assistant", """🦾 **OmniAgent X** ga xush kelibsiz!

Men juda kuchli avtonom AI agentman. Quyidagi ishlarni bajarishim mumkin:

✅ **Kod yozish** - Har qanday dasturlash tilida kod yozish va ishga tushirish
✅ **Web qidiruv** - Internetda ma'lumot qidirish va saytlardan ma'lumot olish  
✅ **Fayl boshqaruv** - Fayllarni o'qish, yozish, o'chirish
✅ **Buyruq ishga tushirish** - Terminal buyruqlarini bajarish
✅ **Ma'lumotlar tahlili** - JSON, CSV, matnlarni tahlil qilish
✅ **Tizim ma'lumotlari** - Kompyuter haqida ma'lumot olish
✅ **Kiberxavsizlik** - Parol tahlili, tarmoq tekshirish

**Biron bir vazifa bering, men avtonom ravishda bajaram!**

Misol uchun:
- "Python da kalkulyator yarat"
- "Wikipedia haqida ma'lumot top"
- "Kompyuter tizimi haqida ma'lumot ber"
- "123456 parolining kuchini tekshir"
""")
    
    def _create_sidebar(self):
        """Create sidebar with quick actions"""
        self.sidebar = ctk.CTkFrame(
            self.window, 
            width=200, 
            corner_radius=0,
            fg_color=self.COLORS["panel"]
        )
        self.sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Title
        title = ctk.CTkLabel(
            self.sidebar,
            text="🦾 OmniAgent X",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.COLORS["accent"]
        )
        title.pack(pady=20)
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            self.sidebar,
            text="● Tayyor",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["success"]
        )
        self.status_label.pack(pady=5)
        
        # Quick actions
        actions_label = ctk.CTkLabel(
            self.sidebar,
            text="⚡ Tezkor amallar",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS["text"]
        )
        actions_label.pack(pady=(30, 10))
        
        # Action buttons
        self._create_action_button("💻 Kod ishga tushir", self._quick_code)
        self._create_action_button("🌐 Web qidiruv", self._quick_search)
        self._create_action_button("📁 Fayllar ro'yxati", self._quick_files)
        self._create_action_button("💾 Tizim ma'lumot", self._quick_system)
        self._create_action_button("⏰ Vaqt", self._quick_time)
        
        # Spacer
        spacer = ctk.CTkLabel(self.sidebar, text="")
        spacer.pack(expand=True)
        
        # Clear button
        clear_btn = ctk.CTkButton(
            self.sidebar,
            text="🗑️ Tozalash",
            command=self.clear_chat,
            fg_color="#EF4444",
            hover_color="#DC2626"
        )
        clear_btn.pack(pady=10, padx=20, fill="x")
    
    def _create_action_button(self, text: str, command: Callable):
        """Create a sidebar action button"""
        btn = ctk.CTkButton(
            self.sidebar,
            text=text,
            command=command,
            fg_color=self.COLORS["panel"],
            border_color=self.COLORS["accent"],
            border_width=1,
            hover_color=self.COLORS["accent"]
        )
        btn.pack(pady=5, padx=20, fill="x")
    
    def _create_main_area(self):
        """Create main chat area"""
        self.chat_frame = ctk.CTkFrame(
            self.window,
            fg_color="transparent"
        )
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame,
            font=("Segoe UI", 13),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            wrap="word",
            state="disabled",
            bd=0,
            highlightthickness=0
        )
        self.chat_display.pack(fill="both", expand=True)
        
        # Configure text tags for styling
        self.chat_display.tag_config("user", lmargin1=20, lmargin2=20, spacing1=10)
        self.chat_display.tag_config("assistant", lmargin1=20, lmargin2=20, spacing1=10)
    
    def _create_input_area(self):
        """Create input area at bottom"""
        self.input_frame = ctk.CTkFrame(
            self.window,
            height=80,
            fg_color=self.COLORS["panel"],
            corner_radius=0
        )
        self.input_frame.grid(row=2, column=1, sticky="ew")
        self.input_frame.grid_propagate(False)
        
        # Input field
        self.input_field = ctk.CTkEntry(
            self.input_frame,
            font=("Segoe UI", 14),
            placeholder_text="Vazifa kiriting... (Enter bilan jo'natish)",
            placeholder_text_color="#6B7280",
            fg_color=self.COLORS["bg"],
            border_color=self.COLORS["accent"],
            border_width=2,
            text_color=self.COLORS["text"]
        )
        self.input_field.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=15)
        self.input_field.bind("<Return>", self._on_submit)
        
        # Send button
        self.send_button = ctk.CTkButton(
            self.input_frame,
            text="🚀 Yuborish",
            command=self._on_submit,
            fg_color=self.COLORS["accent"],
            hover_color="#6D28D9",
            width=120,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.send_button.pack(side="right", padx=(10, 20), pady=15)
    
    def _on_submit(self, event=None):
        """Handle message submission"""
        if self.is_processing:
            return
        
        message = self.input_field.get().strip()
        if not message:
            return
        
        # Clear input
        self.input_field.delete(0, "end")
        
        # Add user message
        self.add_message("user", message)
        
        # Process in background thread
        self.is_processing = True
        self.update_status("🔄 Ishlanmoqda...", "warning")
        
        thread = threading.Thread(target=self._process_message, args=(message,))
        thread.daemon = True
        thread.start()
    
    def _process_message(self, message: str):
        """Process message in background"""
        try:
            response = self.app_callback(message)
            self.window.after(0, lambda: self.add_message("assistant", response))
        except Exception as e:
            logger.error(f"Error processing: {e}")
            self.window.after(0, lambda: self.add_message("assistant", f"❌ Xatolik: {str(e)}"))
        finally:
            self.window.after(0, self._finish_processing)
    
    def _finish_processing(self):
        """Called when processing is done"""
        self.is_processing = False
        self.update_status("● Tayyor", self.COLORS["success"])
    
    def add_message(self, role: str, content: str):
        """Add a message to the chat"""
        self.chat_display.configure(state="normal")
        
        # Determine styling
        if role == "user":
            prefix = "👤 Siz: "
            bg_color = self.COLORS["user_msg"]
            tag = "user"
        else:
            prefix = "🤖 OmniAgent: "
            bg_color = self.COLORS["ai_msg"]
            tag = "assistant"
        
        # Insert message
        self.chat_display.insert("end", f"\n{prefix}\n{content}\n", tag)
        
        # Scroll to bottom
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
    
    def update_status(self, text: str, color: str):
        """Update status indicator"""
        self.status_label.configure(text=text, text_color=color)
    
    def clear_chat(self):
        """Clear all messages"""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
    
    # Quick action handlers
    def _quick_code(self):
        self.input_field.insert(0, "Python da ")
        self.input_field.focus_set()
    
    def _quick_search(self):
        self.input_field.insert(0, "Internetda qidiruv: ")
        self.input_field.focus_set()
    
    def _quick_files(self):
        self.input_field.insert(0, "Fayllar ro'yxatini ko'rsat")
        self.input_field.focus_set()
    
    def _quick_system(self):
        self.input_field.insert(0, "Tizim haqida ma'lumot ber")
        self.input_field.focus_set()
    
    def _quick_time(self):
        self.input_field.insert(0, "Hozirgi vaqt qancha?")
        self.input_field.focus_set()
    
    def run(self):
        """Start the UI"""
        logger.info("🚀 Starting UI...")
        self.window.mainloop()
    
    def stop(self):
        """Stop the UI"""
        self.window.quit()