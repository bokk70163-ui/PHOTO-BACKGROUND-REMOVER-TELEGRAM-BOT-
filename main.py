import config
import handlers_user
import handlers_admin
import db_helpers

import os
import asyncio # এটি এখন শুধু post_init এর জন্য ব্যবহৃত হবে
import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    filters
)
from telegram.constants import ChatType
from telegram import Update

# --- Webhook Configuration (অপরিবর্তিত) ---
PORT = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_URL = None
if config.BOT_TOKEN and RENDER_EXTERNAL_HOSTNAME:
    WEBHOOK_URL = f"https://{RENDER_EXTERNAL_HOSTNAME}/{config.BOT_TOKEN}"

# Logging সেটআপ (অপরিবর্তিত)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- নতুন async setup ফাংশন ---
async def setup(application: Application):
    """
    এই ফাংশনটি অ্যাপ্লিকেশন বিল্ড হওয়ার পর কিন্তু সার্ভার চালু হওয়ার আগে চলবে।
    এটি async Webhook সেট করার জন্য ব্যবহৃত হয়।
    """
    if not WEBHOOK_URL:
        logger.error("WEBHOOK_URL is not set!")
        return
        
    logger.info(f"Setting webhook to {WEBHOOK_URL}...")
    await application.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=Update.ALL_TYPES)


def main() -> Application: # <--- এই ফাংশনটি এখন আর async নয়
    """
    অ্যাপ্লিকেশন তৈরি করে এবং হ্যান্ডলার যোগ করে।
    এটি এখন Application অবজেক্টটি রিটার্ন করবে।
    """
    
    # পারসিস্টেন্স অবজেক্ট তৈরি করুন
    persistence = PicklePersistence(filepath='bot_persistence')

    # অ্যাপ্লিকেশন বিল্ডার তৈরি করুন
    application = (Application.builder()
        .token(config.BOT_TOKEN)
        .persistence(persistence)
        .post_init(setup) # <--- Webhook সেট করার জন্য post_init ব্যবহার করা
        .build())

    # --- ইউজার হ্যান্ডলার (অপরিবর্তিত) ---
    application.add_handler(CommandHandler("start", handlers_user.start_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("help", handlers_user.help_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("status", handlers_user.status_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handlers_user.handle_photo))
    application.add_handler(CallbackQueryHandler(handlers_user.show_credits_callback, pattern="^show_credits$"))
    application.add_handler(CallbackQueryHandler(handlers_user.handle_conversion, pattern="^convert_"))
    
    # --- অ্যাডমিন হ্যান্ডলার (অপরিবর্তিত) ---
    application.add_handler(CommandHandler("ban", handlers_admin.ban_user))
    application.add_handler(CommandHandler("unban", handlers_admin.unban_user))
    application.add_handler(CommandHandler("sendmsg", handlers_admin.send_message_to_user))
    application.add_handler(CommandHandler("sendmsgall", handlers_admin.send_message_all))

    # --- গ্রুপ মেসেজ উপেক্ষা (অপরিবর্তিত) ---
    application.add_handler(MessageHandler(
        filters.ChatType.GROUP | filters.ChatType.SUPERGROUP | filters.ChatType.CHANNEL,
        handlers_user.ignore_non_private_chats
    ))
    
    return application # <--- অ্যাপ্লিকেশন অবজেক্টটি রিটার্ন করুন


if __name__ == "__main__":
    
    # --- কনফিগারেশন চেক (অপরিবর্তিত) ---
    if not all([config.BOT_TOKEN, config.ADMIN_IDS, config.DB_C_ID, config.RBG_API, config.SE_API_USER, config.SE_API_SECRET]):
        logger.error("ERROR: Environment variables are not set correctly. Please check config.py or env variables.")
    elif not RENDER_EXTERNAL_HOSTNAME:
         logger.error("ERROR: RENDER_EXTERNAL_HOSTNAME is not set. Are you running on Render?")
    else:
        logger.info("Configuration loaded successfully. Building application...")
        
        # ১. অ্যাপ্লিকেশনটি তৈরি করুন
        app = main() 
        
        # ২. Webhook সার্ভার চালু করুন (asyncio.run() ছাড়াই)
        # এটি একটি blocking কল যা নিজেই event loop ম্যানেজ করবে
        logger.info(f"Starting web server on 0.0.0.0:{PORT}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL
    )
        
