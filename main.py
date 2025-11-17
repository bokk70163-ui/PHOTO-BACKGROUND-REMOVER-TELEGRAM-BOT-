import config
import handlers_user
import handlers_admin
import db_helpers

import os
import asyncio
import telegram
import urllib.request
from flask import Flask, request

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    filters
)
from telegram.constants import ChatType

server = Flask(__name__)

def setup_bot():
    """
    Sets up the bot application and adds all handlers.
    """
    persistence = PicklePersistence(filepath='bot_persistence')

    application = (Application.builder()
        .token(config.BOT_TOKEN)
        .persistence(persistence)
        .build())

    # --- User Handlers ---
    application.add_handler(CommandHandler("start", handlers_user.start_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("help", handlers_user.help_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("status", handlers_user.status_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handlers_user.handle_photo))
    
    # --- Callback Handlers ---
    application.add_handler(CallbackQueryHandler(handlers_user.show_credits_callback, pattern="^show_credits$"))
    application.add_handler(CallbackQueryHandler(handlers_user.handle_conversion, pattern="^convert_"))
    
    # --- Admin Handlers ---
    application.add_handler(CommandHandler("ban", handlers_admin.ban_user))
    application.add_handler(CommandHandler("unban", handlers_admin.unban_user))
    application.add_handler(CommandHandler("sendmsg", handlers_admin.send_message_to_user))
    application.add_handler(CommandHandler("sendmsgall", handlers_admin.send_message_all))

    # --- Ignore Group/Channel Messages ---
    application.add_handler(MessageHandler(
        filters.ChatType.GROUP | filters.ChatType.SUPERGROUP | filters.ChatType.CHANNEL,
        handlers_user.ignore_non_private_chats
    ))

    return application

# --- অ্যাপ্লিকেশনটি তৈরি করুন ---
application = setup_bot()

# --- নতুন ফিক্স: অ্যাপ্লিকেশনটি গ্লোবালি Initialize করুন ---
# Gunicorn সার্ভার চালু করার আগেই এটি রান হবে
print("Initializing bot application...")
asyncio.run(application.initialize())
print("Bot application initialized.")
# --- ফিক্স শেষ ---


@server.route('/' + config.BOT_TOKEN, methods=['POST'])
def webhook_update():
    """
    Handles updates from Telegram.
    """
    update_json = request.get_json()
    update = telegram.Update.de_json(update_json, application.bot)
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(application.process_update(update))
    except RuntimeError:
        # Gunicorn-এর sync worker-এ কোনো রানিং লুপ থাকে না, 
        # তাই asyncio.run() ব্যবহার করা সঠিক
        asyncio.run(application.process_update(update))
            
    return "ok", 200

@server.route("/")
def set_webhook():
    """
    Sets the webhook URL on bot startup.
    """
    host_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if not host_url:
        print("WARNING: RENDER_EXTERNAL_HOSTNAME not set. Webhook may fail.")
        return "Webhook setup failed: Host URL not found.", 500

    bot_url = f"https://{host_url}/{config.BOT_TOKEN}"
    api_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/"
    
    req = urllib.request.Request(api_url + "setWebhook?url=" + bot_url)
    try:
        urllib.request.urlopen(req)
        print(f"Webhook set successfully to {bot_url}")
        return "Webhook set!", 200
    except Exception as e:
        print(f"Webhook setup error: {e}")
        return f"Webhook error: {e}", 500

if __name__ == "__main__":
    
    if not all([config.BOT_TOKEN, config.ADMIN_IDS, config.DB_C_ID, config.RBG_API, config.SE_API_USER, config.SE_API_SECRET]):
        print("ERROR: Environment variables are not set correctly. Please check.")
        print("Missing one or more of: BOT_TOKEN, ADMIN_IDS, DB_C_ID, RBG_API, SE_API_USER, SE_API_SECRET")
    else:
        print("Configuration loaded successfully. Starting webhook server...")
        # এই ব্লকটি সরাসরি 'python main.py' চালালে কাজ করবে
        # Gunicorn এটি ব্যবহার করে না, তবে টেস্ট করার জন্য এটি রাখা ভালো
        port = int(os.environ.get("PORT", 10000))
        server.run(host="0.0.0.0", port=port)
