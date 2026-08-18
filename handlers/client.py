# handlers/client.py
import time, re, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config import CHANNEL_USERNAME, ADMIN_CHAT_ID, CARD_INFO, DOWNLOAD_LINKS, XUI_DB_PATH
from middlewares import is_admin, send_message_and_delete, touch_user_activity
from storage import mongo_repo as repo
from services.xui_sqlite import get_xui_user_info
from keyboards import main_menu, admin_menu, join_keyboard, download_app_menu, cancel_kb, user_count_menu, \
    user1_config_menu, user2_config_menu, token_redeem_inline

logger = logging.getLogger(__name__)

# نگهدار انتخاب خرید تا ارسال فیش
user_subscription_choice = {}

# پیام‌ها
MESSAGES = {
    "welcome": "🚀 به FreeLine خوش اومدی 🚀\n"
               "سرویس VPN حرفه‌ای با زیرساخت اختصاصی! ⚡️\n\n"
                "سرویس اشتراکی و اختصاصی با بهره‌گیری از سرورهای پرقدرت در دیتاسنترهای اروپا، آلمان و فنلاند، "
                "اتصال پایدار و پرسرعت رو بدون محدودیت بهت ارائه می‌ده. 💪\n\n"
                "🚀 مناسب برای گیمینگ، استریم، کارهای حساس و کاربرانی که دنبال حداکثر سرعت و پایداری هستن.\n"
                "🚀 مناسب برای ترید چون IP ثابت هست.\n\n"
                "🔥 پشتیبانی ۲۴ ساعته برای بهترین تجربه ممکن.\n\n"
                "🎁 با دعوت دوستان، توکن جایزه بگیر و اشتراک رایگان فعال کن.\n"
                "👇 از منوی زیر شروع کن و به نسل جدید VPN‌ حرفه‌ای بپیوند:",
    "admin_welcome": "به پنل ادمین خوش آمدید",
    "not_member": "⚠️ کاربر گرامی؛ شما عضو چنل ما نیستید\n"
                  "از طریق دکمه زیر وارد کانال شده و عضو شوید\n"
                  "پس از عضویت دکمه «✅ بررسی عضویت» را بزنید",
    "join_prompt": "⚠️ هنوز عضو کانال نشده‌اید."
                   "\nلطفاً ابتدا عضو شوید و سپس روی «✅ بررسی عضویت» بزنید.",
    "membership_verified": "✅ عضویت شما تایید شد. حالا می‌توانید از ربات استفاده کنید.",
    "no_subscriptions": "❌ شما هیچ سرویسی برای تمدید ندارید.",
    "send_payment": "لطفاً عکس فیش واریزی را ارسال کنید تا درخواست تمدید سرویس بررسی شود.",
    "payment_sent": "✅ فیش واریزی برای تمدید سرویس ارسال شد. لطفاً منتظر تأیید ادمین باشید.",
    "payment_error": "❌ خطا در ارسال فیش. لطفاً دوباره تلاش کنید.",
    "invalid_state": "لطفاً ابتدا گزینه‌ای از منو (مثل خرید اکانت یا تمدید سرویس) انتخاب کنید.",
    "main_menu": "منوی اصلی 👇",
    "no_account": "📌 هیچ اکانتی برای شما در سیستم ثبت نشده است.",
    "invited_line": "✅ لینک دعوت شما ثبت شد.\n",
    "app_download": "لطفا نوع دستگاه خود را انتخاب کنید:",
    "account_type": "لطفا نوع اکانت خود را انتخاب کنید:",
    "account_volume": "لطفا حجم اکانت را انتخاب کنید:",
    "photo_sended": "✅ عکس فیش شما دریافت شد و به ادمین ارسال گردید.منتظر تایید باشید."
                    " متشکریم!",
    "free_account_request": "⏳ درخواست شما ثبت شد و برای ادمین ارسال گردید.",
    "free_account_accepted": "🎉 اشتراک رایگان شما تایید شد! \n"
                "به‌زودی لینک اتصال برای شما ارسال می‌شود.",
    "select_renewed": "لطفا سرویسی که می‌خواهید تمدید کنید را انتخاب کنید:",
    "account_renewed": "✅ اکانت شما تمدید شد",
    "support_menu": "📩 پیامت رو برای پشتیبانی بفرست.",
    "support_message_sended": "✅ پیام شما به پشتیبانی ارسال شد.",
    "cancelled": "⛔️ عملیات پشتیبانی لغو شد.",
    "telegram_channel": "📖 راهنما:\nبرای آموزش اتصال، به کانال ما بپیوندید:\nhttps://t.me/vpnfreeline",

}
MESSAGES["no_account"]

IGNORED_MENU_TEXTS = {
    "⬅️ بازگشت",
    "❌ لغو",
    "بازگشت",
    "لغو",
    "☎️ پشتیبانی",
    "📖 راهنما",
    "🕒 تمدید سرویس",
    "📱 دانلود اپ",
    "📋 لیست کاربران",
    "🔑 تک کاربره",
    "🔑 دو کاربره",
    "👤 گزارش اکانت من",
    "🛒 خرید اکانت",
    "🎁 دعوت دوستان",
}

# --- ابزار ---
async def check_channel_membership(bot, user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ("member","administrator","creator")
    except Exception:
        return False

# ---------- start (پشتیبانی از deep-link) ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # 1) استخراج ref_code از /start
    args = context.args or []
    ref_code = args[0][4:] if (args and str(args[0]).startswith("ref_")) else None

    # 2) ارسال پیام ورود به ادمین
    await touch_user_activity(context, user)

    # 4) اگر لینک دعوت بود → فقط یکبار ثبت شود (تابع repo خودش جلوی تکرار را می‌گیرد)
    # invited_line = ""
    if ref_code:
        repo.capture_ref_visit(ref_code, user.id)
        # invited_line = MESSAGES["invited_line"]

    # 3) ثبت/به‌روزرسانی کاربر و last_seen
    repo.upsert_user(user.id, user.username or "", user.full_name or "")
    repo.set_last_seen(user.id)



    # 5) الزام عضویت
    is_member = await check_channel_membership(context.bot, user.id)
    if not is_member:
        await update.message.reply_text(MESSAGES["not_member"], reply_markup=join_keyboard())
        return

    # 6) یک پیام نهایی تمیز
    if is_admin(user.id):
        await update.message.reply_text(
            f'{MESSAGES["admin_welcome"]}',
            reply_markup=admin_menu
        )
    else:
        await update.message.reply_text(
            f'{MESSAGES["welcome"]}',
            reply_markup=main_menu
        )

# ---------- Callback Buttons ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    await touch_user_activity(context, user)

    if query.data == "check_membership":
        try:
            if query.message:
                await query.message.delete()
        except Exception:
            pass

        is_member = await check_channel_membership(context.bot, user.id)
        if is_member:

            context.chat_data["suppress_activity_ping_once"] = True
            try:
                repo.set_last_seen(user.id)
            except Exception:
                pass

            await context.bot.send_message(
                user.id,
                MESSAGES["welcome"],
                reply_markup=(admin_menu if is_admin(user.id) else main_menu)
            )
        else:
            await context.bot.send_message(user.id, MESSAGES["join_prompt"], reply_markup=join_keyboard())
        return

    if query.data == "back_to_main":
        context.user_data["awaiting_payment"] = False
        context.user_data.pop("renew_uuid", None)
        user_subscription_choice.pop(user.id, None)

        context.chat_data["suppress_activity_ping_once"] = True

        try:
            if query.message:
                await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(user.id, MESSAGES["main_menu"], reply_markup=main_menu)
        # send_message_and_delete(context.bot, user.id, MESSAGES["main_menu"], main_menu)
        return

    if query.data.startswith("renew:"):
        uuid = query.data[len("renew:"):]
        context.user_data["renew_uuid"] = uuid
        context.user_data["awaiting_payment"] = True
        try:
            if query.message:
                await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            user.id, MESSAGES["send_payment"],
            reply_markup=ReplyKeyboardMarkup([["⬅️ بازگشت"]], resize_keyboard=True)
        )
        return

    logger.warning(f"Unhandled callback data: {query.data} for user {user.id}")

# ---------- activity ping (هر پیام کاربر، حداکثر هر ۱ ساعت یک بار) ----------
async def activity_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await touch_user_activity(context, user)

# ---------- منوی دانلود ----------
async def app_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["app_download"], reply_markup=download_app_menu)

# ---------- خرید اکانت ----------
async def buy_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["account_type"], reply_markup=user_count_menu)

async def buy_account_one_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["account_volume"], reply_markup=user1_config_menu)

async def buy_account_two_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["account_volume"], reply_markup=user2_config_menu)

async def handle_subscription_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "گیگ" in text or "نامحدود" in text:
        user_subscription_choice[update.effective_user.id] = text
        await update.message.reply_text(
            f"انتخاب شما: {text}\n\nلطفا مبلغ اشتراک را به شماره کارت\n{CARD_INFO}\nو عکس فیش واریزی را ارسال کنید."
        )
        return

# ---------- دریافت عکس (خرید/تمدید) ----------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    fullname = update.effective_user.full_name
    username = update.effective_user.username or "ندارد"

    # حالت خرید اکانت
    if user_id in user_subscription_choice:
        option_selected = user_subscription_choice[user_id]
        if ADMIN_CHAT_ID:
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=update.message.photo[-1].file_id,
                caption=f"نام: {fullname}\nیوزر تلگرام: @{username}\nشناسه تلگرام: {user_id}\nیک اشتراک ({option_selected}) خریداری کرد."
            )
        # پیام به کاربر + بازگشت به منو
        await update.message.reply_text(
            MESSAGES["photo_sended"],
            reply_markup=main_menu
        )
        # پاکسازی state خرید
        user_subscription_choice.pop(user_id, None)
        context.user_data.pop("awaiting_payment", None)
        context.user_data.pop("renew_uuid", None)
        return

    # حالت تمدید سرویس
    if context.user_data.get("renew_uuid"):
        uuid = context.user_data["renew_uuid"]
        order_id = f"REN-{user_id}-{int(time.time())}"

        if ADMIN_CHAT_ID:
            approve_cb = f"approve_renew:{user_id}:{order_id}"
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(MESSAGES["account_renewed"], callback_data=approve_cb)]]
            )

            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=update.message.photo[-1].file_id,
                caption=(
                    "📸 فیش واریزی برای تمدید سرویس\n"
                    f"👤 نام: {fullname}\n"
                    f"🔗 یوزرنیم: @{username}\n"
                    f"🌐 شناسه: {user_id}\n"
                    f"🔑 اکانت: {uuid}\n"
                    f"🧾 order_id: {order_id}\n\n"
                    "پس از شارژ در X-UI، روی دکمهٔ زیر بزن تا توکن‌ها واریز شوند."
                ),
                reply_markup=keyboard
            )

        await update.message.reply_text(MESSAGES["photo_sended"])
        context.user_data.pop("renew_uuid", None)
        context.user_data["awaiting_payment"] = False
        # برگشت به منو
        await update.message.reply_text(MESSAGES["main_menu"], reply_markup=main_menu)
        return

# ---------- تمدید سرویس ----------
async def renew_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    is_member = await check_channel_membership(context.bot, tg_id)
    if not is_member:
        await update.message.reply_text(MESSAGES["not_member"], reply_markup=join_keyboard())
        return

    uuids = repo.get_user_subscriptions(tg_id)
    if not uuids:
        await update.message.reply_text(MESSAGES["no_subscriptions"], reply_markup=main_menu)
        return

    buttons = []
    for uuid in uuids:
        info = get_xui_user_info(XUI_DB_PATH, uuid)
        if info:
            short_uuid = uuid[:15] + "..." if len(uuid) > 15 else uuid
            status = "فعال" if info["enable"] == 1 else "غیرفعال"
            buttons.append([InlineKeyboardButton(f"{short_uuid} ({status})", callback_data=f"renew:{uuid}")])
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back_to_main")])
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(MESSAGES["select_renewed"], reply_markup=keyboard)

# ---------- گزارش اکانت ----------
async def account_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    uuids = repo.get_user_subscriptions(tg_id)
    if not uuids:
        await update.message.reply_text(MESSAGES["no_account"], reply_markup=main_menu)
        return

    messages = []
    for uuid in uuids:
        info = get_xui_user_info(XUI_DB_PATH, uuid)
        if not info:
            messages.append(f"❌ اطلاعاتی برای اشتراک `{uuid}` پیدا نشد.")
            continue
        remain_text = info['remain'] if isinstance(info['remain'], str) else f"{info['remain']:.2f} گیگ"
        expiry_text = (f"⏳ تاریخ انقضا: {info['expire']} روز مانده" if info['expire'] > 0 else
                       "⏳ اکانت منقضی شده است." if info['expiry_ts'] else "⏳ تاریخ انقضا: نامشخص")
        messages.append(
            f"🔑 اکانت: `{info['uuid']}`\n"
            f"{'🟢' if info['enable'] == 1 else '🔴'} وضعیت: {'فعال' if info['enable'] == 1 else 'غیرفعال'}\n"
            f"📊 حجم کل: {info['total'] if info['total'] else 'نامحدود'} {'گیگ' if info['total'] else ''}\n"
            f"📉 مصرف شده: {info['used']:.2f} گیگ\n"
            f"📈 باقی‌مانده: {remain_text}\n"
            f"{expiry_text}\n"
        )
    await update.message.reply_text("\n\n".join(messages), parse_mode="Markdown")

# ---------- پشتیبانی ----------
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["support_mode"] = True
    await update.message.reply_text(
        MESSAGES["support_menu"],
        reply_markup=cancel_kb
    )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    tg_id = update.effective_user.id
    fullname = update.effective_user.full_name or ""
    username = update.effective_user.username or "ندارد"

    # --- الزام به عضویت برای کاربران غیرادمین ---
    if not is_admin(tg_id):
        is_member = await check_channel_membership(context.bot, tg_id)
        if not is_member:
            await update.message.reply_text(MESSAGES["join_prompt"], reply_markup=join_keyboard())
            # await update.message.reply_text(f"{CHANNEL_USERNAME}", reply_markup=join_keyboard())

            return

    # همیشه آخرین فعالیت ثبت شود (بدون ایجاد نوتیف)
    repo.set_last_seen(tg_id)

    # ================== حالت پشتیبانی ==================
    if context.user_data.get("support_mode"):
        # اگر کاربر لغو زد → خروج از حالت پشتیبانی و بازگشت به منوی اصلی
        if text in IGNORED_MENU_TEXTS:
            context.user_data["support_mode"] = False
            await update.message.reply_text(MESSAGES["cancelled"], reply_markup=main_menu)
            return

        # در غیر این صورت، پیام کاربر برای ادمین ارسال شود و در همین حالت بماند
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                ADMIN_CHAT_ID,
                f"📩 پیام پشتیبانی از {fullname} (@{username})\n🆔 {tg_id}\n\n{text}"
            )
        context.chat_data["suppress_activity_ping_once"] = True
        context.user_data["support_mode"] = False
        await update.message.reply_text(
            MESSAGES["support_message_sended"],
            reply_markup=main_menu
        )
        return
    # ===================================================
    # «بازگشت» خارج از حالت پشتیبانی → فقط منوی اصلی
    if text == "⬅️ بازگشت":
        await update.message.reply_text(MESSAGES["main_menu"], reply_markup=main_menu)
        return

    # منوی دانلود اپ
    if text in ["🍎 آیفون", "🤖 اندروید", "🖥️ ویندوز", "💻 مک‌بوک"]:
        label = text.replace("🍎 ", "").replace("🤖 ", "").replace("🖥️ ", "").replace("💻 ", "")
        link = DOWNLOAD_LINKS.get(label)
        await update.message.reply_text(f"لینک دانلود برای {text}:\n{link}", reply_markup=download_app_menu)
        return

# ---------- help ----------
async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["telegram_channel"])


TOKENS_COST = 10
async def token_free_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg = update.effective_user
    tokens = repo.get_tokens(tg.id)

    if tokens < TOKENS_COST:
        await update.message.reply_text(
            f"🚫 تعداد توکن کافی نیست.\n"
            f"توکن فعلی: {tokens}\n"
            f"نیاز: {TOKENS_COST}\n\n"
            f"با «دعوت دوستان» سریع توکن جمع کن ✨"
        )
        return

    await update.message.reply_text(
        "🎁 اکانت رایگان با توکن \n\n"
        f"توکن فعلی: {tokens}\n"
        f"هزینه: {TOKENS_COST}\n\n"
        "اگر تایید می‌کنی، دکمه زیر را بزن.",
        reply_markup=token_redeem_inline()
    )

async def token_req_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user

    # چک مجدد توکن (برای race-safe)
    tokens = repo.get_tokens(user.id)
    if tokens < TOKENS_COST:
        await q.edit_message_text(f"🚫 تعداد توکن کافی نیست. فعلی: {tokens} / نیاز: {TOKENS_COST}")
        return

    # ساخت درخواست
    req = repo.create_token_redeem_request(user.id, allow_ip=1)
    req_id = req["request_id"]

    await q.edit_message_text(MESSAGES["free_account_request"])
    await context.bot.send_message(
        chat_id=q.message.chat_id,
        text=MESSAGES["main_menu"],
        reply_markup=main_menu  # این ReplyKeyboardMarkup است
    )

    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                ADMIN_CHAT_ID,
                (
                    "🎁 درخواست اشتراک توکنی (تک‌کاربره)\n"
                    f"🆔 {user.id}\n"
                    f"👤 {user.full_name} (@{user.username})\n"
                    f"req_id: {req_id}\n"
                    "با تایید شما ۱۰ توکن کسر می‌شود."
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ تایید اشتراک توکنی", callback_data=f"approve_token:{req_id}:{user.id}")
                ]])
            )
        except Exception:
            pass

async def approve_token_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        await q.answer("دسترسی ندارید.", show_alert=True)
        return

    try:
        _, req_id, buyer_str = (q.data or "").split(":", 2)
        buyer_tg = int(buyer_str)
    except Exception:
        await q.answer("داده دکمه نامعتبر است.", show_alert=True)
        return

    ok, msg = repo.approve_token_redeem(req_id, buyer_tg, cost=TOKENS_COST)

    try:
        await q.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    if ok:
        await context.bot.send_message(
            q.message.chat_id,
            f"✅ تایید شد و ۱۰ توکن کسر گردید.\nreq_id: {req_id}\n🆔 {buyer_tg}\nنوع: تک‌کاربره"
        )
        try:
            await context.bot.send_message(
                buyer_tg,
                MESSAGES["free_account_accepted"]
            )
        except Exception:
            pass
    else:
        await context.bot.send_message(
            q.message.chat_id,
            f"❌ عدم موفقیت: {msg}\nreq_id: {req_id}\n🆔 {buyer_tg}"
        )