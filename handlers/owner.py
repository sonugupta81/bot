from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import database
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username
    if not username:
        await update.message.reply_text("You must have a Telegram username to use this bot.")
        return

    # Auto-add initial owner if configured and not yet added
    if config.OWNER_USERNAME and username.lower() == config.OWNER_USERNAME:
        if not database.is_owner(username):
            database.add_owner_safe(username)
            await update.message.reply_text(f"Welcome Boss! You have been registered as an owner.")

    if database.is_owner(username):
        await update.message.reply_text(
            "👑 *Owner Control Panel*\n\n"
            "/addowner <username> - Add new owner\n"
            "/removeowner <username> - Remove owner\n"
            "/listowners - List all owners\n\n"
            "📢 *Channel Management*\n"
            "/addchannel @channel - Add channel\n"
            "/removechannel @channel - Remove channel\n"
            "/listchannels - List channels\n\n"
            "🔗 *Links*\n"
            "/setclaim <link> - Set Claim Link\n\n"
            "📝 *Posting*\n"
            "Just send a message to broadcast.\n"
            "/schedule HH:MM <message> - Schedule post",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("⛔ Access Denied. You are not an authorized owner.")

async def add_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.is_owner(user.username):
        return

    if not context.args:
        await update.message.reply_text("Usage: /addowner username")
        return

    new_owner = context.args[0]
    if database.add_owner_safe(new_owner):
        await update.message.reply_text(f"✅ Added {new_owner} as owner.")
    else:
        await update.message.reply_text(f"⚠️ Could not add {new_owner}. Already exists?")

async def remove_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.is_owner(user.username):
        return

    if not context.args:
        await update.message.reply_text("Usage: /removeowner username")
        return

    target = context.args[0]
    # Protect main owner?
    if config.OWNER_USERNAME and target.replace('@','').lower() == config.OWNER_USERNAME:
        await update.message.reply_text("⛔ Cannot remove the primary owner.")
        return

    if database.remove_owner(target):
        await update.message.reply_text(f"🗑️ Removed {target} from owners.")
    else:
        await update.message.reply_text(f"⚠️ {target} not found.")

async def list_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.is_owner(user.username):
        return

    owners = database.get_owners()
    text = "👑 *OwnersList:*\n" + "\n".join([f"- @{o}" for o in owners])
    await update.message.reply_text(text, parse_mode='Markdown')

async def set_claim_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.is_owner(user.username):
        return

    if not context.args:
        await update.message.reply_text("Usage: /setclaim <new_link>")
        return

    new_link = context.args[0]
    if database.set_setting('claim_link', new_link):
        await update.message.reply_text(f"✅ Claim link updated to:\n{new_link}")
    else:
        await update.message.reply_text("⚠️ Failed to update link.")

def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("addowner", add_owner),
        CommandHandler("removeowner", remove_owner),
        CommandHandler("listowners", list_owners),
        CommandHandler("setclaim", set_claim_link),
    ]
