import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from app.core import handlers
from app.services.daily_report import ReportGenerator
from app.data.models import init_models
from app.data.request import contains_only_urls, save_birthday
from app.core.scheduler import start_scheduler
from app.services.weather_agent import WeatherAgent
from app.services.telegram_notifier import telegram_notifier

load_dotenv()

TOKEN = os.getenv("DC_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
report_generator: ReportGenerator | None = None
weather_agent = WeatherAgent()


@bot.event
async def on_ready():
    await init_models()
    global report_generator
    report_generator = ReportGenerator(bot)
    start_scheduler(bot)
    print("Бот успешно подключился к Discord")


@bot.event
async def on_disconnect():
    print("Бот отключился от Discord")
    await telegram_notifier.send_message("⚠️ <b>Discord бот отключился</b>\nСоединение с Discord потеряно")

@bot.event
async def on_resumed():
    print("Соединение с Discord восстановлено")
    await telegram_notifier.send_message("✅ <b>Discord бот восстановил соединение</b>\nРабота продолжается")


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
            await message.channel.send(f"Произошла ошибка при сохранении даты рождения: {e}")
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
            "!birthday DD.MM.YYYY - команда чтобы добавить свое день рождение\n"
            "Напиши 'погода [город]' для получения текущей погоды\n"
            "Или 'погода [город] завтра' для прогноза на завтра"
        )
        return

    if server_id is None:
        await message.channel.send("Бот работает только на серверах.")
        return

    if "погода" in message.content.lower() and len(message.content.split()) > 1:
        flag = "завтра" in message.content.lower()
        is_weather, city = await weather_agent.should_handle_weather(message.content)

        if is_weather:
            if city:
                weather_info = weather_agent.get_weather(city, flag)
                await message.channel.send(weather_info)
            else:
                response = await handlers.ai_generate(message.content, server_id, message.author)
                await message.channel.send(f"{message.author.mention} {response}")
            return

    response = await handlers.ai_generate(message.content, server_id, message.author)
    await message.channel.send(f"{message.author.mention} {response}")


bot.run(TOKEN)
