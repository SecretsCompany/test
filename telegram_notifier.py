import aiohttp
import asyncio
from config import settings
import logging

class TelegramNotifier:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(3)
        self.worker_task = None
        self.session = None

    async def worker(self):
        self.session = aiohttp.ClientSession()
        while True:
            message = await self.queue.get()
            async with self.semaphore:
                try:
                    await self.session.post(
                        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": settings.TELEGRAM_CHAT_ID,
                            "text": message,
                            "parse_mode": "Markdown"
                        }
                    )
                except Exception as e:
                    logging.error(f"Telegram error: {e}")
                finally:
                    self.queue.task_done()

    async def start(self):
        if not self.worker_task or self.worker_task.done():
            self.worker_task = asyncio.create_task(self.worker())

    async def stop(self):
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        if self.session:
            await self.session.close()

# Глобальный экземпляр
notifier = TelegramNotifier()

async def send_telegram_message(message: str):
    await notifier.queue.put(message)