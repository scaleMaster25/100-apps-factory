import os
import asyncio
import time
import redis
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_core.messages import HumanMessage

from dispatcher import graph 

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Connect to Valkey (Redis drop-in)
valkey = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

async def watchdog_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(120)
    if valkey.get('bot_is_running') != 'True': return
    action = valkey.get('bot_current_action') or 'Processing...'
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'⏱️ Update (2 mins): {action}')
    
    elapsed = 120
    while valkey.get('bot_is_running') == 'True' and elapsed < 300:
        await asyncio.sleep(60)
        elapsed += 60
        if valkey.get('bot_is_running') != 'True': return
        action = valkey.get('bot_current_action') or 'Processing...'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'⏱️ Update ({elapsed//60} mins): {action}')
        
    if valkey.get('bot_is_running') == 'True':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'⚠️ Notice: Task exceeding 5 mins. Continuing to execute in background.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    
    # Lock the state in Valkey
    valkey.set('bot_is_running', 'True')
    valkey.set('bot_start_time', str(time.time()))
    valkey.set('bot_current_action', 'Routing task through Master Dispatcher...')
    
    watchdog_task = asyncio.create_task(watchdog_timer(update, context))
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    await update.message.reply_text("⚙️ Task received. Master Dispatcher is analyzing your request...")
    
    try:
        result = await graph.ainvoke({'messages': [HumanMessage(content=user_input)]})
        await update.message.reply_text(result['messages'][-1].content)
    except Exception as e:
        await update.message.reply_text(f'⚠️ Dispatcher Error: {e}')
    finally:
        valkey.set('bot_is_running', 'False')
        if not watchdog_task.done():
            watchdog_task.cancel()

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()