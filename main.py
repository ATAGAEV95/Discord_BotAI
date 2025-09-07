import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from app import handlers
from app.daily_report import ReportGenerator
from app.models import init_models
from app.requests import save_birthday, contains_only_urls
from app.scheduler import start_scheduler

load_dotenv()

TOKEN = os.getenv("DC_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
report_generator: ReportGenerator | None = None


@bot.event
async def on_ready():
    await init_models()
    global report_generator
    report_generator = ReportGenerator(bot)
    start_scheduler(bot)


@bot.event
async def on_message(message):
    global report_generator
    server_id = message.guild.id if message.guild else None

    if message.author.bot:
        return

    if len(message.content) > 1000:
        if message.content.startswith("!"):
            await message.channel.send(
                f"Сообщение слишком длинное: {len(message.content)} символов! Максимальная длина - 1000 символов."
            )
        return

    if not message.content.startswith("!"):
        if not message.content.strip():
            return

        if contains_only_urls(message.content):
            return

        if report_generator is not None:
            await report_generator.add_message(
                message.channel.id,
                message.content,
                message.author.display_name,
                message.id,
            )
        return

    if message.content.startswith("!birthday"):
        try:
            await save_birthday(
                message.content,
                message.author.display_name,
                message.author.name,
                message.author.id,
            )
            await message.channel.send("Дата рождения сохранена.")
        except ValueError as ve:
            await message.channel.send(str(ve))
        except Exception as e:
            await message.channel.send(
                f"Произошла ошибка при сохранении даты рождения: {e}"
            )
        return

    if message.content.startswith("!reset"):
        if server_id is None:
            await message.channel.send("Эта команда доступна только на сервере.")
            return

        answer = await handlers.clear_server_history(server_id)
        await message.channel.send(answer)
        return

    if message.content.startswith("!help"):
        await message.channel.send(
            "Команды бота:\n"
            "!reset - очистка истории чата\n"
            "!help - справка по командам\n"
            "!birthday DD.MM.YYYY - команда чтобы добавить свое день рождение"
        )
        return

    if server_id is None:
        await message.channel.send("Бот работает только на серверах.")
        return

    response = await handlers.ai_generate(message.content, server_id, message.author)
    await message.channel.send(f"{message.author.mention} {response}")


bot.run(TOKEN)
