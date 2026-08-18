import os
from dotenv import load_dotenv
load_dotenv()

APP_NAME = ""

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
XUI_DB_PATH = os.getenv("XUI_DB_PATH")
XRAY_ACCESS_LOG = os.getenv("XRAY_ACCESS_LOG")
CARD_INFO = os.getenv("CARD_INFO", "xxxx-xxxx-xxxx-xxxx")

# Mongo
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB  = os.getenv("MONGO_DB")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASS = os.getenv("MONGO_PASS")

DOWNLOAD_LINKS = {
    "آیفون":   "https://apps.apple.com/tr/app/streisand/id6450534064",
    "اندروید": "https://play.google.com/store/apps/details?id=com.v2raytun.android&pcampaignid=web_share",
    "ویندوز":  "لینک در دسترس نمیباشد",
    "مک‌بوک":  "https://apps.apple.com/us/app/fair-vpn/id1533873488",
}