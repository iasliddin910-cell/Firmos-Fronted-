# 🤖 OmniAgent X - To'liq Texnik Qo'llanma

## 📋 Umumiy Ko'rinish

**OmniAgent X** - bu zamonaviy sun'iy intellekt asosidagi avtonom agent bo'lib, foydalanuvchilar buyruqlariga muvofiq turli xil vazifalarni mustaqil ravishda bajaradi.

---

## 🎯 Asosiy Imkoniyatlar

### 1. 💬 Chat & Muloqot
- **Savol-javob**: Har qanday mavzuda savollarga javob beradi
- **Tushuntirish**: Murakkab tushunchalarni oddiy tilda tushuntiradi
- **Fikrlash jarayoni**: Think → Plan → Act → Observe → Verify → Repair

### 2. 🌐 Internet bilan Ishlash
- **Qidiruv**: Web qidiruv (DuckDuckGo)
- **Scraping**: Saytlardan ma'lumot yig'ish
- **Browser**: To'liq brauzer boshqaruvi (Playwright)

### 3. 💻 Dasturlash & Kod
- **Kod yozish**: Python, JavaScript, va boshqa tillarda
- **Kod bajarish**: Xavfsiz sandbox muhitida
- **Xatolar tuzatish**: Patch loop
- **Test yozish**: Avtomatik testlar

### 4. 📁 Fayl Boshqaruv
- **O'qish**: Har qanday faylni o'qish
- **Yozish**: Yangi fayllar yaratish
- **Qidirish**: Fayllarni nom bo'yicha izlash
- **Diff**: Fayllarni taqqoslash

### 5. 🖥️ Tizim Boshqaruv
- **Tizim ma'lumotlari**: CPU, RAM, disk haqida
- **Screenshot**: Ekran rasmini olish
- **Buyruqlar**: Terminal buyruqlarini ishga tushirish

### 6. 📱 Telegram Bot
- **Masofadan boshqarish**: Telegram orqali kompyuterni boshqarish
- **Buyruqlar**: /screenshot, /system, /files, /ask
- **Rate limiting**: Spamdan himoya
- **Admin tizimi**: Ruxsat etilgan foydalanuvchilar

---

## 🏗️ Arxitektura

```
┌─────────────────────────────────────────────┐
│                  OmniAgent X                  │
├─────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐│
│  │  GUI    │  │Telegram │  │    API     ││
│  └────┬────┘  └────┬────┘  └──────┬──────┘│
│       └────────────┼───────────────┘        │
│                    ▼                         │
│  ┌────────────────────────────────────────┐ │
│  │           Agent Core                    │ │
│  │  ┌───────────┐  ┌───────────────────┐  │ │
│  │  │UltimateBrain│  │Autonomous Engine │  │ │
│  │  │(ReAct+Ver) │  │(Real Planner)   │  │ │
│  │  └───────────┘  └───────────────────┘  │ │
│  └────────────────┬────────────────────────┘ │
│                   ▼                         │
│  ┌────────────────────────────────────────┐ │
│  │           Tools Engine                   │ │
│  │  • Registry  • Policy  • Audit Log       │ │
│  └────────────────┬────────────────────────┘ │
│                   ▼                         │
│  ┌────────────────────────────────────────┐ │
│  │           Memory System                 │ │
│  │  • Vector  • State  • History          │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 🔧 Texnik Xususiyatlar

### ReAct Pattern
1. **Think** - Vazifani tahlil
2. **Plan** - Amalni rejalashtirish (JSON)
3. **Act** - Amalni bajarish
4. **Observe** - Natijani kuzatish
5. **Verify** - Muvaffaqiyatni tekshirish
6. **Repair** - Xato bo'lsa tuzatish

### Tool Registry
- Args Schema, Timeout, Risk Level, Approval Level

### Xavfsizlik
- Command Policy (denylist/allowlist)
- Shell=False
- Rate Limiting (20 msg/min)

---

## ⚠️ Cheklovlar

### 1. APIga Bog'liqlik
- OpenAI API kerak (GPT-4)
- Token limitlari bor
- Har bir so'rov pullik

### 2. Vaqt Cheklovlari
- Max iterations: 10
- Tool timeout: 30-120 soniya

### 3. Xavfsizlik
- delete_file bloklangan
- Xavfli buyruqlar ro'yxati
- Telegram: faqat ruxsat etilgan foydalanuvchilar

### 4. Bilim Cheklovi
- Malumotlar 2024-yilgacha
- Real vaqtda yangilanmaydi

---

## 🚀 Foydalanish

```bash
cd auto_agent
pip install -r requirements.txt

# .env faylida:
# OPENAI_API_KEY=sk-...
# TELEGRAM_BOT_TOKEN=...

python main.py
```

### Telegram buyruqlar
```
/start - Boshlash
/help - Yordam
/screenshot - Screenshot
/ask <savol> - Savol
/files - Fayllar
```

---

*OmniAgent X - 2026*
