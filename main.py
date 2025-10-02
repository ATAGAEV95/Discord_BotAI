import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import app.core.embeds as EM
from app.core import handlers
from app.core.handlers import llama_manager
from app.core.scheduler import start_scheduler
from app.data.models import init_models
from app.data.request import get_rang, save_birthday, update_message_count
from app.services.daily_report import ReportGenerator
from app.services.telegram_notifier import telegram_notifier
from app.services.weather_agent import WeatherAgent
from app.services.youtube_notifier import YouTubeNotifier
from app.tools.utils import contains_only_urls, get_rank_description

load_dotenv()

TOKEN = os.getenv("DC_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
report_generator: ReportGenerator | None = None
weather_agent = WeatherAgent()
youtube_notifier = YouTubeNotifier(bot)


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
    await telegram_notifier.send_message(
        "⚠️ <b>Discord бот отключился</b>\nСоединение с Discord потеряно"
    )


@bot.event
async def on_resumed():
    print("Соединение с Discord восстановлено")
    await telegram_notifier.send_message(
        "✅ <b>Discord бот восстановил соединение</b>\nРабота продолжается"
    )


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
        try:
            rank_info = await update_message_count(message.author.id, message.author.name, server_id)

            if rank_info["rank_up"]:
                new_rank_description = get_rank_description(rank_info["message_count"])
                avatar_url = (
                    message.author.avatar.url
                    if message.author.avatar
                    else message.author.default_avatar.url
                )

                embed, file = await EM.create_rang_embed(
                    message.author.display_name,
                    rank_info["message_count"],
                    new_rank_description["description"],
                    avatar_url,
                    server_id,
                    message.author.id,
                )

                await message.channel.send(
                    f"🎉 **{message.author.mention}** повысил свой ранг!", embed=embed, file=file
                )

        except Exception as e:
            print(f"Произошла ошибка при обновлении статистики: {e}")

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

    if message.content.startswith("!update_user"):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("Эта команда доступна только администраторам.")
            return

        try:
            if server_id is None:
                await message.channel.send("Эта команда доступна только на сервере.")
                return

            server = message.guild
            members = server.members
            all_server_users = [f"{member.name}" for member in members if not member.bot]

            await llama_manager.index_server_users(server_id, all_server_users)

            await message.channel.send(
                f"✅ Список пользователей сервера обновлен! Добавлено {len(all_server_users)} пользователей."
            )
            return
        except Exception as e:
            await message.channel.send(f"❌ Ошибка: {e}")
            return

    if message.content.startswith("!add_youtube"):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("Эта команда доступна только администраторам.")
            return

        try:
            args = message.content.split()
            if len(args) < 4:
                await message.channel.send(
                    "Использование: !add_youtube <youtube_channel_id> <discord_channel_id> <название_канала>"
                )
                return

            youtube_id = args[1]
            discord_channel_id = int(args[2])
            name = " ".join(args[3:])

            success = await youtube_notifier.add_channel(
                youtube_id, discord_channel_id, name, server_id
            )
            if success:
                await message.channel.send("✅ Канал добавлен для отслеживания")
            else:
                await message.channel.send("❌ Ошибка при добавлении канала")
        except Exception as e:
            await message.channel.send(f"❌ Ошибка: {e}")
        return

    if message.content.startswith("!rank"):
        if message.content == "!rank list":
            embed = EM.create_rang_list_embed()
            await message.channel.send(embed=embed)
            return

        try:
            result = await get_rang(message.author.id, server_id)
            rank_description = get_rank_description(int(result))
            message_count = await get_rang(message.author.id, server_id)

            avatar_url = (
                message.author.avatar.url
                if message.author.avatar
                else message.author.default_avatar.url
            )

            embed, file = await EM.create_rang_embed(
                message.author.display_name,
                message_count,
                rank_description["description"],
                avatar_url,
                server_id,
                message.author.id,
            )
            await message.channel.send(embed=embed, file=file)
        except ValueError as ve:
            await message.channel.send(str(ve))
        except Exception as e:
            await message.channel.send(f"Произошла ошибка при получении статистики: {e}")
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
        embed = EM.create_help_embed()
        await message.channel.send(embed=embed)
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
