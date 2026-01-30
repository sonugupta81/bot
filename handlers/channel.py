from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError
import database

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.is_owner(user.username):
        return

    if not context.args:
        await update.message.reply_text("Usage:\nPublic: `/addchannel https://t.me/channel`\nPrivate: `/addchannel -100xxxx https://t.me/+abcd...`", parse_mode='Markdown')
        return

    args = context.args
    channel_id = None
    invite_link = None
    username = None
    
    # helper to check if string is link
    def is_link(s): return s.startswith('http') or s.startswith('t.me')

    if len(args) == 2:
        # Assume <id> <link>
        channel_id = args[0]
        invite_link = args[1]
    elif len(args) == 1:
        arg = args[0]
        if is_link(arg):
            invite_link = arg
            # Try to extract username if public
            if 't.me/+' in arg or 'joinchat' in arg:
                # Private link - Allow it but mark as link-only
                pass
            else:
                # Assume public t.me/username
                parts = arg.split('t.me/')
                if len(parts) > 1:
                    username = "@" + parts[1].split('/')[0].split('?')[0] # simplistic parsing
                else:
                    await update.message.reply_text("❌ Invalid link format. Use https://t.me/username")
                    return
        else:
            # Assume username or ID
            if arg.startswith('@'):
                username = arg
                invite_link = f"https://t.me/{username[1:]}"
            else:
                channel_id = arg # ID provided, no link
                pass

    try:
        # If we have an ID, use it. If not, use username.
        target = channel_id if channel_id else username
        chat = None
        
        if target:
            try:
                chat = await context.bot.get_chat(target)
            except TelegramError:
                # Could not fetch chat.
                pass
        
        # Logic for adding handling for unknown private channels
        if not chat and invite_link and ('t.me/+' in invite_link or 'joinchat' in invite_link):
            # Force add private channel without verification
            import time
            dummy_id = f"private_{int(time.time())}"
            # Use a generic title since we can't fetch it
            dummy_title = f"Channel {int(time.time())}" # TODO: Allow user to set title
            
            if database.add_channel_safe(dummy_id, dummy_title, None, invite_link):
                await update.message.reply_text(
                    f"✅ Private Link Added!\n\n"
                    f"⚠️ **Note:** Since no ID was provided, bot cannot verify members for this channel.\n"
                    f"Users will be able to join via the link, but verification will be skipped (auto-passed)."
                )
            else:
                await update.message.reply_text("⚠️ Channel already exists.")
            return

        if not target:
             await update.message.reply_text("❌ Could not determine target channel. If using a private link, just send the link.")
             return
             
        if not chat:
            # Try once more if we only had a link but no username extraction worked well?
            # Unlikely for public.
            await update.message.reply_text("❌ Could not find that channel. Ensure the bot is admin if searching by ID, or valid public username.")
            return

        if chat.type != 'channel':
            await update.message.reply_text("❌ That is not a channel.")
            return

        # Check admin rights
        try:
            member = await chat.get_member(context.bot.id)
            if member.status not in ['administrator', 'creator']:
                await update.message.reply_text("⚠️ I am not an admin in that channel. I added it, but I cannot verify members until I am admin.")
        except:
             await update.message.reply_text("⚠️ Could not check admin status.")

        # Prepare data for DB
        # Use existing username from chat if we didn't extract one
        final_username = chat.username if chat.username else username
        # Use invite_link if provided, else try chat.invite_link?
        final_link = invite_link if invite_link else chat.invite_link
        
        # If still no link, default to something if public
        if not final_link and chat.username:
            final_link = f"https://t.me/{chat.username}"
            
        # If still no link...
        if not final_link:
             final_link = "https://t.me/"

        if database.add_channel_safe(chat.id, chat.title, final_username, final_link):
            await update.message.reply_text(f"✅ Channel '{chat.title}' added!\nLink: {final_link}")
        else:
            await update.message.reply_text("⚠️ Channel already exists.")

    except TelegramError as e:
        await update.message.reply_text(f"❌ Error finding channel: {e}")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.is_owner(user.username):
        return
    
    if not context.args:
         # User requested to see data when clicking remove (running command without args)
         channels = database.get_channels()
         if not channels:
             await update.message.reply_text("⚠️ No channels found to remove.")
             return
         
         text = f"🗑️ *Select Channel to Remove* (Total: {len(channels)})\n\n"
         for c in channels:
             handle = f"@{c.username}" if c.username else "Private/Link"
             text += f"❌ `/removechannel {c.channel_id}`\nTitle: {c.title}\nLink: {handle}\n\n"
         
         await update.message.reply_text(text, parse_mode='Markdown')
         return
    
    # We need to resolve ID if username is passed, or iterate DB?
    # Simpler: If arg starts with @, find in DB by username, else by ID?
    # But DB store might not have username updated.
    # Try to execute delete by channel_id
    
    target = context.args[0]
    # Try to find ID if username passed
    if target.startswith('@'):
        # This is tricky without fetching from TG. 
        # But we can search our DB for this username?
        # Peewee query:
        # channel = Channel.select().where(Channel.username == target.replace('@', ''))...
        # Implementation in database.py is needed really.
        # For now, let's assume user passes ID or we resolve it via API
        try:
             chat = await context.bot.get_chat(target)
             target_id = chat.id
        except:
             await update.message.reply_text("❌ valid channel not found.")
             return
    else:
        target_id = target

    if database.remove_channel(target_id):
        await update.message.reply_text(f"🗑️ Channel {target} removed.")
    else:
        await update.message.reply_text("⚠️ Channel not found in database.")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.is_owner(user.username):
        return

    channels = database.get_channels()
    if not channels:
        await update.message.reply_text("Test: No channels added.")
        return

    text = "📢 *Added Channels:*\n"
    for c in channels:
        handle = f"@{c.username}" if c.username else "Private"
        text += f"- {c.title} ({handle}) `ID: {c.channel_id}`\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

    await update.message.reply_text(text, parse_mode='Markdown')

async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Detect if bot is added to a channel
    result = update.my_chat_member
    new_member = result.new_chat_member
    
    if new_member.status in ['administrator', 'creator'] and result.chat.type == 'channel':
        chat = result.chat
        
        # Check if we have any pending "private_" channels
        channels = database.get_channels()
        updated = False
        
        for c in channels:
            if c.channel_id.startswith('private_'):
                # Try to match?
                # Matching by Link is hard if we can't get link from 'chat' object easily 
                # (chat.invite_link might be None if we are just added).
                # But we can try matching Title?
                if c.title == chat.title: # Exact title match
                     database.update_channel_id(c.channel_id, chat.id, chat.title)
                     updated = True
                     # Notify owner
                     if config.OWNER_USERNAME:
                         await context.bot.send_message(
                             chat_id=result.from_user.id, # The user who added the bot
                             text=f"✅ *Channel ID Detected!*\n\nMatched '{chat.title}' and updated ID to `{chat.id}`.\nVerification will now work!"
                         )
                     break
        
        if not updated:
             # Just notify owner of ID
             await context.bot.send_message(
                 chat_id=result.from_user.id,
                 text=f"🤖 I was added to *{chat.title}*.\n\nID: `{chat.id}`\n\nIf you added this channel via link-only, please remove it and add again with this ID for verification to work."
             )

def get_handlers():
    from telegram.ext import ChatMemberHandler
    return [
        CommandHandler("addchannel", add_channel),
        CommandHandler("removechannel", remove_channel),
        CommandHandler("listchannels", list_channels),
        ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER)
    ]
