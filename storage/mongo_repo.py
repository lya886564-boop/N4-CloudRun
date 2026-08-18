from datetime import datetime
from pymongo import MongoClient, ASCENDING, ReturnDocument
import string, random
from config import MONGO_URI, MONGO_DB, MONGO_USER, MONGO_PASS
import certifi
import time
from pymongo.errors import OperationFailure, DuplicateKeyError




common_kwargs = dict(serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())

if MONGO_USER and MONGO_PASS:
    client = MongoClient(MONGO_URI, username=MONGO_USER, password=MONGO_PASS, **common_kwargs)
else:
    client = MongoClient(MONGO_URI, **common_kwargs)


db = client[MONGO_DB]

# ایندکس‌ها
db.users.create_index([("telegram_id", ASCENDING)], unique=True)
db.users.create_index([("ref_code", ASCENDING)], unique=True, sparse=True)
db.subscriptions.create_index([("telegram_id", ASCENDING)])
db.referrals.create_index([("referrer_ref_code", ASCENDING), ("referred_tg", ASCENDING)], unique=True, sparse=True)

try:
    db.tokens_history.create_index(
        [("order_id", ASCENDING), ("telegram_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"order_id": {"$type": "string"}}
    )
except OperationFailure:
    pass
# شمارش خرید/تمدید بر اساس (by, reason) سریع‌تر می‌شود
db.tokens_history.create_index([("by", ASCENDING), ("reason", ASCENDING)])

def _rand_code(n=7):
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))

# ---------- Users ----------
def upsert_user(telegram_id: int, username: str = "", fullname: str = ""):
    current_timestamp = int(time.time())

    user_document = db.users.find_one_and_update(
        {"telegram_id": telegram_id},
        {
            "$set": {
                "username": username,
                "fullname": fullname,
                "updated_at": current_timestamp,
            },
            "$setOnInsert": {
                "telegram_id": telegram_id,
                "created_at": current_timestamp,
                "tokens": 0,
                "first_purchase_done": False,   # ← اضافه شد
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    # اگر هنوز ref_code ندارد، تولید کن
    if not user_document.get("ref_code"):
        for _ in range(5):
            generated_code = _rand_code()
            if not db.users.find_one({"ref_code": generated_code}):
                user_document = db.users.find_one_and_update(
                    {"telegram_id": telegram_id},
                    {"$set": {"ref_code": generated_code}},
                    return_document=ReturnDocument.AFTER,
                )
                break

    return user_document

def get_user(tg_id: int):
    return db.users.find_one({"telegram_id": tg_id})

def get_all_user_ids() -> list[int]:
    return list(db.users.distinct("telegram_id"))

def set_last_seen(tg_id: int):
    db.users.update_one({"telegram_id": tg_id}, {"$set": {"last_seen": int(datetime.utcnow().timestamp())}})

def get_last_notification(tg_id: int) -> int | None:
    u = db.users.find_one({"telegram_id": tg_id}, {"last_notif": 1})
    return u.get("last_notif") if u else None

def set_last_notification(tg_id: int, ts: int):
    db.users.update_one({"telegram_id": tg_id}, {"$set": {"last_notif": ts}})

def get_user_by_ref_code(code: str):
    return db.users.find_one({"ref_code": code})

# ---------- Subscriptions (به جای جدول subscriptions در SQLite) ----------
def link_subscription(tg_id: int, uuid: str, allow_ip: int = 1, order_id: str | None = None):
    # ثبت/آپدیت سرویس
    db.subscriptions.update_one(
        {"telegram_id": tg_id, "uuid": uuid},
        {
            "$set": {"allow_ip": allow_ip, "updated_at": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )

    # اطمینان از وجود کاربر
    user_doc = get_user(tg_id) or upsert_user(tg_id)

    # اگر referrer ندارد، پاداش ارجاعی نداریم
    ref_code = user_doc.get("referred_by")
    if not ref_code:
        return

    referrer = get_user_by_ref_code(ref_code)
    if not referrer:
        return

    # ❌ جلوگیری از خودارجاع
    if referrer["telegram_id"] == tg_id:
        db.users.update_one({"telegram_id": tg_id}, {"$unset": {"referred_by": ""}})
        db.referrals.update_one(
            {"referrer_ref_code": ref_code, "referred_tg": tg_id},
            {"$set": {"self_referral_blocked": True}},
            upsert=True
        )
        return

    first_done = bool(user_doc.get("first_purchase_done", False))

    if not first_done:
        # اولین اختصاص/خرید → +۲ برای هر دو
        add_tokens(tg_id, +2, "first_purchase_bonus_buyer",   by=ref_code, order_id=order_id)
        add_tokens(referrer["telegram_id"], +2, "first_purchase_bonus_referrer", by=ref_code, order_id=order_id)

        db.users.update_one({"telegram_id": tg_id}, {"$set": {"first_purchase_done": True}})

        db.referrals.update_one(
            {"referrer_ref_code": ref_code, "referred_tg": tg_id},
            {
                "$set": {
                    "converted": True,
                    "converted_at": datetime.utcnow(),
                    "last_order_id": order_id,
                    "last_purchase_at": datetime.utcnow(),
                },
                "$setOnInsert": {"captured_at": datetime.utcnow()},
                "$inc": {"purchase_count": 1},
            },
            upsert=True
        )
    else:
        # خریدها/اختصاص‌های بعدی (غیر از تمدید تاییدشده‌ی ادمین) → +۱ برای هر دو
        add_tokens(tg_id, +1, "repeat_purchase_bonus_buyer",   by=ref_code, order_id=order_id)
        add_tokens(referrer["telegram_id"], +1, "repeat_purchase_bonus_referrer", by=ref_code, order_id=order_id)

        db.referrals.update_one(
            {"referrer_ref_code": ref_code, "referred_tg": tg_id},
            {
                "$set": {
                    "converted": True,
                    "last_order_id": order_id,
                    "last_purchase_at": datetime.utcnow(),
                },
                "$inc": {"purchase_count": 1},
            },
            upsert=True
        )

def remove_subscription(tg_id: int, uuid: str):
    db.subscriptions.delete_one({"telegram_id": tg_id, "uuid": uuid})

def get_user_subscriptions(tg_id: int) -> list[str]:
    cur = db.subscriptions.find({"telegram_id": tg_id}, {"uuid": 1})
    return [d["uuid"] for d in cur]

def get_all_users_subs() -> list[tuple[int, str, int]]:
    cur = db.subscriptions.find({}, {"telegram_id": 1, "uuid": 1, "allow_ip": 1})
    return [(d["telegram_id"], d["uuid"], d.get("allow_ip", 1)) for d in cur]

# ---------- Referral / Tokens ----------
def capture_ref_visit(ref_code: str, referred_tg: int):
    # پیدا کردن صاحب ref_code
    referrer = get_user_by_ref_code(ref_code)
    if not referrer:
        return  # ref_code نامعتبر

    # ❌ جلو خودارجاع: کاربر نمی‌تواند زیرمجموعه‌ی خودش باشد
    if referrer.get("telegram_id") == referred_tg:
        # می‌توانی برای آنالیتیکس لاگ هم ذخیره کنی
        db.referrals.update_one(
            {"referrer_ref_code": ref_code, "referred_tg": referred_tg},
            {"$set": {"self_referral_blocked": True, "captured_at": datetime.utcnow()}},
            upsert=True
        )
        return

    # ادامه حالت عادی
    referred = get_user(referred_tg) or upsert_user(referred_tg)
    if not referred.get("referred_by"):
        db.users.update_one(
            {"telegram_id": referred_tg},
            {"$set": {"referred_by": ref_code}}
        )
        db.referrals.update_one(
            {"referrer_ref_code": ref_code, "referred_tg": referred_tg},
            {"$setOnInsert": {"captured_at": datetime.utcnow(), "converted": False}},
            upsert=True
        )



def add_tokens(telegram_id: int, change: int, reason: str, by: str | None = None, order_id: str | None = None):
    # اول موجودی کاربر را افزایش بده
    db.users.update_one({"telegram_id": telegram_id}, {"$inc": {"tokens": change}})

    event_doc = {
        "telegram_id": telegram_id,
        "change": change,
        "reason": reason,
        "by": by,
        "ts": datetime.utcnow(),
    }

    if order_id:
        try:
            db.tokens_history.update_one(
                {"order_id": order_id, "telegram_id": telegram_id},
                {"$setOnInsert": {**event_doc, "order_id": order_id}},
                upsert=True
            )
        except DuplicateKeyError:
            pass
    else:
        db.tokens_history.insert_one(event_doc)


def get_ref_overview(tg_id: int, bot_username: str | None):
    user_doc = get_user(tg_id) or upsert_user(tg_id)
    ref_code = user_doc.get("ref_code")

    deep_link = f"https://t.me/{bot_username}?start=ref_{ref_code}" if bot_username else None

    tokens = user_doc.get("tokens", 0)
    to_next = max(0, 10 - (tokens % 10))

    # 1) شمردن تعداد کل خرید/تمدیدهای نسبت داده‌شده به این ref_code از referrals.purchase_count
    agg = list(db.referrals.aggregate([
        {"$match": {"referrer_ref_code": ref_code}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$purchase_count", 0]}}}}
    ]))
    successful_count = (agg[0]["total"] if agg else 0)

    # 2) اگر به هر دلیل صفر بود (مثلاً داده‌های legacy)، از tokens_history به عنوان fallback استفاده کن
    if successful_count == 0:
        reasons_for_referrer = [
            "first_purchase_bonus_referrer",
            "repeat_purchase_bonus_referrer",
            "renew_bonus_referrer",
            "referral_bonus_referrer",  # legacy
        ]
        successful_count = db.tokens_history.count_documents({
            "by": ref_code,
            "reason": {"$in": reasons_for_referrer}
        })

    return {
        "ref_code": ref_code,
        "deep_link": deep_link,
        "tokens": tokens,
        "to_next_reward": to_next,
        "successful_count": successful_count,
    }

def update_user_activity(telegram_id: int, username: str, fullname: str) -> str:
    """
    ثبت فعالیت کاربر:
    - همیشه last_seen را آپدیت می‌کند.
    - اگر کاربر جدید باشد → "new"
    - اگر بیش از ۱ ساعت از آخرین فعالیت گذشته → "reactivated"
    - در غیر این صورت → "silent"
    """
    current_timestamp = int(time.time())
    user_document = db.users.find_one({"telegram_id": telegram_id})

    if not user_document:
        # کاربر جدید → ایجاد و بازگشت new
        db.users.insert_one({
            "telegram_id": telegram_id,
            "username": username,
            "fullname": fullname,
            "created_at": current_timestamp,
            "last_seen": current_timestamp,
            "tokens": 0
        })
        return "new"

    last_seen_timestamp = user_document.get("last_seen", 0)
    # همیشه ابتدا last_seen را آپدیت می‌کنیم
    db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": {
            "username": username,
            "fullname": fullname,
            "last_seen": current_timestamp
        }}
    )

    # محاسبه اختلاف زمان فعلی با آخرین اکتیو قبلی
    time_since_last_seen = current_timestamp - int(last_seen_timestamp or 0)
    if time_since_last_seen >= 3600:
        return "reactivated"
    else:
        return "silent"

def reward_renewal(buyer_tg: int, order_id: str) -> tuple[bool, str]:
    if not order_id or not isinstance(order_id, str):
        return False, "invalid_order_id"

        # قفل سفارش: اگر قبلاً تایید شده باشد، BEFORE != None برمی‌گردد
    prev = db.order_locks.find_one_and_update(
        {"order_id": order_id},
        {"$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
        return_document=ReturnDocument.BEFORE,
    )
    if prev is not None:
        return False, "duplicate_order_id"




    # ضد تکرار: اگر قبلاً همین order_id ثبت شده باشد، دوباره پاداش نده
    if db.tokens_history.find_one({"order_id": order_id}):
        return False, "duplicate_order_id"

    buyer_doc = get_user(buyer_tg)
    if not buyer_doc:
        return False, "buyer_not_found"

    ref_code = buyer_doc.get("referred_by")
    if not ref_code:
        return False, "no_referrer"

    referrer_doc = get_user_by_ref_code(ref_code)
    if not referrer_doc:
        return False, "referrer_not_found"

    # جلو خودارجاع
    if referrer_doc["telegram_id"] == buyer_tg:
        return False, "self_referral_blocked"

    # پاداش تمدید: هر دو +1
    add_tokens(buyer_tg, +1, "renew_bonus_buyer", by=ref_code, order_id=order_id)
    add_tokens(referrer_doc["telegram_id"], +1, "renew_bonus_referrer", by=ref_code, order_id=order_id)

    # آمار ریفرال (converted را هم True نگه می‌داریم)
    db.referrals.update_one(
        {"referrer_ref_code": ref_code, "referred_tg": buyer_tg},
        {
            "$set": {"converted": True, "last_order_id": order_id, "last_purchase_at": datetime.utcnow()},
            "$inc": {"purchase_count": 1},
            "$setOnInsert": {"captured_at": datetime.utcnow()}
        },
        upsert=True
    )
    return True, "ok"


# --- Tokens helpers ---
def get_tokens(tg_id: int) -> int:
    doc = db.users.find_one({"telegram_id": tg_id}, {"tokens": 1})
    return int(doc.get("tokens", 0) if doc else 0)

def create_token_redeem_request(tg_id: int, allow_ip: int) -> dict:
    # درخواست در انتظار تایید ادمین
    req_id = f"TOK-{tg_id}-{int(time.time())}"
    doc = {
        "request_id": req_id,
        "telegram_id": tg_id,
        "allow_ip": int(allow_ip),
        "status": "pending",
        "created_at": datetime.utcnow(),
    }
    db.token_redemptions.insert_one(doc)
    return doc

def get_redeem_request(req_id: str) -> dict | None:
    return db.token_redemptions.find_one({"request_id": req_id})

def approve_token_redeem(req_id: str, tg_id: int, cost: int = 10) -> tuple[bool, str]:
    # 1) قفل درخواست: یکبار مصرف
    prev = db.token_redemptions.find_one_and_update(
        {"request_id": req_id, "status": "pending"},
        {"$set": {"status": "approved", "approved_at": datetime.utcnow()}},
        return_document=ReturnDocument.BEFORE,
    )
    if prev is None:
        return False, "already_processed_or_not_found"

    # 2) کم‌کردن توکن به‌صورت اتمیک
    user_after = db.users.find_one_and_update(
        {"telegram_id": tg_id, "tokens": {"$gte": cost}},
        {"$inc": {"tokens": -cost}},
        return_document=ReturnDocument.AFTER,
    )
    if user_after is None:
        # برگرداندن وضعیت درخواست
        db.token_redemptions.update_one({"request_id": req_id}, {"$set": {"status": "rejected", "reject_reason": "insufficient_tokens"}})
        return False, "insufficient_tokens"

    # 3) ثبت رویداد تاریخچه
    db.tokens_history.insert_one({
        "telegram_id": tg_id,
        "change": -cost,
        "reason": "token_redeem_subscription",
        "by": None,
        "order_id": req_id,
        "ts": datetime.utcnow(),
    })
    return True, "ok"