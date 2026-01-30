import logging
import sys
import asyncio
import platform

# Fix for Windows asyncio SSL issues
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from telegram.ext import ApplicationBuilder
from telegram.request import HTTPXRequest
import config
import database
from handlers import owner, channel, broadcast, user

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    if not config.BOT_TOKEN:
        print("Error: BOT_TOKEN not found in config or env.")
        return

    # Init DB
    database.init_db()
    
    # Build Application
    request = HTTPXRequest(connect_timeout=60.0, read_timeout=60.0, write_timeout=60.0, pool_timeout=60.0)
    application = ApplicationBuilder().token(config.BOT_TOKEN).request(request).build()
    
    # Register User Handlers (Start, Join, Verify) - High Priority
    for h in user.get_handlers():
        application.add_handler(h)

    # Register Owner Handlers
    for h in owner.get_handlers():
        application.add_handler(h)
        
    # Register Channel Handlers
    for h in channel.get_handlers():
        application.add_handler(h)
        
    # Register Broadcast/Schedule Handlers
    # Note: broadcast_message is in get_handlers() of broadcast module
    # We must ensure MessageHandler is added LAST so it doesn't block commands
    # But get_handlers() list order matters. 
    # owner/channel handlers are Commands.
    # broadcast has Commands AND MessageHandler.
    for h in broadcast.get_handlers():
        application.add_handler(h)

    # Load Scheduled Jobs
    print("Loading scheduled jobs...")
    broadcast.load_jobs(application)

    # Start
    print(f"Bot started! Owner: {config.OWNER_USERNAME}")
    application.run_polling()

if __name__ == '__main__':
    main()
