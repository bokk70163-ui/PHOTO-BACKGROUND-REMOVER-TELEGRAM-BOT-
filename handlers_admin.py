import config
import db_helpers
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

# Helper to check admin status
def is_admin(user_id):
    return user_id in config.ADMIN_IDS

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id_to_ban = int(context.args[0])
        
        # We need to access that user's data. 
        # This is tricky without loading their data first.
        # A simple ban flag might not be stored yet if the user never started the bot.
        # A better approach (not implemented here) would be a separate ban list.
        # For simplicity, we assume we can fetch their user_data if they ever used the bot.
        
        # This line is complex with PicklePersistence. We'll use a simpler 'ban list'.
        if 'ban_list' not in context.bot_data:
            context.bot_data['ban_list'] = set()
        
        context.bot_data['ban_list'].add(user_id_to_ban)
        
        # Also update the user's personal data if they exist
        # This requires manually loading/saving persistence data, which is complex.
        # We will rely on checking the ban_list AND user_data.
        # When the user next messages, their `user_data` will be loaded, 
        # and we can set `user_data['banned'] = True` then.
        
        await update.message.reply_text(f"User {user_id_to_ban} has been added to the ban list.")
        await db_helpers.log_event_to_db(context, f"Admin {update.effective_user.id} banned user {user_id_to_ban}")

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /ban <user_id>")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id_to_unban = int(context.args[0])
        
        if 'ban_list' in context.bot_data:
            context.bot_data['ban_list'].discard(user_id_to_unban)
            
        # We also need to reset their user_data if it's loaded
        # This is a limitation of this simple model.
        # A proper implementation would fetch and update the user's pickled data.
            
        await update.message.reply_text(f"User {user_id_to_unban} has been removed from the ban list. "
                                        "They may need to type /start to reset their status.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /unban <user_id>")


async def send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
        
        if not message_text:
            await update.message.reply_text("Usage: /sendmsg <user_id> <message>")
            return
            
        await context.bot.send_message(chat_id=user_id, text=message_text)
        await update.message.reply_text("Message sent successfully.")
        
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /sendmsg <user_id> <message>")
    except TelegramError as e:
        await update.message.reply_text(f"Could not send message: {e}")


async def send_message_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("Usage: /sendmsgall <message>")
        return

    all_users = db_helpers.get_all_users(context)
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text(f"Starting broadcast to {len(all_users)} users. This may take time.")

    for user_id in all_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text)
            sent_count += 1
        except TelegramError as e:
            # User blocked the bot, etc.
            print(f"Failed to send to {user_id}: {e}")
            failed_count += 1
            
    await update.message.reply_text(
        f"Broadcast complete.\n"
        f"Successfully sent: {sent_count}\n"
        f"Failed: {failed_count}"
    )
    
