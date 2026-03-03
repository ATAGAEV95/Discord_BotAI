import asyncio
import sys

from dotenv import load_dotenv

# Обязательно загружаем .env перед импортом `telegram_notifier`,
# так как он инициализируется сразу при импорте модуля
load_dotenv()

from app.services.telegram_notifier import telegram_notifier


async def main() -> None:
    """
    Ручной тест для отправки сообщения в Telegram.
    Можно передать текст сообщения аргументом при запуске скрипта.
    """
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = "Привет! Это тестовое сообщение из ручного скрипта 🚀."

    print(f"Попытка отправить сообщение: {message}")

    success = await telegram_notifier.send_message(message)

    if success:
        print("✅ Сообщение успешно отправлено!")
    else:
        print("❌ Не удалось отправить сообщение. Проверь токены в .env файле.")


if __name__ == "__main__":
    asyncio.run(main())
