import asyncio
from arbitrage import ArbitrageEngine
from telegram_notifier import notifier

async def main():
    await notifier.start()  # Запуск TelegramNotifier
    engine = ArbitrageEngine()

    try:
        while True:
            # Пример анализа пары
            await engine.analyze_pair("ETH", "0x...")  # Замените на реальные данные
            await asyncio.sleep(5)  # Пауза между итерациями
    except asyncio.CancelledError:
        pass
    finally:
        await notifier.stop()  # Корректное завершение TelegramNotifier

if __name__ == "__main__":
    asyncio.run(main())