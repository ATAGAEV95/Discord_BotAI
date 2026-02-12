import asyncio
from datetime import datetime

import discord
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.handlers import ai_generate_birthday_congrats
from app.data.models import Birthday, async_session
from app.data.request import check_holiday
from app.services.holiday import ai_generate_holiday_congrats
from app.services.youtube_notifier import YouTubeNotifier

DB_TIMEOUT = 10


async def get_today_birthday_users(timezone: str = "Europe/Moscow") -> list[Birthday]:
    """Получает список пользователей, у которых сегодня день рождения."""
    today = datetime.now(pytz.timezone(timezone)).date()
    async with async_session() as session:
        try:
            stmt = select(Birthday).where(Birthday.birthday is not None)
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


async def send_birthday_congratulations(bot: discord.Client) -> None:
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


async def send_holiday_congratulations(bot: discord.Client) -> None:
    """Отправляет поздравления с праздниками всем участникам серверов."""
    try:
        msk_tz = pytz.timezone("Europe/Moscow")
        now_msk = datetime.now(msk_tz)
        holiday = await check_holiday(now_msk.date())

        if not holiday:
            return

        for guild in bot.guilds:
            channel = guild.text_channels[0] if guild.text_channels else None
            if not channel:
                continue

            member_names = [member.name for member in guild.members if not member.bot]
            if not member_names:
                continue

            try:
                congrats_text = await ai_generate_holiday_congrats(member_names, holiday)
                await channel.send(f"🎉 **С праздником, {guild.name}!** 🎉\n{congrats_text}")
            except Exception as e:
                print(f"[Ошибка] при отправке поздравления с {holiday} для {guild.name}: {e}")

    except Exception as e:
        print(f"[Ошибка] в задаче send_holiday_congratulations: {e}")


def start_scheduler(bot: discord.Client) -> None:
    """Инициализирует и запускает асинхронный планировщик задач."""
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(send_birthday_congratulations, "cron", hour=9, minute=0, args=[bot])
    scheduler.add_job(
        send_holiday_congratulations,
        "cron",
        hour=0,
        minute=1,
        args=[bot],
        id="holiday_greeting",
    )
    # scheduler.add_job(
    #     send_holiday_congratulations,
    #     "interval",
    #     seconds=20,
    #     args=[bot],
    #     id="holiday_greeting_test"
    # )

    youtube_notifier = YouTubeNotifier(bot)
    scheduler.add_job(youtube_notifier.check_new_videos, "interval", minutes=60, id="youtube_check")
    scheduler.start()
