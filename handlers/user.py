from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import BadRequest
import database

import config

# Constants
POINTS_PER_JOIN = 100
POINTS_PER_REFERRAL = 50

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = None
    
    # Check for referral code
    if args and args[0].isdigit():
        possible_referrer = int(args[0])
        if possible_referrer != user.id:
            referrer_id = possible_referrer

    # Add user to DB
    db_user = database.add_user(user.id, user.username, referrer_id)
    
    # Check if owner
    is_admin = database.is_owner(user.username)
    
    # If new user and has referrer, maybe notify referrer or just track it?
    # For now, we just track it in DB. Points are awarded when they VERIFY.

    text = (
        f"� *WELCOME BOSS {user.first_name}* 🔥\n\n"
        "� *EARNING OPPORTUNITY LIVE* 💥\n\n"
        "📢 *Channels Join Karo*\n"
        "💸 *Sirf ₹100 Pay Karo*\n\n"
        "📝 *Register Karo & Instant Bonus Lo*\n"
        "🎁 *₹350 Bonus Pao* 😍\n\n"
        "📲 *Payment Screenshot Bhejo*\n"
        f"📩 *Contact / Support:* @{config.OWNER_USERNAME}\n\n"
        "⏰ ⚠️ *Offer Limited Time Ke Liye Hai*\n"
        "🚀 *Late Mat Karo – Abhi Join Karo!*"
    )
    
    keyboard = []
    
    # 1. Add Channel Buttons (3 per row)
    channels = database.get_channels()
    if channels:
        row = []
        for i, c in enumerate(channels):
            # We utilize stored invite_link if available
            if getattr(c, 'invite_link', None):
                 url = c.invite_link
            elif c.username:
                 url = f"https://t.me/{c.username}"
            else:
                 try:
                     chat = await context.bot.get_chat(c.channel_id)
                     url = chat.invite_link or f"https://t.me/c/{str(c.channel_id)[4:]}/1" # Hacky
                 except:
                     url = "https://t.me/"
            
            # User requested "Join Here" text on buttons
            btn_text = "Join ↗️"
            
            row.append(InlineKeyboardButton(btn_text, url=url))
            
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # Append remaining
        if row:
            keyboard.append(row)

        # 2. Add Verify Button

        # 2. Add Verify Button
        keyboard.append([InlineKeyboardButton("✅ Verify Joined", callback_data="verify_join")])
    else:
        text += "\n\n⚠️ *No channels added yet.*"

    # 3. Add Claim Here Section
    text += "\n\n👇 *Claim Here:*"
    claim_link = database.get_setting('claim_link', config.EXTERNAL_LINK)
    keyboard.append([InlineKeyboardButton("🎁 Claim", url=claim_link)])
    
    # 4. Add Contact Owner Button
    if config.OWNER_USERNAME:
        owner_url = f"https://t.me/{config.OWNER_USERNAME}"
        keyboard.append([InlineKeyboardButton("➕ Add Your Channel", url=owner_url)])
    
    # 4. Other Buttons (None for now)
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Owner Panel", callback_data="owner_panel")])
    
    # Reply
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        except BadRequest:
            pass # Ignore if message not modified
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def start_earning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Deprecated: merged into start. Redirecting.
    await start(update, context)

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    db_user = database.get_user(user_id)
    
    if db_user and db_user.joined_all:
         await query.answer("✅ You have already verified and claimed rewards!", show_alert=True)
         return

    channels = database.get_channels()
    not_joined = []
    
    await query.answer("Checking membership...") # Toast
    
    for c in channels:
        # If it's a "Link Only" channel (dummy ID), skip verification (Auto-pass)
        if str(c.channel_id).startswith('private_'):
            continue

        try:
            member = await context.bot.get_chat_member(chat_id=c.channel_id, user_id=user_id)
            if member.status in ['left', 'kicked', 'restricted']: # restricted might mean banned
                not_joined.append(c.title)
        except BadRequest:
            # Bot might not be admin or channel issue
            print(f"Error checking {c.title}")
            not_joined.append(c.title) # Assume not joined if check fails

    if not_joined:
        text = "❌ *You haven't joined all channels!*\n\nMissing:\n" + "\n".join([f"- {t}" for t in not_joined])
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Try Again", callback_data="start_earning")]
        ]))
    else:
        # Success!
        database.add_points(user_id, POINTS_PER_JOIN)
        
        # Mark as joined_all
        db_user.joined_all = True
        db_user.save()
        
        # Reward Referrer (if any and not already rewarded for this user?)
        # Logic: If referrer exists, give them points now.
        if db_user.referrer_id:
            database.add_points(db_user.referrer_id, POINTS_PER_REFERRAL)
            # Optional: Notify referrer
            try:
                await context.bot.send_message(
                    db_user.referrer_id, 
                    f"🎉 *Referral Bonus!* A user you invited just verified their account. +{POINTS_PER_REFERRAL} points!",
                    parse_mode='Markdown'
                )
            except:
                pass # Blocked bot or error

        await query.edit_message_text(
            f"✅ *Verification Successful!*\n\nYou earned {POINTS_PER_JOIN} points!",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="back_home")]])
        )

async def back_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reuse start logic but edits message
    await start(update, context)

async def owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_name = query.from_user.username
    if not database.is_owner(user_name):
         await query.edit_message_text("⛔ Access Denied.")
         return

    text = (
            "👑 *Owner Control Panel*\n\n"
            "/addowner <username> - Add new owner\n"
            "/removeowner <username> - Remove owner\n"
            "/listowners - List all owners\n\n"
            "📢 *Channel Management*\n"
            "/addchannel <link> - Add channel\n"
            "/removechannel <id> - Remove channel\n"
            "/listchannels - List channels\n\n"
            "📝 *Posting*\n"
            "Just send a message to broadcast.\n"
            "/schedule HH:MM <message> - Schedule post"
    )
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="back_home")]]))

def get_handlers():
    return [
        CommandHandler("start", start),
        CallbackQueryHandler(start_earning, pattern="^start_earning$"),
        CallbackQueryHandler(verify_join, pattern="^verify_join$"),
        CallbackQueryHandler(back_home, pattern="^back_home$"),
        CallbackQueryHandler(owner_panel, pattern="^owner_panel$"),
    ]
