import psutil
import platform
from telegram_notifier import send_telegram_message

class SystemMonitor:
    @staticmethod
    async def check_resources():
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        alert = ""
        if cpu > 90: alert += f"CPU: {cpu}% "
        if mem > 90: alert += f"Memory: {mem}% "
        if disk > 90: alert += f"Disk: {disk}%"
        
        if alert:
            await send_telegram_message(f"🚨 System Alert: {alert}")