import config
import handlers_user
import handlers_admin
import db_helpers

import os
import asyncio
import telegram
import urllib.request
from flask import Flask, request

# টেলিগ্রাম লাইব্রেরি ইম্পোর্ট
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    filters
)

server = Flask(__name__)

def setup_bot():
    """
    Sets up the bot application and adds all handlers.
    """
    # পারসিসটেন্স সেটআপ (যদি আপনার bot_persistence ফাইল থাকে)
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

# গ্লোবাল অ্যাপ্লিকেশন অবজেক্ট তৈরি
application = setup_bot()

@server.route('/' + config.BOT_TOKEN, methods=['POST'])
async def webhook_update():
    """
    Handles updates from Telegram properly with async/await.
    """
    # অ্যাপ্লিকেশন যদি ইনিশিলাইজ না থাকে, তবে করে নিতে হবে
    if not application._initialized:
        await application.initialize()

    update_json = request.get_json()
    
    if update_json:
        # JSON থেকে আপডেট অবজেক্ট তৈরি
        update = telegram.Update.de_json(update_json, application.bot)
        
        # সরাসরি await ব্যবহার করে প্রসেস করা (asyncio.run ব্যবহার করবেন না)
        await application.process_update(update)
            
    return "ok", 200

@server.route("/")
def set_webhook():
    """
    Sets the webhook URL. Can be triggered manually or by a cron job.
    """
    host_url = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if not host_url:
        return "Webhook setup failed: Host URL not found.", 500

    bot_url = f"https://{host_url}/{config.BOT_TOKEN}"
    api_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/"
    
    try:
        req = urllib.request.Request(api_url + "setWebhook?url=" + bot_url)
        urllib.request.urlopen(req)
        return f"Webhook set successfully to {bot_url}", 200
    except Exception as e:
        return f"Webhook error: {e}", 500

if __name__ == "__main__":
    # লোকাল টেস্ট এর জন্য
    import uvicorn
    
    if not all([config.BOT_TOKEN, config.ADMIN_IDS, config.DB_C_ID]):
        print("WARNING: Some environment variables might be missing.")
    
    print("Starting server locally with Uvicorn...")
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(server, host="0.0.0.0", port=port)
