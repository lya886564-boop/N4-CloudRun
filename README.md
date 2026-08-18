# 🚀 Telegram VPN Bot – Xray / XUI Full Manager

این پروژه یک **ربات تلگرام پیشرفته و ماژولار** برای مدیریت کامل کاربران VPN مبتنی بر **Xray / XUI** است.  
ربات دارای **پنل مجزای کاربر و ادمین داخل تلگرام** بوده و تمام عملیات بدون نیاز به پنل وب انجام می‌شود.

---

## 🎛️ پنل‌ها (Telegram-Based Panels)

### 👤 پنل کاربران
- ثبت خودکار کاربر در اولین ورود
- مشاهده وضعیت سرویس (حجم، انقضا، وضعیت)
- تمدید سرویس با یک کلیک (ارسال درخواست تمدید)
- دریافت لینک اتصال VPN
- سیستم دعوت دوستان و دریافت امتیاز (Referral)
- ارتباط با پشتیبانی

---

### 👑 پنل ادمین
- ثبت، لینک و حذف کاربران
- مدیریت محدودیت IP
- تمدید سرویس کاربران با یک کلیک
- ارسال پیام تکی یا همگانی (Broadcast)
- مشاهده لیست تمام کاربران ثبت‌شده
- دریافت هشدار استفاده غیرمجاز (IP Abuse)

---

## 🎁 سیستم Referral
- لینک دعوت اختصاصی برای هر کاربر
- دریافت امتیاز با دعوت کاربران جدید
- تبدیل امتیاز به تمدید سرویس یا حجم هدیه
- مدیریت کامل توسط ادمین

---

## 🧱 ساختار واقعی پروژه

```
vpnfreeline_bot/
├── app.py                     
├── config.py
├── keyboards.py
├── middlewares.py
│
├── handlers/
│   ├── admin.py
│   ├── client.py
│   ├── referral.py 
│
├── services/
│   ├── xui_sqlite.py
│   ├── notifier.py
│
├── jobs/
│   ├── xray_watch.py
│
├── storage/
│   ├── mongo_repo.py
│
├── requirements.txt
├── .env
└── README.md
```

---

## ⚙️ راه‌اندازی (Setup)

### ✅ پیش‌نیازها
- Python **3.10 یا بالاتر**
- دسترسی به سرور دارای:
  - **XUI Panel**
  - **Xray** (فعال بودن access.log)
- MongoDB (برای لاگ‌ها – اختیاری ولی توصیه‌شده)
- توکن ربات تلگرام از BotFather

---

### 1️⃣ نصب پروژه
```bash
git clone https://github.com/majid-abedi/vpn-telegram-bot.git
cd vpn-telegram-bot
pip install -r requirements.txt
```

---

### 2️⃣ ایجاد فایل `.env`
در ریشه پروژه یک فایل به نام `.env` بسازید:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_CHAT_ID=YOUR_TELEGRAM_ID
CARD_INFO=YOUR_BANK_CART_NUMBER
XUI_DB_PATH=ADDRESS_OF(x-ui.db)
XRAY_ACCESS_LOG=ADDRESS_OF(access.log)
MONGO_URI=mongodb://localhost:27017
CHANNEL_USERNAME=YOUR_TELEGRAM_CHANNEL_USERNAME
MONGO_URI=
MONGO_USER=
MONGO_PASS=
MONGO_DB=
```
---

### 3️⃣ اجرای ربات
```bash
python app.py
```

پس از اجرا، ربات آماده استفاده است و کاربران با `/start` وارد سیستم می‌شوند.

---

## 📜 License
MIT License

---

## ⭐ حمایت
اگر این پروژه براتون مفید بود، خوشحال می‌شم یک ⭐ به ریپازیتوری بدید.

---

# 🌐 English Overview

**Telegram VPN Bot** is a modular and production-ready Telegram bot designed to manage **Xray / XUI based VPN services**.

The bot provides **separate Telegram-based panels for users and administrators**, eliminating the need for a web dashboard.

---

## 🎛️ Panels

### 👤 User Panel
Each user is automatically registered on their first interaction with the bot.

User features:
- View VPN account status (usage, remaining quota, expiry date, active/inactive state)
- One-click service renewal request
- Receive VPN connection details
- Invite friends and earn rewards (Referral system)
- Contact support directly via the bot

---

### 👑 Admin Panel
Admin capabilities:
- Add, link, and remove users
- Set and enforce IP connection limits
- One-click service renewal for users
- Send messages:
  - To a specific user
  - To all registered users (broadcast)
- View and manage the full list of users who have ever interacted with the bot
- Receive real-time alerts for abnormal usage (excessive concurrent IPs)

---

## 🎁 Referral System
- Unique referral link for each user
- Earn points by inviting new users
- Redeem points for service renewal or bonus traffic
- Fully manageable by the admin

---

## 🛠️ Technology Stack
- Python 3.10+
- python-telegram-bot v20+
- SQLite (XUI database)
- MongoDB (logs & monitoring)
- APScheduler / background jobs
- python-dotenv

---


## ⭐ Support
If you find this project useful, please consider giving it a ⭐ on GitHub.
