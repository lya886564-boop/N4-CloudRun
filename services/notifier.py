# services/notifier.py
import logging
from telegram.ext import ContextTypes
from config import ADMIN_CHAT_ID

logger = logging.getLogger(__name__)

async def send_to_admin(context: ContextTypes.DEFAULT_TYPE, message: str):
    """ارسال پیام به ادمین (اگر تنظیم شده باشد)."""
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(ADMIN_CHAT_ID, message)
        except Exception as e:
            logger.error(f"Failed to send message to admin: {e}")