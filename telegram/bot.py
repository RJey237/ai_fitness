import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

API_TOKEN = '7866665708:AAHxg1medDESQqiPtJGOwTE-ZZ8utoPvyyI'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_code():
    return random.randint(100000, 999999)

async def start_command(message: types.Message):
    logger.info(f"Received /start command from {message.from_user.id}") 
    await message.reply("Hello! I'm your Telegram bot. Use /generate to get your 6-digit code for registration.")

async def help_command(message: types.Message):
    logger.info(f"Received /help command from {message.from_user.id}") 
    await message.reply("Use /start to see the welcome message and /generate to get a 6-digit code.")

async def generate_code_command(message: types.Message):
    logger.info(f"Generating code for {message.from_user.id}") 
    code = generate_code()
    await message.reply(f"Here is your 6-digit code: {code}")
    
async def send_link_command(message: types.Message):
    url = "https://www.fitnessblender.com/"
    await message.answer(
        f"Check this out: {url}",
        disable_web_page_preview=True  
    )
    

async def echo(message: types.Message):
    logger.info(f"Echoing message from {message.from_user.id}: {message.text}")  
    await message.answer(message.text)

dp.message.register(start_command, Command('start'))
dp.message.register(help_command, Command('help'))
dp.message.register(generate_code_command, Command('generate'))
dp.message.register(send_link_command,Command('link'))
dp.message.register(echo)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())