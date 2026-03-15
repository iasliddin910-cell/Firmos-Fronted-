# OmniAgent X foydalanuvchi qo'llanmasi

## 🚀 Bosqich 1: API kalitini sozlash

ChatGPT API kalitingizni quyidagi usullardan biri bilan o'rnating:

### Usul 1: .env fayl (tavsiya etiladi)
```bash
# Loyiha papkasida .env fayl yarating va quyidagini yozing:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Usul 2: Export buyrug'i (vaqtinchalik)
```bash
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### Usul 3: api_key.txt fayl (alternativ)
```bash
# api_key.txt fayl yarating va kalitni ichiga yozing
```

---

## 📥 2-qadam: Kutubxonalarni o'rnatish

```bash
cd auto_agent
pip install -r requirements.txt
```

---

## ▶️ 3-qadam: Ilovani ishga tushirish

```bash
python main.py
```

---

## 💬 Foydalanish

Ilova ishga tushganda, chat oynasida savolingizni yozing. Misollar:

| Buyruq | Natija |
|--------|--------|
| "Python da kalkulyator yarat" | Python kodi yaratadi va ishga tushiradi |
| "Internetda qidiruv: AI haqida" | Web qidiruv natijalarini ko'rsatadi |
| "tizim haqida ma'lumot ber" | Kompyuter ma'lumotlarini ko'rsatadi |
| "Fayllar ro'yxatini ko'rsat" | Joriy papkadagi fayllarni ko'rsatadi |
| "parolni tekshir: P@ssw0rd" | Parol kuchini tahlil qiladi |

---

## 🔧 Qo'shimcha imkoniyatlar

- **Sidebar**: Tezkor amallar tugmalari
- **Xotira**: Suhbat tarixini saqlaydi
- **Dark Theme**: Qora rangli interfeys

---

## ⚠️ Muhim eslatmalar

1. API kalitingiz maxfiy saqlang
2. Katta byudjetingiz borligini aytdingiz, lekin GPT-4 pullik - har bir so'rov uchun to'lov bor
3. Agar muammo bo'lsa, `python main.py` buyrug'ini terminalda ishga tushiring va xatolarni tekshiring

---

## 🔄 Yangilash

Kodni yangilash uchun:
```bash
git pull  # (agar Git repo bo'lsa)
pip install -r requirements.txt --upgrade
python main.py
```

---

## 📞 Yordam

Har qanday savollar bo'lsa, shunchaki so'rang!