import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from sqlalchemy import select
from app.models import Birthday, async_session
import discord
from app.handlers import ai_generate_birthday_congrats


async def get_today_birthday_users(timezone='Europe/Moscow'):
    today = datetime.now(pytz.timezone(timezone)).date()
    async with async_session() as session:
        stmt = select(Birthday).where(Birthday.birthday != None)
        result = await session.execute(stmt)
        users = result.scalars().all()
        birthday_users = [u for u in users if u.birthday and u.birthday.month == today.month and u.birthday.day == today.day]
        return birthday_users


async def send_birthday_congratulations(bot: discord.Client):
    guilds = bot.guilds
    users = await get_today_birthday_users()
    for guild in guilds:
        channel = guild.text_channels[0] if guild.text_channels else None
        if not channel:
            continue
        for user in users:
            member = guild.get_member(user.user_id)
            if member:
                congrats_text = await ai_generate_birthday_congrats(member.mention, user.name)
                await channel.send(f"{member.mention} {congrats_text}")


def start_scheduler(bot: discord.Client):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
    scheduler.add_job(send_birthday_congratulations, 'cron', hour=9, minute=0, args=[bot])
    # scheduler.add_job(send_birthday_congratulations, 'interval', minutes=1, args=[bot])
    scheduler.start()
