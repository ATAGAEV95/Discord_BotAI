import os

import discord
from dotenv import load_dotenv

from app.core.bot import DisBot

load_dotenv()

TOKEN = os.getenv("DC_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


def main() -> None:
    """Запуск бота."""
    bot = DisBot(command_prefix="!", intents=intents, help_command=None)
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
