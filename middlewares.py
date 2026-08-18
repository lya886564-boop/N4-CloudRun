# middlewares.py
import asyncio
import logging
import time

from telegram import Bot
from telegram.ext import ContextTypes
from config import CHANNEL_USERNAME, ADMIN_CHAT_ID
from storage import mongo_repo as repo


logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    # خروجی حتماً bool باشد
    return bool(ADMIN_CHAT_ID and user_id == ADMIN_CHAT_ID)

async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    """بررسی عضویت کاربر در کانال (True اگر عضو است)."""
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Membership check failed for {user_id}: {e}")
        return False

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    """هندلر خطای عمومی—لاگ و سکوت."""
    logger.exception("Unhandled exception while handling update: %s", context.error)

async def send_message_and_delete(bot: Bot, chat_id: int, text: str, reply_markup):
    message = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup
    )

    # حذف خودکار پیام منوی اصلی پس از 2 ثانیه
    await asyncio.sleep(2)
    try:
        await bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    except Exception:
        pass




async def touch_user_activity(context, tg_user):
    try:
        now = int(time.time())

        # آیا کاربر قبلاً در DB هست؟
        user_doc = repo.get_user(tg_user.id)

        if not user_doc:
            # اولین بار دیده می‌شود → بساز + اعلان «کاربر جدید»
            repo.upsert_user(tg_user.id, tg_user.username or "", tg_user.full_name or "")
            repo.set_last_seen(tg_user.id)

            if ADMIN_CHAT_ID:
                uname = f"@{tg_user.username}" if tg_user.username else "—"
                if tg_user.id != ADMIN_CHAT_ID:
                    await context.bot.send_message(
                        ADMIN_CHAT_ID,
                        f"🟩 کاربر جدید وارد شد\n\n"
                        f"👤 نام: {tg_user.full_name}\n"
                        f"🌐 یوزر: {uname}\n"
                        f"🪪 آیدی: {tg_user.id}\n"
                    )
            # از همین لحظه، تایمر اعلان را ست کن تا یک‌ساعتی بعد دوباره «فعال شد» بیاید
            repo.set_last_notification(tg_user.id, now)
            return

        # برای کاربرِ موجود: همیشه last_seen را تازه کن
        repo.set_last_seen(tg_user.id)

        # اگر از آخرین اعلان ≥ ۱ ساعت گذشته، یک «فعالسازی» بفرست
        last_notif = repo.get_last_notification(tg_user.id) or 0
        if now - int(last_notif) >= 3600:
            if ADMIN_CHAT_ID:
                uname = f"@{tg_user.username}" if tg_user.username else "—"
                if tg_user.id != ADMIN_CHAT_ID:
                    await context.bot.send_message(
                        ADMIN_CHAT_ID,
                        f"🟦 کاربر فعال شد\n\n"
                        f"👤 نام: {tg_user.full_name}\n"
                        f"🌐 یوزر: {uname}\n"
                        f"🪪 آیدی: {tg_user.id}\n"
                    )
            repo.set_last_notification(tg_user.id, now)

    except Exception as e:
        logger.warning(f"[touch_user_activity] error: {e}")