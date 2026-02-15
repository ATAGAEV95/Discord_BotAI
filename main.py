import os

import discord
from dotenv import load_dotenv

from app.core.bot import DisBot

load_dotenv()

TOKEN = os.getenv("DC_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# Настройки функций
ENABLE_TELEGRAM_NOTIFIER = True  # Включить/выключить уведомления в Telegram
ENABLE_WEATHER = True  # Включить/выключить поиск погоды (нужен API ключ)
ENABLE_SEARCH = True   # Включить/выключить поиск в интернете (нужен API ключ)


def main() -> None:
    """Запуск бота."""
    bot = DisBot(
        command_prefix="!",
        intents=intents,
        telegram_enabled=ENABLE_TELEGRAM_NOTIFIER,
        weather_enabled=ENABLE_WEATHER,
        search_enabled=ENABLE_SEARCH,
        help_command=None,
    )

    if not TOKEN:
        print("Ошибка: DC_TOKEN не найден в переменных окружения!")
        return

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
