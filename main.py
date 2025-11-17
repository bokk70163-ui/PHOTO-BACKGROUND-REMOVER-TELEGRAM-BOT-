import config
import handlers_user
import handlers_admin
import db_helpers

import os  # Webhook এর জন্য যোগ করা হয়েছে
import asyncio  # Webhook এর জন্য যোগ করা হয়েছে
import logging  # Webhook এর জন্য যোগ করা হয়েছে

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    filters
)
from telegram.constants import ChatType
from telegram import Update # Webhook এর জন্য

# --- Webhook Configuration ---
# Render.com স্বয়ংক্রিয়ভাবে এই ভ্যারিয়েবলগুলো সেট করে
PORT = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

# config.py থেকে বট টোকেন লোড করা হচ্ছে
# WEBHOOK_URL তৈরি করার জন্য এটি প্রয়োজন
WEBHOOK_URL = None
if config.BOT_TOKEN and RENDER_EXTERNAL_HOSTNAME:
    WEBHOOK_URL = f"https://{RENDER_EXTERNAL_HOSTNAME}/{config.BOT_TOKEN}"

# Logging সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main(): # ফাংশনটিকে async করা হয়েছে
    """Starts the bot."""
    
    # বট রিস্টার্ট হলেও ডাটা মনে রাখার জন্য পারসিস্টেন্স অবজেক্ট তৈরি করুন
    persistence = PicklePersistence(filepath='bot_persistence')

    # অ্যাপ্লিকেশন বিল্ডার তৈরি করুন
    application = (Application.builder()
        .token(config.BOT_TOKEN)
        .persistence(persistence)
        .build())

    # --- ইউজার হ্যান্ডলার যোগ করুন (অপরিবর্তিত) ---
    application.add_handler(CommandHandler("start", handlers_user.start_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("help", handlers_user.help_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("status", handlers_user.status_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handlers_user.handle_photo))
    application.add_handler(CallbackQueryHandler(handlers_user.show_credits_callback, pattern="^show_credits$"))
    application.add_handler(CallbackQueryHandler(handlers_user.handle_conversion, pattern="^convert_"))
    
    # --- অ্যাডমিন হ্যান্ডলার যোগ করুন (অপরিবর্তিত) ---
    application.add_handler(CommandHandler("ban", handlers_admin.ban_user))
    application.add_handler(CommandHandler("unban", handlers_admin.unban_user))
    application.add_handler(CommandHandler("sendmsg", handlers_admin.send_message_to_user))
    application.add_handler(CommandHandler("sendmsgall", handlers_admin.send_message_all))

    # --- গ্রুপ বা চ্যানেলের মেসেজ উপেক্ষা করার হ্যান্ডলার (অপরিবর্তিত) ---
    application.add_handler(MessageHandler(
        filters.ChatType.GROUP | filters.ChatType.SUPERGROUP | filters.ChatType.CHANNEL,
        handlers_user.ignore_non_private_chats
    ))

    # --- Webhook মোডে চালু করুন ---
    # application.run_polling() এর বদলে নিচের কোড:
    logger.info(f"Setting webhook to {WEBHOOK_URL}...")
    await application.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=Update.ALL_TYPES)
    
    logger.info(f"Starting web server on 0.0.0.0:{PORT}...")
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    
    # বট চালু করার আগে চেক করুন সব এনভায়রনমেন্ট ভেরিয়েবল ঠিক আছে কিনা
    if not all([config.BOT_TOKEN, config.ADMIN_IDS, config.DB_C_ID, config.RBG_API, config.SE_API_USER, config.SE_API_SECRET]):
        logger.error("ERROR: Environment variables are not set correctly. Please check config.py or env variables.")
    elif not RENDER_EXTERNAL_HOSTNAME:
         logger.error("ERROR: RENDER_EXTERNAL_HOSTNAME is not set. Are you running on Render?")
    else:
        logger.info("Configuration loaded successfully. Starting bot in Webhook mode...")
        # main() কে async হিসেবে চালানোর জন্য asyncio.run() ব্যবহার করা হচ্ছে
        asyncio.run(main())
  
