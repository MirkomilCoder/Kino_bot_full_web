# Setup Guide - Kino Bot Web App

Bu faylda qadim-qadim setup instructions bor.

## 1️⃣ Oldingi Preparation

### Flask App dan Migrate qilish

Agar siz Flask appdan migrate qilyapsan:

1. **Old database**dan backupini oling:
   ```bash
   cp app/data.sqlite3 data.sqlite3.backup
   ```

2. **Old movielar va users ni export** qiling (opsional - agar kerak bo'lsa)

## 2️⃣ Dependencies o'rnatish

```bash
npm install
# yoki
pnpm install
# yoki
yarn install
# yoki
bun install
```

Bu `node_modules` papkasini va barcha dependencieslarni o'rnatadi.

## 3️⃣ Environment Variables

### `.env` fayl yaratish

```bash
# Linux/Mac
cp .env.example .env

# Windows
copy .env.example .env
```

### `.env` ni to'ldirish

```env
# REQUIRED - Telegram Bot Settings
MAIN_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
MAIN_BOT_USERNAME=your_bot_username
OWNER_ID=123456789
ADMIN_IDS=987654321,111111111

# OPTIONAL - Web App URL (For production)
WEB_APP_URL=https://your-domain.com/app
```

**Qayerdan olish:**

1. **MAIN_BOT_TOKEN**: @BotFather bilan suhbat qilib "/token" buyrugi qo'ying
2. **MAIN_BOT_USERNAME**: Bot usernamenti yozing (@ belgisisiz)
3. **OWNER_ID**: `/start` commanda yuboring botga, logs da user ID ko'radi, yoki:
   ```bash
   python3 -c "from telegram import Bot; bot = Bot('TOKEN'); print(bot.get_me())"
   ```
4. **ADMIN_IDS**: Admin user IDlarini vergul bilan ajrating

## 4️⃣ Database o'rnatish

### SQLite Database yaratish

```bash
npm run init:db
```

Bu buyruq:
- `data.sqlite3` faylini yaratadi (agar yo'q bo'lsa)
- Barcha tablelarni create qiladi
- Schema ni setup qiladi

### Existing database dan migrate qilish

Agar siz Flask appdan data ko'chirmoqchi bo'lsangiz:

```bash
# Old Flask appdan backup olish
python3 -c "
import sqlite3
import shutil

# Backup
shutil.copy('app/data.sqlite3', 'data.sqlite3.backup')

# Data ko'chirish (manual yoki script yordamida)
"
```

## 5️⃣ Development serverini boshlash

```bash
npm run dev
```

Output:
```
> next dev

  ▲ Next.js 15.0.0
  - Local:        http://localhost:3000
```

Brauzeringizda `http://localhost:3000` ni oching.

## 6️⃣ Telegram Botga Web App qo'shish

### Python (aiogram) Example:

```python
from aiogram import types
from aiogram.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

# Web app button
web_app_button = InlineKeyboardButton(
    text="📱 Web App Ochish",
    web_app=WebAppInfo(url="http://localhost:3000")  # Development uchun
    # Production: url="https://your-domain.com/app"
)

keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])

# User ga xabar yuborish
await message.answer(
    "Web appni oching:",
    reply_markup=keyboard
)
```

### Node.js (telegram-bot-api) Example:

```javascript
const bot = new TelegramBot(TOKEN);

bot.onText(/start/, (msg) => {
  const chatId = msg.chat.id;
  
  const opts = {
    reply_markup: {
      inline_keyboard: [
        [
          {
            text: "📱 Web App Ochish",
            web_app: { url: "http://localhost:3000" }
          }
        ]
      ]
    }
  };
  
  bot.sendMessage(chatId, "Web appni oching:", opts);
});
```

## 7️⃣ Test qilish

### Login Test

1. Telegram botda web app tugmasini bosing
2. Web app ochiladi
3. Agar Telegram Web App bilan ochilgan bo'lsa, auto login qiladi
4. Rolini ko'radi:
   - Owner - Barcha panellar ko'radi
   - Admin - Admin panel
   - User - User dashboard

### Features Test

**Owner:**
- [ ] Statistics page ochiladi
- [ ] Filmlar add/edit/delete qilsa boladi
- [ ] Users manage qilsa boladi
- [ ] Broadcast yuborsa boladi

**Admin:**
- [ ] Filmlar manage qilsa boladi
- [ ] Support ticketlarga javob bersa boladi
- [ ] Users ban qilsa boladi

**User:**
- [ ] Filmlar qidiray boladi
- [ ] Profile ko'rsa boladi
- [ ] Support ticket yuborsa boladi

## 8️⃣ Production Deployment

### Vercel ga deploy

```bash
# 1. GitHub repositoryga push qiling
git push origin main

# 2. Vercel ga connect qiling
# https://vercel.com/new

# 3. Environment variables qo'ying
# Settings → Environment Variables:
MAIN_BOT_TOKEN=...
MAIN_BOT_USERNAME=...
OWNER_ID=...
ADMIN_IDS=...
WEB_APP_URL=https://your-project.vercel.app
```

### Own server ga deploy

```bash
# Build qilish
npm run build

# Start qilish
npm start

# Production: PORT=3000 npm start
```

### Docker bilan deploy

```bash
# 1. Build
docker build -t kino-bot-app .

# 2. Run
docker run -p 3000:3000 \
  -e MAIN_BOT_TOKEN=... \
  -e MAIN_BOT_USERNAME=... \
  -e OWNER_ID=... \
  -e ADMIN_IDS=... \
  kino-bot-app
```

## 9️⃣ Troubleshooting

### Database error: "Cannot find module 'better-sqlite3'"

```bash
# Solution
npm install better-sqlite3
# yoki
npm rebuild better-sqlite3
```

### Port 3000 already in use

```bash
# Other port bilan ishlatish
PORT=3001 npm run dev

# Or kill process
lsof -ti:3000 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :3000   # Windows
```

### Telegram Web App not available

- Telegram botda `web_app` button yordamida ochish kerak
- Browser console da test qila olmaysiz
- Telegram Desktop yoki mobile app ishlatish kerak

### Database lock error

```bash
# Database file ni delete qiling va qayta create qiling
rm data.sqlite3
npm run init:db
```

### OWNER_ID or ADMIN_IDS error

- `.env` fayldagi ID lar raqam bo'lishi kerak
- Virgul bilan qo'shish kerak: `987654321,111111111`
- Database reset qiling: `npm run init:db`

## 🔟 Advanced Setup

### Database backup

```bash
# Automatic backup script
cp data.sqlite3 data.sqlite3.$(date +%Y%m%d_%H%M%S).backup
```

### Custom domain

1. Your domain ni Vercel ga qo'ying
2. `.env` ni update qiling:
   ```env
   WEB_APP_URL=https://your-domain.com/app
   ```
3. Telegram bot web_app urlni update qiling

### Multi-admin setup

```env
ADMIN_IDS=admin1_id,admin2_id,admin3_id,admin4_id
```

---

## 📞 Help

Muammolar bo'lsa:

1. Console logs ni ko'ring: `npm run dev` output
2. `.env` settings ni double-check qiling
3. Database ni reset qiling: `npm run init:db`
4. Node version check: `node --version` (18+ kerak)
5. Cache clean: `rm -rf .next node_modules && npm install`

**Happy coding! 🚀**
