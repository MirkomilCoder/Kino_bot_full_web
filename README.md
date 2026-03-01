# Kino Bot Web App - Full Stack Next.js Application

Telegram Kino Bot uchun kompletli React + Next.js web aplikatsiya. Owner, Admin va User rollariga mos keladigan dashboard va funksiyalar bilan.

## 🚀 Xususiyatlar

### Owner Panel (Владелец)
- 📊 **Statistika** - Hamma narsaning statistikasini ko'rish
- 🎬 **Filmlar boshqarish** - Qo'shish, o'chirish, tahrirlash
- 📺 **Kanallar** - Kanal qo'shish va boshqarish  
- 👥 **Userlarni manage** - Bloqlab/oldib qo'yish
- 💬 **Support** - Hamma tickets va javoblarni ko'rish
- 📢 **Broadcast** - Hamma userlarga xabar yuborish

### Admin Panel (Администратор)
- 🎬 **Filmlar** - Qo'shish, o'chirish, tahrirlash
- 📺 **Kanallar** - Kanal qo'shish va boshqarish
- 👥 **Pользователи** - Bloqlab/oldib qo'yish
- 💬 **Support** - Ticketlarga javob berish
- 📢 **Broadcast** - Xabar tarqatish

### User Dashboard (Foydalanuvchi)
- 🎬 **Filmlar** - Qidirib, sortlab, pagina bilan ko'rish
- 👤 **Profil** - User statistikasi va ma'lumotlari
- 💬 **Support** - Adminlarga obuna yozing

## 📋 Talablar

- Node.js 18+
- npm / yarn / pnpm / bun
- Telegram Bot Token

## 🔧 O'rnatish va Setup

### 1. Dependencies o'rnatish

```bash
npm install
# yoki
pnpm install
# yoki
yarn install
```

### 2. Environment variables

`.env` fayliga qo'wing (`.env.example` dan koying):

```bash
cp .env.example .env
```

Keyin `.env` faylini to'ldiring:

```env
# Telegram Bot Configuration
MAIN_BOT_TOKEN=your_telegram_bot_token_here
MAIN_BOT_USERNAME=your_bot_username_here
OWNER_ID=your_telegram_id_here
ADMIN_IDS=admin_id_1,admin_id_2,admin_id_3

# Web App Configuration
WEB_APP_URL=https://your-domain.com/app
```

### 3. Database o'rnatish

```bash
npm run init:db
# yoki direct run
npx ts-node scripts/init-db.ts
```

Bu SQLite database ni va barcha tablelarni yaratadi.

### 4. Development serverini boshlash

```bash
npm run dev
```

Server `http://localhost:3000` da ishga tushadi.

## 📁 Proyekta Struktura

```
/app
  /api              # API routes
    /auth           # Authentication
    /admin          # Admin APIs
    /owner          # Owner APIs
    /user           # User APIs
    /support        # Support APIs
  /page.tsx         # Main app page
  /layout.tsx       # Root layout
  /globals.css      # Global styles

/components
  /dashboards       # Dashboard components
    /AdminDashboard.tsx
    /OwnerDashboard.tsx
    /UserDashboard.tsx
  /admin            # Admin components
  /user             # User components
  /owner            # Owner components
  /Header.tsx
  /AuthPage.tsx

/lib
  /db.ts            # Database operations
  /telegram-auth.ts # Telegram auth utilities
  /api-middleware.ts # API authentication

/scripts
  /init-db.ts       # Database initialization

/public            # Static files
```

## 🔐 Authentication

### Telegram Web App Validation

Bu aplikatsiya Telegram Web App signature validation ishlatadi:

1. Foydalanuvchi Telegram botda web app ochishi
2. Telegram Web App `initData` yuboradi (hashed va signed)
3. Backend validate qiladi hash orqali
4. User ma'lumotlari database ga saqlanadi
5. Session token qaytadi

**Security:**
- HMAC-SHA256 validation
- 24-hour token expiration
- HttpOnly cookies
- Role-based access control

## 🛠️ API Routes

### Authentication
- `POST /api/auth/login` - Telegram Web App login

### User APIs
- `GET /api/user/profile` - Get user profile
- `GET /api/movies` - Get movies list
- `GET /api/support/tickets` - Get user's tickets
- `POST /api/support/tickets` - Create support ticket

### Admin APIs
- `GET/POST/DELETE /api/admin/movies` - Movies management
- `GET/POST /api/admin/users` - Users management (ban/unban)
- `GET/POST /api/admin/channels` - Channels management
- `GET/POST /api/admin/support` - Support management
- `GET/POST /api/admin/broadcast` - Broadcast messages

### Owner APIs
- `GET /api/owner/stats` - System statistics

## 🎨 Styling

- **Tailwind CSS** - Utility-first CSS framework
- **Responsive Design** - Mobile-first approach
- **Custom Colors:**
  - Primary: `#1f2937`
  - Accent: `#3b82f6`
  - Success: `#10b981`
  - Warning: `#f59e0b`
  - Danger: `#ef4444`

## 🗄️ Database Schema

### Users Table
- `user_id` (Primary Key)
- `first_name`, `last_name`, `username`
- `joined_at`, `last_seen`

### Movies Table
- `code` (Primary Key)
- `file_id`, `file_type`
- `channel_id`, `message_id`
- `added_at`

### Support Tickets
- `id` (Auto increment)
- `user_id`, `message_text`, `status`
- `answer_text`, `answered_by`
- `created_at`, `answered_at`

### More Tables
- `blocked_users` - Bloklangan userlar
- `movie_channels` - Kanallar
- `admin_sessions` - Session management
- `broadcast_logs` - Broadcast history

## 📝 Deployment

### Vercel (Recommended)

```bash
# Push to GitHub
git push origin main

# Deploy via Vercel
# https://vercel.com/new
```

#### Environment Variables in Vercel
Settings → Environment Variables:
- `MAIN_BOT_TOKEN`
- `MAIN_BOT_USERNAME`
- `OWNER_ID`
- `ADMIN_IDS`
- `WEB_APP_URL`

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🐛 Debugging

Enable debug logs:
```javascript
// Logs appear in console as [v0] prefix
console.log("[v0] Message:", data);
```

## 📚 Bot Integration

### Telegram Bot Code Example

```python
from aiogram.types import WebAppInfo

# Web app button
web_app = WebAppInfo(url="https://your-domain.com/app")
button = InlineKeyboardButton(
    text="📱 Web App",
    web_app=web_app
)
```

## 🤝 Contributing

1. Create a feature branch
2. Commit changes
3. Push to branch
4. Open Pull Request

## 📄 License

MIT License

## 📞 Support

Agar muammolar bo'lsa, GitHub issues ga yozing yoki botga message yuboring.

---

**Created with ❤️ for Kino Bot**
