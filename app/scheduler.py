import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from sqlalchemy import select
from app.models import Birthday, async_session  # изменено User на Birthday
import discord


async def get_today_birthday_users(timezone='Europe/Moscow'):
    today = datetime.now(pytz.timezone(timezone)).date()
    async with async_session() as session:
        stmt = select(Birthday).where(Birthday.birthday != None)
        result = await session.execute(stmt)
        users = result.scalars().all()
        # Проверяем только по дню и месяцу, год — не берем в расчет!
        birthday_users = [u for u in users if u.birthday and u.birthday.month == today.month and u.birthday.day == today.day]
        return birthday_users


async def send_birthday_congratulations(bot: discord.Client):
    guilds = bot.guilds
    users = await get_today_birthday_users()
    for guild in guilds:
        # Ищем первый текстовый канал
        channel = discord.utils.get(guild.text_channels, position=0)
        if not channel:
            continue
        for user in users:
            member = guild.get_member(user.user_id)
            if member:
                await channel.send(f"Поздравляем {member.mention} с днём рождения! 🎉")


def start_scheduler(bot: discord.Client):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    # Каждый день в 9:00
    scheduler.add_job(send_birthday_congratulations, 'cron', hour=9, minute=0, args=[bot])
    scheduler.start()
