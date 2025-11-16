import config
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
import datetime

# Helper to add user to the global list for /sendmsgall
def add_user_to_db(context, user_id):
    if 'user_ids' not in context.bot_data:
        context.bot_data['user_ids'] = set()
    context.bot_data['user_ids'].add(user_id)

def get_all_users(context):
    return context.bot_data.get('user_ids', set())

# Helper to format the stats message
def get_user_stats_text(user, user_data):
    user_name = user.first_name
    username = f"@{user.username}" if user.username else "No Username"
    
    return (
        f"<b>User:</b> {user_name}\n"
        f"<b>Username:</b> {username}\n"
        f"<b>User ID:</b> <code>{user.id}</code>\n\n"
        f"<b>Credits Left:</b> {user_data.get('daily_limit', 3)}\n"
        f"<b>Violations:</b> {user_data.get('violations', 0)}\n"
        f"<b>Banned:</b> {'Yes' if user_data.get('banned', False) else 'No'}"
    )

# This function sends or edits the message in the DB channel
async def update_db_channel_message(context, user):
    user_data = context.user_data
    stats_text = get_user_stats_text(user, user_data)
    
    db_msg_id = user_data.get('db_msg_id')
    
    try:
        if db_msg_id:
            # Edit existing message
            await context.bot.edit_message_text(
                chat_id=config.DB_C_ID,
                message_id=db_msg_id,
                text=stats_text,
                parse_mode=ParseMode.HTML
            )
        else:
            # Send new message and save its ID
            message = await context.bot.send_message(
                chat_id=config.DB_C_ID,
                text=stats_text,
                parse_mode=ParseMode.HTML
            )
            user_data['db_msg_id'] = message.message_id
            
    except TelegramError as e:
        error_str = str(e).lower()
        # If message content is the same, no update needed - silently ignore
        if "message is not modified" in error_str:
            return  # Nothing to update, this is fine
        # If message was deleted or bot was kicked, send a new one
        if "message to edit not found" in error_str:
            print(f"DB Channel Error: Message not found. Sending new message.")
            user_data['db_msg_id'] = None # Reset
            await update_db_channel_message(context, user) # Recurse
        else:
            print(f"DB Channel Error: {e}")
    except Exception as e:
        print(f"Failed to update DB channel: {e}")

# Logs a new event (like a ban) to the DB channel
async def log_event_to_db(context, event_text):
    try:
        await context.bot.send_message(
            chat_id=config.DB_C_ID,
            text=event_text
        )
    except Exception as e:
        print(f"Failed to log event to DB channel: {e}")

# Helper to check and reset daily limits
def check_daily_limit(user_data, is_admin):
    if is_admin:
        return True # Admins have no limit
        
    today = datetime.date.today().isoformat()
    last_used = user_data.get('last_used_date')
    
    if last_used != today:
        user_data['last_used_date'] = today
        user_data['daily_limit'] = 3 # Reset limit
    
    return user_data.get('daily_limit', 3) > 0

def use_credit(user_data, is_admin):
    if is_admin:
        return # Admins don't use credits
        
    if user_data.get('daily_limit', 3) > 0:
        user_data['daily_limit'] = user_data.get('daily_limit', 3) - 1
  
