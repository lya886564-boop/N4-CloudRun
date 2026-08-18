# handlers/referral.py
from datetime import datetime
from urllib.parse import quote
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from storage import mongo_repo as repo

def _format_events(events: list[dict]) -> str:
    if not events:
        return "— رویدادی ثبت نشده است."
    lines = []
    for ev in events:
        reason = ev.get("reason", "-")
        change = ev.get("change", 0)
        ts = ev.get("ts")
        when = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts)
        lines.append(f"• {reason}: {change:+d} ({when})")
    return "\n".join(lines)

async def invite_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_info = await context.bot.get_me()

    overview = repo.get_ref_overview(
        tg_id=user.id,
        bot_username=bot_info.username,  # خود تلگرام یوزرنیم دقیق را می‌دهد
    )

    ref_code        = overview.get("ref_code", "-")
    deep_link       = overview.get("deep_link") or ""
    tokens          = overview.get("tokens", 0)
    to_next_reward  = overview.get("to_next_reward", 10)
    converted_count = overview.get("converted_count", 0)
    successful_count = overview.get("successful_count", 0)

    # متن اصلی با HTML تا لینک *کلیک‌پذیر و یک‌خطی* باشد
    text = (
        "🎁 <b>دعوت دوستان، جایزه بگیر!</b>\n\n"
        "با هر خرید دوستت از طریق لینک اختصاصی تو:\n"
        "• بار اول: هر دو نفر <b>۲ توکن</b> هدیه 🎉\n"
        "• هر خرید بعدی: هر دو نفر <b>۱ توکن</b> اضافه 🔁\n\n"
        "هر <b>۱۰ توکن</b> = یک ماه اشتراک <b>۱۰GB رایگان!</b> 🚀\n\n"
        f"🔗 <b>لینک اختصاصی تو:</b>\n"
        f'<a href="{deep_link}">{deep_link}</a>\n\n'  # ← یک خط و قابل کلیک
        f"🧾 <b>کد دعوت:</b> <code>{ref_code}</code>\n"
        f"🪙 <b>توکن‌ها:</b> <b>{tokens}</b>\n"
        f"🎯 <b>تا جایزه بعدی:</b> <b>{to_next_reward}</b> توکن باقی‌مانده\n"
        f"✅ <b>خریدهای موفق:</b> <b>{successful_count}</b>\n"
        "لینک رو براشون ارسال کن تا ثبت نام کنند\n"
    )

    # متن اشتراک‌گذاری
    share_text = (
        "🚀 من از VPN FreeLine استفاده می‌کنم\n"
        "پرسرعت، امن و بدون محدودیت! 🔒\n\n"
        "تو هم با این لینک ثبت‌نام کن تا هر دو 🎁 جایزه بگیریم 👇\n"
        f"{deep_link}\n\n"
        "⚡️ فیلترشکن واقعی یعنی FreeLine!"
    )

    # پارامترها را درست encode کن
    enc_url = quote(deep_link, safe='')
    enc_text = quote(share_text, safe='')

    # لینک‌های دکمه‌ها

    telegram_share_url = f"tg://msg?text={enc_text}"
    whatsapp_share_url = f"https://api.whatsapp.com/send?text={enc_text}"


    buttons = [
        [InlineKeyboardButton("📤 ارسال از طریق تلگرام", url=telegram_share_url)],
        [InlineKeyboardButton("💬 ارسال از طریق واتساپ", url=whatsapp_share_url)],
        # اگر خواستی فقط «ارسال لینک خام» هم داشته باشی:
        # [InlineKeyboardButton("🔗 فقط ارسال لینک", url=deep_link)],
    ]

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,   # پیش‌نمایش بزرگ لینک نگه نداریم
        reply_markup=InlineKeyboardMarkup(buttons)
    )