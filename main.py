import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message

# Load environment variables from .env file
load_dotenv()

from config import API_ID, API_HASH, BOT_TOKEN
from database.database import Database
from plugins import *

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBot(Client):
    def __init__(self):
        super().__init__(
            "gdsys_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )
        self.db = None

    async def start(self):
        await super().start()
        self.db = Database()
        await self.db.connect()
        logger.info("Bot started successfully!")

    async def stop(self):
        if self.db:
            await self.db.close()
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()