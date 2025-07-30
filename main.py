import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional

from app import handlers
from app.daily_report import ReportGenerator
from app.models import init_models

load_dotenv()

TOKEN = os.getenv("DC_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
report_generator: Optional[ReportGenerator] = None


@bot.event
async def on_ready():
    await init_models()
    global report_generator
    report_generator = ReportGenerator(bot)


@bot.event
async def on_message(message):
    global report_generator

    if message.author.bot:
        return

    if not message.content.startswith("!"):
        if report_generator is not None:
            await report_generator.add_message(
                message.channel.id,
                message.content,
                message.author.display_name,
                message.id
            )
        return

    if message.content.startswith("!reset"):
        user_id = message.author.id
        await handlers.clear_user_history(user_id)
        await message.channel.send(f"История переписки для {message.author} успешно очищена.")
        return

    if message.content.startswith("!help"):
        await message.channel.send(
            "Команды бота:\n"
            "!reset - очистка истории чата\n"
            "!help - справка по командам"
        )
        return

    response = await handlers.ai_generate(message.content, message.author.id, message.author)
    await message.channel.send(response)


bot.run(TOKEN)
