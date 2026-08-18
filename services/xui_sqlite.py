import sqlite3, logging
from datetime import datetime
logger = logging.getLogger(__name__)

def get_xui_user_info(XUI_DB_PATH: str, uuid: str):
    try:
        with sqlite3.connect(XUI_DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT enable, email, up, down, expiry_time, total FROM client_traffics WHERE email=?",
                (uuid,)
            )
            row = cur.fetchone()
            if not row:
                return None
            enable, email, up, down, expiry_time, total = row
            used_gb = (up + down) / (1024**3)
            total_gb = (total / (1024**3)) if total and total > 0 else 0.0
            remain = total_gb - used_gb if total_gb > 0 else "نامحدود"
            expiry_ts = (expiry_time / 1000) if expiry_time and expiry_time > 0 else None
            days_remaining = (datetime.fromtimestamp(expiry_ts) - datetime.now()).days if expiry_ts else -1
            return {
                "uuid": uuid, "total": total_gb, "used": used_gb,
                "remain": remain, "expire": days_remaining,
                "enable": enable, "expiry_ts": expiry_ts
            }
    except Exception as e:
        logger.error(f"get_xui_user_info error for {uuid}: {e}")
        return None