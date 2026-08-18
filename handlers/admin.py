# handlers/admin.py
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from storage import mongo_repo as repo
from keyboards import admin_menu, cancel_kb
from middlewares import is_admin
from config import ADMIN_CHAT_ID
import time


# همان اندیس‌ها مثل bot.py
REG_TG_ID, REG_UUID, REG_ALLOW, \
DEL_TG_ID, DEL_UUID, \
CONN_TGID, CONN_TEXT, \
MSG_TGID, MSG_TEXT, \
MASS_MSG_TEXT = range(10)

MAX_TG_MSG = 4096
SAFE_CHUNK = 3800

# پیام‌ها
MESSAGES = {
    "admin_menu": "منوی ادمین 👇",
    "err_registration": "❌ خطا در ثبت:",
    "err_delete": "❌ خطا در حذف:",
    "err_send": "❌ خطا در ارسال:",
    "err_account_list": "❌ خطا در دریافت لیست کاربران:",
    "err_none_text": "⚠️ متن پیام نمی‌تواند خالی باشد.",
    "admin_access": "\n❌ شما دسترسی لازم را ندارید."
                    "⛔️ فقط ادمین می‌تواند این دستور را اجرا کند.",
    "cancelled": "❌ عملیات لغو شد.",
    "inter_id": "لطفاً شناسه تلگرام کاربر را ارسال کنید:",
    "inter_account": "✅ دریافت شد.\nحالا اکانت اشتراک کاربر را ارسال کنید:",
    "inter_ip_count": "✅ دریافت شد.\nتعداد اتصال مجاز (IP) را ارسال:",
    "inter_connection": "🔗 متن/لینک کانکشن را ارسال کنید:",
    "inter_text": "✉️ حالا پیام مورد نظر را بنویسید و بفرستید.",
    "connection_sended": "✅ کانکشن ارسال شد.",
    "text_sended": "✅ پیام با موفقیت ارسال شد.",
    "id_not_found": "❌ شناسه کاربر پیدا نشد. دوباره تلاش کنید.",
    "value_not_valid": "❗️ مقدار نامعتبر است. لطفا مقدار صحیح را وارد نمایید:",
    "select_account": "✅ دریافت شد.\nاکانت اشتراک کاربر را برای حذف را بفرستید.\n\nاکانت‌های کاربر",
    "select_account_notvalid": "✅ دریافت شد.\nاکانت اشتراک کاربر را برای حذف را بفرستید.\n(برای این کاربر چیزی در لیست پیدا نشد؛ مقدار درست را دستی وارد کنید.)",
    "purchased_with_referrer": "✅ سرویس شما ثبت شد! 🎉\n"
                    "🎁 پاداش توکن به حساب شما اضافه شد.\n"
                    "ممنون از اعتماد به VPN FreeLine 💙",
    "renewed_with_referred": "✅ سرویس/تمدید شما ثبت شد! 🔁\n"
                    "🪙 ۱ توکن به حساب شما اضافه شد.\n"
                    "ممنون از اعتماد به VPN FreeLine 💙",
    "purchased": "✅ سرویس شما ثبت شد! 🎉\n"
                    "ممنون از اعتماد به VPN FreeLine 💙",
    "referred_first_buy":  "🎉 یکی از دوستان معرفی‌شده توسط شما خرید انجام داد!\n"
                        "🪙 پاداش توکن برای شما واریز شد 👏",
    "referred_buy": "🔁 خرید/تمدید جدید از دوست معرفی‌شده شما ثبت شد!\n"
                        "🪙 ۱ توکن به حساب شما اضافه شد.\n"

}

# # ---------- لیست کاربران ----------
# async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if not is_admin(update.effective_user.id):
#         return
#     try:
#         rows = repo.get_all_users_subs()  # [(tg_id, uuid, allow_ip)]
#         if not rows:
#             await update.message.reply_text("هیچ کاربری ثبت نشده.", reply_markup=admin_menu)
#             return
#
#         grouped = {}
#         for tg_id, uuid, allow_ip in rows:
#             grouped.setdefault(tg_id, {"subs": [], "username": None, "full_name": None})
#             grouped[tg_id]["subs"].append((uuid, allow_ip))
#
#         for tg_id in list(grouped.keys()):
#             try:
#                 chat = await context.bot.get_chat(tg_id)
#                 username = chat.username or "-"
#                 if hasattr(chat, "full_name") and chat.full_name:
#                     full_name = chat.full_name
#                 else:
#                     first = getattr(chat, "first_name", "") or ""
#                     last = getattr(chat, "last_name", "") or ""
#                     full_name = (first + " " + last).strip() or "—"
#             except Exception:
#                 username = "-"
#                 full_name = "—"
#             grouped[tg_id]["username"] = username
#             grouped[tg_id]["full_name"] = full_name
#
#         ordered_users = sorted(grouped.items(), key=lambda x: x[0])
#
#         header = f"👥 تعداد کاربران: {len(ordered_users)}\n\n"
#         chunk = header
#         parts = []
#
#         for tg_id, data in ordered_users:
#             username = data["username"]
#             full_name = data["full_name"]
#             subs = sorted(data["subs"], key=lambda x: (str(x[0]).lower(), x[1]))
#
#             uname_part = f"(@{username})" if username and username != "-" else ""
#             name_part = f"{full_name}" if full_name and full_name != "—" else ""
#             display_name = (name_part + (" " if name_part and uname_part else "") + uname_part) or "بدون نام"
#
#             lines = [f"🆔 {tg_id}", f"👤 {display_name}"]
#             if subs:
#                 for uuid, allow_ip in subs:
#                     lines.append(f"   • {uuid} — IP≤{allow_ip}")
#             else:
#                 lines.append("   • (بدون اشتراک)")
#             block = "\n".join(lines) + "\n\n"
#
#             if len(chunk) + len(block) > SAFE_CHUNK:
#                 parts.append(chunk.rstrip())
#                 chunk = block
#             else:
#                 chunk += block
#
#         if chunk.strip():
#             parts.append(chunk.rstrip())
#
#         for i, text in enumerate(parts):
#             if i == 0:
#                 await update.message.reply_text(text, reply_markup=admin_menu)
#             else:
#                 await update.message.reply_text(text)
#
#     except Exception as e:
#         await update.message.reply_text(f"{MESSAGES["err_account_list"]} {e}", reply_markup=admin_menu)
# ---------- لیست کاربران ----------
async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        # ۱) کاربران دارای اشتراک
        rows = repo.get_all_users_subs() or []  # [(tg_id, uuid, allow_ip)]

        grouped = {}

        # پر کردن اطلاعات اشتراک‌ها
        for tg_id, uuid, allow_ip in rows:
            if is_admin(tg_id):
                continue  # ادمین‌ها تو لیست کاربران نیان
            grouped.setdefault(tg_id, {"subs": [], "username": None, "full_name": None})
            grouped[tg_id]["subs"].append((uuid, allow_ip))

        # ۲) همه کاربران ثبت‌شده (برای اضافه کردن بدون‌اشتراک‌ها)
        try:
            all_user_ids = list(repo.get_all_user_ids())
        except AttributeError:
            all_user_ids = []

        for tg_id in all_user_ids:
            if is_admin(tg_id):
                continue  # حذف ادمین‌ها
            grouped.setdefault(tg_id, {"subs": [], "username": None, "full_name": None})

        # اگر بعد از فیلتر هنوز چیزی نداریم
        if not grouped:
            await update.message.reply_text("هیچ کاربری ثبت نشده.", reply_markup=admin_menu)
            return

        # ۳) گرفتن نام و یوزرنیم هر کاربر
        for tg_id in list(grouped.keys()):
            try:
                chat = await context.bot.get_chat(tg_id)
                username = chat.username or "-"
                if getattr(chat, "full_name", None):
                    full_name = chat.full_name
                else:
                    first = getattr(chat, "first_name", "") or ""
                    last = getattr(chat, "last_name", "") or ""
                    full_name = (first + " " + last).strip() or "—"
            except Exception:
                username = "-"
                full_name = "—"

            grouped[tg_id]["username"] = username
            grouped[tg_id]["full_name"] = full_name

        # ۴) مرتب‌سازی:
        #    - اول کسانی که subs دارند (has_subs = True → گروه 0)
        #    - بعد کسانی که subs ندارند (has_subs = False → گروه 1)
        #    - داخل هر گروه بر اساس tg_id صعودی
        ordered_users = sorted(
            grouped.items(),
            key=lambda item: (
                0 if item[1]["subs"] else 1,
                item[0],
            )
        )

        header = f"👥 تعداد کاربران: {len(ordered_users)}\n"
        chunk = header
        parts = []

        for tg_id, data in ordered_users:
            username = data["username"]
            full_name = data["full_name"]
            subs = sorted(data["subs"], key=lambda x: (str(x[0]).lower(), x[1])) if data["subs"] else []

            uname_part = f"(@{username})" if username and username != "-" else ""
            name_part = f"{full_name}" if full_name and full_name != "—" else ""
            display_name = (name_part + (" " if name_part and uname_part else "") + uname_part) or "بدون نام"

            lines = [f"🆔 {tg_id}", f"👤 {display_name}"]
            if subs:
                for uuid, allow_ip in subs:
                    lines.append(f"   • {uuid} — IP≤{allow_ip}")
            else:
                lines.append("   • (بدون اشتراک)")
            block = "\n".join(lines) + "\n\n"

            if len(chunk) + len(block) > SAFE_CHUNK:
                parts.append(chunk.rstrip())
                chunk = block
            else:
                chunk += block

        if chunk.strip():
            parts.append(chunk.rstrip())

        # ۵) ارسال
        for i, text in enumerate(parts):
            if i == 0:
                await update.message.reply_text(text, reply_markup=admin_menu)
            else:
                await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"{MESSAGES['err_account_list']} {e}", reply_markup=admin_menu)
# ---------- ثبت کاربر ----------
async def admin_register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data.pop("reg_tg_id", None)
    context.user_data.pop("reg_uuid", None)
    context.user_data.pop("reg_allow", None)
    await update.message.reply_text(MESSAGES["inter_id"], reply_markup=cancel_kb)
    return REG_TG_ID

async def admin_register_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "❌ لغو":
        return await admin_cancel(update, context)
    txt = update.message.text.strip()
    if not txt.isdigit():
        await update.message.reply_text(MESSAGES["value_not_valid"])
        return REG_TG_ID
    context.user_data["reg_tg_id"] = int(txt)
    await update.message.reply_text(MESSAGES["inter_account"])
    return REG_UUID

async def admin_register_uuid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "❌ لغو":
        return await admin_cancel(update, context)
    uuid_txt = update.message.text.strip()
    if not uuid_txt:
        await update.message.reply_text(MESSAGES["value_not_valid"])
        return REG_UUID
    context.user_data["reg_uuid"] = uuid_txt
    await update.message.reply_text(MESSAGES["inter_ip_count"])
    return REG_ALLOW

async def admin_register_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "❌ لغو":
        return await admin_cancel(update, context)

    allow_txt = update.message.text.strip()
    if not allow_txt.isdigit():
        await update.message.reply_text(
            MESSAGES["value_not_valid"],
            reply_markup=cancel_kb
        )
        return REG_ALLOW

    allow_ip = int(allow_txt)
    tg_id = context.user_data.get("reg_tg_id")
    uuid = context.user_data.get("reg_uuid")

    # قبل از ثبت، وضعیت «اولین خرید» را تشخیص بدهیم تا پیام مناسب بفرستیم
    buyer_doc = repo.get_user(tg_id) or repo.upsert_user(tg_id)
    is_first_time = not bool(buyer_doc.get("first_purchase_done", False))
    ref_code = buyer_doc.get("referred_by")

    try:
        # یک order_id یکتا برای اتصال لاگ پاداش‌ها به این ثبت
        order_id = f"ORD-{tg_id}-{int(time.time())}"

        # فقط همین فراخوانی؛ هیچ mark_first... ای وجود ندارد
        # منطق پاداش «اولین خرید / خرید بعدی» داخل link_subscription اجرا می‌شود
        repo.link_subscription(tg_id, uuid, allow_ip, order_id=order_id)

        # پیام تایید ثبت به ادمین
        await update.message.reply_text(
            f"✅ اشتراک ثبت شد:\n"
            f"🌐 شناسه: {tg_id}\n"
            f"🔑 اکانت: {uuid}\n"
            f"🔢 اتصال مجاز: {allow_ip}\n"
        )

        # اطلاع‌رسانی به خریدار
        has_valid_referrer = False
        referrer_tg_id = None
        if ref_code:
            referrer_doc = repo.get_user_by_ref_code(ref_code)
            if referrer_doc and referrer_doc.get("telegram_id") != tg_id:
                has_valid_referrer = True
                referrer_tg_id = referrer_doc["telegram_id"]

        # پیام برای خریدار
        try:
            if has_valid_referrer:
                buyer_msg = (
                    MESSAGES["purchased_with_referrer"]
                    if is_first_time else
                    MESSAGES["renewed_with_referred"]
                )
            else:
                # بدون معرف → فقط تأیید سرویس، بدون اشاره به توکن
                buyer_msg = (
                    MESSAGES["purchased"]
                )
            await context.bot.send_message(tg_id, buyer_msg)
        except Exception:
            pass

        # اگر معرف دارد و خودارجاع نیست، به معرف هم خبر بده
        try:
            if ref_code:
                referrer_doc = repo.get_user_by_ref_code(ref_code)
                if referrer_doc and referrer_doc.get("telegram_id") != tg_id:
                    ref_msg = (
                        MESSAGES["referred_first_buy"]
                        if is_first_time else
                        MESSAGES["referred_buy"]
                    )
                    await context.bot.send_message(referrer_doc["telegram_id"], ref_msg)
        except Exception:
            pass

        # بازگشت به منوی ادمین
        await update.message.reply_text(MESSAGES["admin_menu"], reply_markup=admin_menu)

    except Exception as e:
        await update.message.reply_text(f'{MESSAGES["err_registration"]} {e}', reply_markup=admin_menu)

    # پاکسازی state‌ها
    context.user_data.pop("reg_tg_id", None)
    context.user_data.pop("reg_uuid", None)
    context.user_data.pop("reg_allow", None)
    return ConversationHandler.END

# ---------- حذف ----------
async def admin_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data.pop("del_tg_id", None)
    context.user_data.pop("del_uuid", None)
    await update.message.reply_text(MESSAGES["inter_id"], reply_markup=cancel_kb)
    return DEL_TG_ID

async def admin_delete_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "❌ لغو":
        return await admin_cancel(update, context)
    txt = update.message.text.strip()
    if not txt.isdigit():
        await update.message.reply_text(MESSAGES["value_not_valid"])
        return DEL_TG_ID

    tg_id = int(txt)
    context.user_data["del_tg_id"] = tg_id

    try:
        uuids = repo.get_user_subscriptions(tg_id) or []
    except Exception:
        uuids = []

    if uuids:
        view = "\n".join([f"• {u}" for u in uuids])
        await update.message.reply_text(
            f'{MESSAGES["select_account"]} {tg_id}:\n{view}'
        )
    else:
        await update.message.reply_text(
            MESSAGES["select_account_notvalid"]
        )
    return DEL_UUID

async def admin_delete_uuid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "❌ لغو":
        return await admin_cancel(update, context)
    uuid = update.message.text.strip()
    if not uuid:
        await update.message.reply_text(MESSAGES["value_not_valid"])
        return DEL_UUID

    tg_id = context.user_data.get("del_tg_id")
    try:
        repo.remove_subscription(tg_id, uuid)
        await update.message.reply_text(
            f"✅ اشتراک حذف شد:\n"
            f"🌐 شناسه: {tg_id}\n"
            f"🔑 اکانت: {uuid}",
        )
        await update.message.reply_text(MESSAGES["admin_menu"], reply_markup=admin_menu)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f'{MESSAGES["err_delete"]} {e}')

    context.user_data.pop("del_tg_id", None)
    context.user_data.pop("del_uuid", None)
    return ConversationHandler.END


# ---------- ارسال کانکشن ----------
async def admin_conn_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    # پاکسازی state قبلی
    context.user_data.pop("conn_tg_id", None)

    await update.message.reply_text(
        MESSAGES["inter_id"],  # "لطفاً شناسه تلگرام کاربر را ارسال کنید:"
        reply_markup=cancel_kb
    )
    return CONN_TGID


async def admin_conn_get_tgid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    # لغو
    if text in {"❌ لغو", "لغو"}:
        return await admin_cancel(update, context)

    if not text.isdigit():
        await update.message.reply_text(MESSAGES["value_not_valid"], reply_markup=cancel_kb)
        return CONN_TGID

    context.user_data["conn_tg_id"] = int(text)

    await update.message.reply_text(
        MESSAGES["inter_connection"],  # "🔗 متن/لینک کانکشن را ارسال کنید:"
        reply_markup=cancel_kb
    )
    return CONN_TEXT


async def admin_conn_get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()

    # لغو
    if txt in {"❌ لغو", "لغو"}:
        context.user_data.pop("conn_tg_id", None)
        await update.message.reply_text(MESSAGES["cancelled"], reply_markup=admin_menu)
        return ConversationHandler.END

    tg_id = context.user_data.get("conn_tg_id")
    if not tg_id:
        await update.message.reply_text(MESSAGES["id_not_found"], reply_markup=admin_menu)
        return ConversationHandler.END

    try:
        # ارسال کانکشن برای کاربر
        await context.bot.send_message(tg_id, txt)

        # فقط یک پیام تایید برای همین ادمین
        await update.message.reply_text(MESSAGES["connection_sended"], reply_markup=admin_menu)


    except Exception as e:
        await update.message.reply_text(
            f"{MESSAGES['err_send']} {e}",
            reply_markup=admin_menu
        )

    # پاک کردن state
    context.user_data.pop("conn_tg_id", None)
    return ConversationHandler.END

# ---------- پیام تکی ----------
def _is_cancel_text(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    import re
    t = re.sub(r"[\.!\u060C،…]+$", "", t).strip()
    return t in {"لغو", "❌ لغو", "❌لغو", "کنسل", "انصراف"}

async def admin_msg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.pop("msg_tg_id", None)
    await update.message.reply_text(MESSAGES["inter_id"], reply_markup=cancel_kb)
    return MSG_TGID

async def admin_msg_get_tgid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if _is_cancel_text(txt):
        context.user_data.pop("msg_tg_id", None)
        await update.message.reply_text(MESSAGES["cancelled"], reply_markup=admin_menu)
        return ConversationHandler.END
    if not txt.isdigit():
        await update.message.reply_text(MESSAGES["value_not_valid"], reply_markup=cancel_kb)
        return MSG_TGID
    context.user_data["msg_tg_id"] = int(txt)
    await update.message.reply_text(MESSAGES["inter_text"], reply_markup=cancel_kb)
    return MSG_TEXT

async def admin_msg_get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_text = (update.message.text or "").strip()
    if _is_cancel_text(admin_text):
        context.user_data.pop("msg_tg_id", None)
        await update.message.reply_text(MESSAGES["cancelled"], reply_markup=admin_menu)
        return ConversationHandler.END

    tg_id = context.user_data.get("msg_tg_id")
    if not tg_id:
        await update.message.reply_text(MESSAGES["id_not_found"], reply_markup=admin_menu)
        return ConversationHandler.END

    final_text = f"📩 پیام از پشتیبانی:\n\n{admin_text}"
    try:
        await context.bot.send_message(tg_id, final_text)
        await update.message.reply_text(MESSAGES["text_sended"], reply_markup=admin_menu)
    except Exception as e:
        await update.message.reply_text(f'{MESSAGES["err_send"]}{e}', reply_markup=admin_menu)

    context.user_data.pop("msg_tg_id", None)
    return ConversationHandler.END

# ---------- پیام انبوه ----------
async def admin_massmsg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    await update.message.reply_text(
        "✉️ لطفاً متن پیامی که می‌خواهید برای *همه کاربران* ارسال شود را بنویسید:",
        reply_markup=cancel_kb, parse_mode="Markdown"
    )
    return MASS_MSG_TEXT

async def admin_massmsg_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.error import Forbidden, BadRequest
    admin_text = (update.message.text or "").strip()
    if _is_cancel_text(admin_text):
        await update.message.reply_text(MESSAGES["cancelled"], reply_markup=admin_menu)
        return ConversationHandler.END
    if not admin_text:
        await update.message.reply_text(MESSAGES["err_none_text"], reply_markup=cancel_kb)
        return MASS_MSG_TEXT

    final_text = f"📩 پیام از پشتیبانی:\n\n{admin_text}"
    # rows = repo.get_all_users_subs()
    # unique_tg_ids = {tg_id for (tg_id, _, _) in rows}

    # # کاربرانی که حداقل یک اشتراک دارند
    # rows = repo.get_all_users_subs()
    # subs_ids = {tg_id for (tg_id, _, _) in rows}
    #
    # # همه کاربرانی که در ربات ثبت شده‌اند (حتی بدون اشتراک)
    # all_user_ids = set(repo.get_all_user_ids())
    #
    # # اجتماع هر دو: اشتراکی‌ها + فقط-استارت‌کرده‌ها
    # unique_tg_ids = all_user_ids | subs_ids

    unique_tg_ids = set(repo.get_all_user_ids())

    sent = failed = 0
    for tg_id in unique_tg_ids:
        try:
            if tg_id != ADMIN_CHAT_ID:
                await context.bot.send_message(tg_id, final_text)
                sent += 1

        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ پیام برای {sent} کاربر ارسال شد.\n⚠️ ناموفق: {failed} کاربر.", reply_markup=admin_menu)
    return ConversationHandler.END

# ---------- لغو ----------
async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["cancelled"])
    await update.message.reply_text(MESSAGES["admin_menu"], reply_markup=admin_menu)
    return ConversationHandler.END


async def approve_renew_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ادمین روی «اکانت تمدید شد» می‌زند → واریز توکن + اطلاع‌رسانی."""
    query = update.callback_query

    await query.answer()
    admin_id = query.from_user.id
    if not is_admin(admin_id):
        # فقط ادمین مجاز است
        await query.answer(MESSAGES["admin_access"], show_alert=True)
        return

    try:
        # approve_renew:<buyer_tg>:<order_id>
        _, buyer_str, order_id = (query.data or "").split(":", 2)
        buyer_tg = int(buyer_str)
    except Exception:
        await query.answer("دادهٔ دکمه نامعتبر است.", show_alert=True)
        return


    ok, msg = repo.reward_renewal(buyer_tg, order_id)

    # جمع کردن دکمه تا دوباره کلیک نشود
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    if ok:
        # --- پیام‌ها ---
        buyer_doc = repo.get_user(buyer_tg) or {}
        ref_code = buyer_doc.get("referred_by")
        referrer_doc = repo.get_user_by_ref_code(ref_code) if ref_code else None

        # پیام تایید برای ادمین
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"✅ تمدید تایید شد و توکن‌ها واریز شدند.\n🧾 order_id: {order_id}\n🆔 TG: {buyer_tg}"
        )

        # پیام برای خریدار
        try:
            refreshed_buyer = repo.get_user(buyer_tg) or {}
            await context.bot.send_message(
                chat_id=buyer_tg,
                text=(
                    f'{MESSAGES["renewed_with_referred"]}\n'
                    f"موجودی فعلی: {refreshed_buyer.get('tokens', 0)}\n"
                )
            )
        except Exception:
            pass

        # پیام برای معرف (اگر وجود داشته باشد و خودارجاع نباشد)
        if referrer_doc and referrer_doc.get("telegram_id") != buyer_tg:
            try:
                refreshed_ref = repo.get_user(referrer_doc["telegram_id"]) or {}
                await context.bot.send_message(
                    chat_id=referrer_doc["telegram_id"],
                    text=(
                        f'{MESSAGES["referred_buy"]}\n'
                        f"موجودی فعلی: {refreshed_ref.get('tokens', 0)}\n"
                    )
                )
            except Exception:
                pass
    else:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❌ عدم موفقیت در پاداش تمدید: {msg}\n🧾 order_id: {order_id}\n🆔 TG: {buyer_tg}"
        )