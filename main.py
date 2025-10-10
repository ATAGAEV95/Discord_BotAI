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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
report_generator: ReportGenerator | None = None
weather_agent = WeatherAgent()
youtube_notifier = YouTubeNotifier(bot)


@bot.command(name="help")
async def help_command(ctx):
    """Показать список команд"""
    embed = EM.create_help_embed()
    await ctx.send(embed=embed)


@bot.command(name="rank")
async def rank_command(ctx, arg: str = None):
    """Показать ранг пользователя или список рангов

    Если указан аргумент "list", отображает список всех рангов.
    В противном случае показывает текущий ранг автора сообщения.
    """
    if arg == "list":
        embed = EM.create_rang_list_embed()
        await ctx.send(embed=embed)
        return

    try:
        server_id = ctx.guild.id if ctx.guild else None
        message_count = await get_rang(ctx.author.id, server_id)
        rank_description = get_rank_description(int(message_count))

        avatar_url = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )

        embed, file = await EM.create_rang_embed(
            ctx.author.display_name,
            message_count,
            rank_description["description"],
            avatar_url,
            server_id,
            ctx.author.id,
        )
        await ctx.send(embed=embed, file=file)
    except ValueError as ve:
        await ctx.send(str(ve))
    except Exception as e:
        await ctx.send(f"Произошла ошибка при получении статистики: {e}")


@bot.command(name="birthday")
async def birthday_command(ctx, *, date: str):
    """Сохранить дату рождения

    Args:
        date: Дата рождения в формате строки
    """
    try:
        await save_birthday(
            f"!birthday {date}",
            ctx.author.display_name,
            ctx.author.name,
            ctx.author.id,
        )
        await ctx.send("Дата рождения сохранена.")
    except ValueError as ve:
        await ctx.send(str(ve))
    except Exception as e:
        await ctx.send(f"Произошла ошибка при сохранении даты рождения: {e}")


@bot.command(name="reset")
@commands.guild_only()
async def reset_command(ctx):
    """Очистить историю сервера (только для администраторов)"""
    answer = await handlers.clear_server_history(ctx.guild.id)
    await ctx.send(answer)


@bot.command(name="update_user")
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def update_user_command(ctx):
    """Обновить список пользователей сервера (только для администраторов)"""
    try:
        server = ctx.guild
        members = server.members
        all_server_users = [f"{member.name}" for member in members if not member.bot]

        await llama_manager.index_server_users(server.id, all_server_users)

        await ctx.send(
            f"✅ Список пользователей сервера обновлен! Добавлено {len(all_server_users)} пользователей."
        )
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")


@bot.command(name="add_youtube")
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def add_youtube_command(ctx, youtube_id: str, discord_channel_id: int, *, name: str):
    """Добавить YouTube канал для отслеживания

    Args:
        youtube_id: ID YouTube канала
        discord_channel_id: ID Discord канала для уведомлений
        name: Название канала
    """
    try:
        success = await youtube_notifier.add_channel(
            youtube_id, discord_channel_id, name, ctx.guild.id
        )
        if success:
            await ctx.send("✅ Канал добавлен для отслеживания")
        else:
            await ctx.send("❌ Ошибка при добавлении канала")
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")


@bot.command(name="weather")
async def weather_command(ctx, *, location: str):
    """Получить погоду для указанного места

    Args:
        location: Местоположение с возможным флагом "завтра"
    """
    flag = "завтра" in location.lower()
    is_weather, city = await weather_agent.should_handle_weather(location)

    if is_weather and city:
        weather_info = weather_agent.get_weather(city, flag)
        await ctx.send(weather_info)
    else:
        await ctx.send("Не удалось определить местоположение для прогноза погоды")


@bot.event
async def on_ready():
    """Инициализация при подключении бота к Discord"""
    await init_models()
    global report_generator
    report_generator = ReportGenerator(bot)
    start_scheduler(bot)
    print("Бот успешно подключился к Discord")


@bot.event
async def on_disconnect():
    """Обработка отключения от Discord"""
    print("Бот отключился от Discord")
    await telegram_notifier.send_message(
        "⚠️ <b>Discord бот отключился</b>\nСоединение с Discord потеряно"
    )


@bot.event
async def on_resumed():
    """Обработка восстановления соединения с Discord"""
    print("Соединение с Discord восстановлено")
    await telegram_notifier.send_message(
        "✅ <b>Discord бот восстановил соединение</b>\nРабота продолжается"
    )


@bot.event
async def on_command_error(ctx, error):
    """Обработка ошибок команд

    Args:
        ctx: Контекст команды
        error: Возникшая ошибка
    """
    if isinstance(error, commands.CommandNotFound):
        server_id = ctx.guild.id if ctx.guild else None
        response = await handlers.ai_generate(ctx.message.content, server_id, ctx.author)
        await ctx.send(f"{ctx.author.mention} {response}")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас недостаточно прав для выполнения этой команды.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"❌ Неправильное использование команды. Используйте: `!{ctx.command.name} {ctx.command.signature}`")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Эта команда недоступна в личных сообщениях.")
    else:
        await ctx.send("❌ Произошла ошибка при выполнении команды.")
        print(f"Command error: {error}")


@bot.event
async def on_message(message):
    """Обработка входящих сообщений

    Args:
        message: Объект сообщения Discord
    """
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

    await bot.process_commands(message)


bot.run(TOKEN)
