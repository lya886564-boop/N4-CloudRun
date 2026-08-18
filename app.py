# app.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from config import BOT_TOKEN
from handlers import admin as Hadmin, client as Hclient, referral as Href
from jobs import xray_watch as J
from middlewares import on_error


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ----- Admin Conversations -----
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📋 لیست کاربران$"), Hadmin.admin_list_users))

    register_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^➕ ثبت کاربر$"), Hadmin.admin_register_start)],
        states={
            Hadmin.REG_TG_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_register_tg)],
            Hadmin.REG_UUID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_register_uuid)],
            Hadmin.REG_ALLOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_register_allow)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ لغو$"), Hadmin.admin_cancel)],
    )
    app.add_handler(register_conv)

    delete_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("^🗑 حذف کاربر$"), Hadmin.admin_delete_start)],
        states={
            Hadmin.DEL_TG_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_delete_tg)],
            Hadmin.DEL_UUID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_delete_uuid)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ لغو$"), Hadmin.admin_cancel)],
    )
    app.add_handler(delete_conv)

    conn_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔗 ارسال کانکشن$"), Hadmin.admin_conn_start)],
        states={
            Hadmin.CONN_TGID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_conn_get_tgid)],
            Hadmin.CONN_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_conn_get_text)],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ لغو$"), Hadmin.admin_cancel),
            CommandHandler("cancel", Hadmin.admin_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(conn_conv)

    msg_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✉️ پیام به کاربر$"), Hadmin.admin_msg_start)],
        states={
            Hadmin.MSG_TGID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_msg_get_tgid)],
            Hadmin.MSG_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_msg_get_text)],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ لغو$"), Hadmin.admin_cancel),
            CommandHandler("cancel", Hadmin.admin_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(msg_conv)

    mass_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📣 ارسال پیام انبوه$"), Hadmin.admin_massmsg_start)],
        states={Hadmin.MASS_MSG_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, Hadmin.admin_massmsg_send)]},
        fallbacks=[
            MessageHandler(filters.Regex("^❌ لغو$"), Hadmin.admin_cancel),
            CommandHandler("cancel", Hadmin.admin_cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(mass_conv)


    # ----- Client Commands -----
    app.add_handler(CommandHandler("start", Hclient.start))
    app.add_handler(CommandHandler("invite", Href.invite_menu))
    app.add_handler(CommandHandler("help", Hclient.help_message))

    # ----- Inline callbacks -----
    # app.add_handler(CallbackQueryHandler(Hclient.button_handler))

    # ----- Menus (Texts) -----

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("خرید اکانت"), Hclient.buy_account))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("دانلود اپ"), Hclient.app_download))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🔑 تک کاربره$"), Hclient.buy_account_one_user))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🔑 دو کاربره$"), Hclient.buy_account_two_user))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🎁 دعوت دوستان$"), Href.invite_menu))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("👤 گزارش اکانت من"), Hclient.account_report))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("🕒 تمدید سرویس"), Hclient.renew_service))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("☎️ پشتیبانی"), Hclient.support))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📖 راهنما"), Hclient.help_message))


    app.add_handler(CallbackQueryHandler(Hadmin.approve_renew_cb, pattern=r"^approve_renew:"))

    # هندلر عمومی موجود شما
    app.add_handler(CallbackQueryHandler(
        Hclient.button_handler,
        pattern=r"^(check_membership|back_to_main|renew:.+)$"
    ))

    # پلن‌ها (عین bot.py)
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(
            "تک کاربره ۱۰ گیگ : ۵۰.۰۰۰ تومان|تک کاربره ۲۰ گیگ : ۷۰.۰۰۰ تومان|تک کاربره ۵۰ گیگ : ۱۰۰.۰۰۰ تومان|تک کاربره ۱۰۰ گیگ : ۱۵۰.۰۰۰ تومان|تک کاربره نامحدود گیگ : ۲۰۰.۰۰۰ تومان"
        ),
        Hclient.handle_subscription_selection
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(
            "دو کاربره ۲۰ گیگ : ۱۰۰.۰۰۰ تومان|دو کاربره ۵۰ گیگ : ۱۲۰.۰۰۰ تومان|دو کاربره ۱۰۰ گیگ : ۲۰۰.۰۰۰ تومان|دو کاربره نامحدود گیگ : ۲۰۰.۰۰۰ تومان"
        ),
        Hclient.handle_subscription_selection
    ))



    # 🎁 اکانت رایگان با توکن
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("🎁 اکانت رایگان با توکن"),
            Hclient.token_free_entry
        )
    )

    # ----- Photo -----
    app.add_handler(MessageHandler(filters.PHOTO, Hclient.photo_handler))

    # ورود به مسیر توکنی (از منو)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🎁 اکانت رایگان با توکن$"), Hclient.token_free_entry))

    # کال‌بک‌های توکنی
    app.add_handler(CallbackQueryHandler(Hclient.token_req_cb, pattern=r"^token_req$"))
    app.add_handler(CallbackQueryHandler(Hclient.approve_token_cb, pattern=r"^approve_token:"))

    # ----- Other texts -----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, Hclient.text_handler))

    # ----- Activity ping (group=100) -----
    activity_filter = filters.TEXT & ~filters.COMMAND
    app.add_handler(MessageHandler(activity_filter, Hclient.activity_ping, block=False), group=100)

    # ----- Jobs -----
    app.job_queue.run_repeating(J.check_log_job, interval=180, first=5)
    app.job_queue.run_repeating(J.scheduled_auto_check, interval=3600, first=20)

    app.add_error_handler(on_error)

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()