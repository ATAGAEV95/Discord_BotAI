import asyncio
from datetime import datetime

import discord
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.handlers import ai_generate_birthday_congrats
from app.data.models import Birthday, async_session
from app.services.holiday import ai_generate_new_year_congrats
from app.services.youtube_notifier import YouTubeNotifier

DB_TIMEOUT = 10


async def get_today_birthday_users(timezone="Europe/Moscow"):
    """Получает список пользователей, у которых сегодня день рождения."""
    today = datetime.now(pytz.timezone(timezone)).date()
    async with async_session() as session:
        try:
            stmt = select(Birthday).where(Birthday.birthday != None)
            result = await asyncio.wait_for(session.execute(stmt), timeout=DB_TIMEOUT)
            users = result.scalars().all()
            birthday_users = [
                u
                for u in users
                if u.birthday and u.birthday.month == today.month and u.birthday.day == today.day
            ]
            return birthday_users
        except TimeoutError:
            print("Таймаут при получении дней рождения из базы данных.")
            return []
        except Exception as e:
            print(f"Ошибка доступа к базе данных (дни рождения): {e}")
            return []


async def send_birthday_congratulations(bot: discord.Client):
    """Отправляет поздравления пользователям, у которых сегодня день рождения."""
    try:
        users = await get_today_birthday_users()
        if not users:
            return

        for guild in bot.guilds:
            channel = guild.text_channels[0] if guild.text_channels else None
            if not channel:
                continue

            for user in users:
                member = guild.get_member(user.user_id)
                if not member:
                    continue

                try:
                    congrats_text = await ai_generate_birthday_congrats(user.name)
                    await channel.send(f"{member.mention} {congrats_text}")
                except Exception as e:
                    print(f"[Ошибка] при отправке поздравления для {user.name}: {e}")
    except Exception as e:
        print(f"[Ошибка] в задаче send_birthday_congratulations: {e}")


async def send_new_year_congratulations(bot: discord.Client):
    """Отправляет поздравления с Новым годом всем участникам серверов."""
    try:
        for guild in bot.guilds:
            channel = guild.text_channels[0] if guild.text_channels else None
            if not channel:
                continue

            member_names = [member.name for member in guild.members if not member.bot]
            if not member_names:
                continue

            try:
                congrats_text = await ai_generate_new_year_congrats(member_names)
                await channel.send(f"🎉 **С Новым Годом, {guild.name}!** 🎉\n{congrats_text}")
            except Exception as e:
                print(f"[Ошибка] при отправке Новогоднего поздравления для {guild.name}: {e}")

    except Exception as e:
        print(f"[Ошибка] в задаче send_new_year_congratulations: {e}")


def start_scheduler(bot: discord.Client):
    """Инициализирует и запускает асинхронный планировщик задач."""
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(send_birthday_congratulations, "cron", hour=9, minute=0, args=[bot])
    scheduler.add_job(
        send_new_year_congratulations,
        "cron",
        month=12,
        day=31,
        hour=23,
        minute=59,
        args=[bot],
        id="new_year_greeting",
    )
    # scheduler.add_job(send_new_year_congratulations, "interval", seconds=20, args=[bot], id="new_year_greeting")
    youtube_notifier = YouTubeNotifier(bot)
    scheduler.add_job(youtube_notifier.check_new_videos, "interval", minutes=60, id="youtube_check")
    scheduler.start()
