# jobs/xray_watch.py
import os, re, time, logging, sqlite3
from datetime import datetime
from telegram.ext import ContextTypes
from config import XRAY_ACCESS_LOG, ADMIN_CHAT_ID, XUI_DB_PATH

from storage import mongo_repo as repo

logger = logging.getLogger(__name__)

# ---------------- تنظیمات ----------------
INTERVAL_SECONDS        = 180           # هر 3 دقیقه
MAX_BYTES_PER_TICK      = 2_000_000     # 2MB
RECENT_WINDOW_SECS      = 10 * 60       # 10 دقیقه
CONCURRENCY_WINDOW_SECS = 240           # 4 دقیقه
HANDOFF_GRACE_SECS      = 90            # 90 ثانیه
MIN_HITS_PER_IP         = 5
VIOLATION_STREAK_REQUIRED = 3
WARN_COOLDOWN_SECS      = 60 * 60       # 1 ساعت

LOW_GB_THRESHOLD        = 1.0           # هشدار حجم کمتر از 1GB
EXPIRY_THRESHOLD_DAYS   = 3             # هشدار انقضا کمتر از 3 روز

# ---------------- وضعیت داخلی ----------------
last_log_pos = 0
recent_seen = {}              # { email -> { ip -> {"first": ts, "last": ts, "count": n} } }
last_ip_warn_by_email = {}    # { email -> last_warn_ts }
violation_streak_by_email = {}# { email -> count }
last_low_gb_warn_by_uuid = {} # { uuid -> ts }
last_expiry_warn_by_uuid = {} # { uuid -> ts }

EMAIL_RE = re.compile(r'email:\s*([^\s]+)')
SRC_RE   = re.compile(r'from\s+(?:tcp:)?(\[?[0-9A-Fa-f:.]+\]?)(?::\d+)')

def _extract_email(line: str):
    m = EMAIL_RE.search(line)
    return m.group(1) if m else None

def _extract_src_ip(line: str):
    m = SRC_RE.search(line)
    if m:
        ip = m.group(1)
        if ip.startswith('[') and ip.endswith(']'):
            ip = ip[1:-1]
        return ip
    # fallback خیلی ساده
    try:
        first = line.split()[0]
        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', first) or ':' in first:
            return first
    except Exception:
        pass
    return None

async def check_log() -> list[tuple[int, str]]:
    """
    فایل لاگ Xray رو به صورت افزایشی می‌خونه و تخلف «تعداد IP هم‌زمان» رو تشخیص می‌ده.
    خروجی: [(chat_id, message), ...]
    """
    global last_log_pos, recent_seen, last_ip_warn_by_email, violation_streak_by_email

    now = time.time()
    if not XRAY_ACCESS_LOG:
        logger.warning("XRAY_ACCESS_LOG is not set.")
        return []

    # هندل rotate/truncate
    try:
        st = os.stat(XRAY_ACCESS_LOG)
        if last_log_pos > st.st_size:
            last_log_pos = 0
        if st.st_size == last_log_pos:
            return []
    except FileNotFoundError as e:
        logger.error(f"Xray log file not found: {e}")
        return []

    try:
        with open(XRAY_ACCESS_LOG, "rb") as f:
            f.seek(last_log_pos)
            to_read = min(MAX_BYTES_PER_TICK, st.st_size - last_log_pos)
            chunk = f.read(to_read)

        if not chunk:
            return []

        cut = chunk.rfind(b"\n")
        if cut == -1:
            return []

        process = chunk[:cut + 1]
        last_log_pos += cut + 1

        try:
            lines = process.decode("utf-8", errors="ignore").splitlines()
        except Exception:
            lines = process.decode(errors="ignore").splitlines()
    except Exception as e:
        logger.error(f"Failed reading XRAY_ACCESS_LOG: {e}")
        return []

    # پارس خطوط
    for line in lines:
        email = _extract_email(line)
        src_ip = _extract_src_ip(line)
        if not email or not src_ip:
            continue
        bucket = recent_seen.setdefault(email, {})
        meta = bucket.get(src_ip)
        if meta:
            meta["last"]  = now
            meta["count"] += 1
        else:
            bucket[src_ip] = {"first": now, "last": now, "count": 1}

    # پاکسازی
    cutoff = now - RECENT_WINDOW_SECS
    for email, ip_map in list(recent_seen.items()):
        for ip, meta in list(ip_map.items()):
            if meta["last"] < cutoff:
                del ip_map[ip]
        if not ip_map:
            del recent_seen[email]

    # بررسی تخلف‌ها
    alerts: list[tuple[int, str]] = []
    users = repo.get_all_users_subs()  # [(tg_id, uuid/email, allow_ip)]
    for tg_id, email_or_uuid, user_allow in users:
        email = email_or_uuid
        ip_map = recent_seen.get(email, {})

        active_now = [
            ip for ip, meta in ip_map.items()
            if (now - meta["last"] <= CONCURRENCY_WINDOW_SECS) and (meta["count"] >= MIN_HITS_PER_IP)
        ]
        active_count = len(active_now)

        if active_count > user_allow:
            if active_count == user_allow + 1:
                newest_first_ts = max(ip_map[ip]["first"] for ip in active_now)
                if (now - newest_first_ts) <= HANDOFF_GRACE_SECS:
                    continue
            violation_streak_by_email[email] = violation_streak_by_email.get(email, 0) + 1
        else:
            violation_streak_by_email[email] = 0

        if violation_streak_by_email[email] >= VIOLATION_STREAK_REQUIRED and active_count > user_allow:
            last_warn = last_ip_warn_by_email.get(email, 0)
            if now - last_warn >= WARN_COOLDOWN_SECS:
                # پیام به کاربر
                alerts.append((
                    tg_id,
                    "⚠️ اتصال بیش از حد مجاز شناسایی شد.\n"
                    f"اکانت: {email}\n"
                    "لطفاً فقط با تعداد دستگاه‌های مجاز متصل شوید.\n"
                    "در صورت تکرار، سرویس شما ممکن است محدود شود."
                ))
                # پیام به ادمین
                if ADMIN_CHAT_ID:
                    ip_list = ", ".join(sorted(active_now))
                    admin_msg = (
                        f"⚠️ هشدار نقض محدودیت IP\n"
                        f"اکانت: {email}\n"
                        f"حدمجاز: {user_allow} | فعلی: {active_count}\n"
                        f"آی‌پی‌های فعال: {ip_list}\n"
                        f"👤 TG: {tg_id}"
                    )
                    alerts.append((ADMIN_CHAT_ID, admin_msg))
                last_ip_warn_by_email[email] = now
                violation_streak_by_email[email] = 0

    return alerts

async def check_log_job(context: ContextTypes.DEFAULT_TYPE):
    alerts = await check_log()
    for chat_id, msg in alerts:
        try:
            await context.bot.send_message(chat_id, msg)
        except Exception as e:
            logger.warning(f"check_log_job: could not send to {chat_id}: {e}")

# ---------------- هشدار کمبود حجم/انقضا (X-UI) ----------------

def _read_xui_row(uuid: str):
    """خواندن وضعیت یک UUID از DB X-UI (فقط خواندنی)."""
    try:
        with sqlite3.connect(XUI_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT enable, email, up, down, expiry_time, total FROM client_traffics WHERE email=?",(uuid,))
            return cur.fetchone()
    except Exception as e:
        logger.error(f"XUI read error for {uuid}: {e}")
        return None

async def scheduled_auto_check(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    users = repo.get_all_users_subs()  # [(tg_id, uuid, allow_ip)]
    for tg_id, uuid, _ in users:
        row = _read_xui_row(uuid)
        if not row:
            continue
        enable, _, up, down, expiry_time, total = row

        if enable != 1:
            continue  # فقط فعال‌ها

        used = (up + down) / (1024**3)
        total_gb = (total / (1024**3)) if total and total > 0 else 0.0
        remain = (total_gb - used) if total_gb > 0 else "نامحدود"

        expiry_ts = (expiry_time / 1000) if (expiry_time and expiry_time > 0) else None
        is_expired_time = bool(expiry_ts and expiry_ts <= now)
        if is_expired_time:
            continue

        # هشدار حجم
        if isinstance(remain, float) and remain > 0 and remain < LOW_GB_THRESHOLD:
            last = last_low_gb_warn_by_uuid.get(uuid)
            if last is None or (now - last >= WARN_COOLDOWN_SECS):
                try:
                    await context.bot.send_message(
                        tg_id,
                        f"⚠️ هشدار: حجم باقی‌مانده اکانت `{uuid}` کمتر از {LOW_GB_THRESHOLD:.0f} گیگ است. لطفا تمدید کنید.",
                        parse_mode="Markdown"
                    )
                    last_low_gb_warn_by_uuid[uuid] = now
                except Exception:
                    pass

        # هشدار انقضا
        if expiry_ts:
            seconds_left = expiry_ts - now
            if seconds_left < EXPIRY_THRESHOLD_DAYS * 24 * 3600:
                last = last_expiry_warn_by_uuid.get(uuid)
                if last is None or (now - last >= WARN_COOLDOWN_SECS):
                    days_left = int(seconds_left // 86400)
                    try:
                        await context.bot.send_message(
                            tg_id,
                            f"⏳ یادآوری: اکانت `{uuid}` کمتر از {days_left} روز دیگر اعتبار دارد. لطفا تمدید کنید.",
                            parse_mode="Markdown"
                        )
                        last_expiry_warn_by_uuid[uuid] = now
                    except Exception:
                        pass