from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from config import CHANNEL_USERNAME

# ====== منوی اصلی کاربران ======
main_menu = ReplyKeyboardMarkup(
    [
        ["🛒 خرید اکانت"],
        ["🕒 تمدید سرویس", "👤 گزارش اکانت من"],
        ["☎️ پشتیبانی", "📖 راهنما"],
        ["🎁 دعوت دوستان"],
        ["📱 دانلود اپ"]
    ],
    resize_keyboard=True
)

# ====== منوی انتخاب تعداد کاربران ======
user_count_menu = ReplyKeyboardMarkup([["🔑 دو کاربره", "🔑 تک کاربره"], ["🎁 اکانت رایگان با توکن"], ["⬅️ بازگشت"]], resize_keyboard=True)

# ====== منوی کانفیگ ۱ کاربران ======
user1_config_menu = ReplyKeyboardMarkup(
        [
            ["تک کاربره ۲۰ گیگ : ۷۰.۰۰۰ تومان", "تک کاربره ۱۰ گیگ : ۵۰.۰۰۰ تومان"],
            ["تک کاربره ۱۰۰ گیگ : ۱۵۰.۰۰۰ تومان", "تک کاربره ۵۰ گیگ : ۱۰۰.۰۰۰ تومان"],
            ["تک کاربره نامحدود گیگ : ۲۰۰.۰۰۰ تومان"], ["⬅️ بازگشت"]
        ], resize_keyboard=True
    )

# ====== منوی کانفیگ ۲ کاربران ======
user2_config_menu = ReplyKeyboardMarkup(
        [
            ["دو کاربره ۵۰ گیگ : ۱۲۰.۰۰۰ تومان", "دو کاربره ۲۰ گیگ : ۱۰۰.۰۰۰ تومان"],
            ["دو کاربره ۱۰۰ گیگ : ۲۰۰.۰۰۰ تومان"],
            ["دو کاربره نامحدود گیگ : ۲۰۰.۰۰۰ تومان"], ["⬅️ بازگشت"]
        ], resize_keyboard=True
    )

# ====== منوی دانلود اپ ======
download_app_menu = ReplyKeyboardMarkup(
    [
        ["🍎 آیفون", "🤖 اندروید"],
        ["🖥️ ویندوز", "💻 مک‌بوک"],
        ["⬅️ بازگشت"]
    ],
    resize_keyboard=True
)

# ====== منوی ادمین ======
admin_menu = ReplyKeyboardMarkup(
    [
        ["📋 لیست کاربران"],
        ["➕ ثبت کاربر", "🗑 حذف کاربر"],
        ["🔗 ارسال کانکشن"],
        ["✉️ پیام به کاربر", "📣 ارسال پیام انبوه"]
    ],
    resize_keyboard=True
)

# ====== سایر ======
cancel_kb = ReplyKeyboardMarkup([["❌ لغو"]], resize_keyboard=True)

def join_keyboard() -> InlineKeyboardMarkup:
    # داینامیک بر اساس CHANNEL_USERNAME
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 کانال اطلاع‌رسانی", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")],
        ]
    )

def token_redeem_inline():
    TOKEN_REDEEM_BTN_TEXT = "✅ دریافت اشتراک رایگان (۱۰ توکن)"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TOKEN_REDEEM_BTN_TEXT, callback_data="token_req")]
    ])


