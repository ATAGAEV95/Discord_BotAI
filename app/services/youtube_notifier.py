import asyncio
from datetime import datetime

import feedparser
from dotenv import load_dotenv
from sqlalchemy import select

from app.data.models import YouTubeChannel, YouTubeVideo, async_session

load_dotenv()


class YouTubeNotifier:
    def __init__(self, bot):
        self.bot = bot

    async def check_new_videos(self):
        try:
            async with async_session() as session:
                query = select(YouTubeChannel)
                result = await session.execute(query)
                channels = result.scalars().all()

                for channel in channels:
                    await self._check_channel_videos(channel)
        except Exception as e:
            print(f"Ошибка при проверке YouTube видео: {e}")

    async def _check_channel_videos(self, channel):
        try:
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel.channel_id}"
            feed = await asyncio.to_thread(feedparser.parse, url)

            if feed.status != 200 or not feed.entries:
                print(f"❌ Неверный или недоступный канал: {channel.name} (ID: {channel.channel_id})")
                print(f"HTTP статус: {feed.status}")
                return

            latest_video = feed.entries[0]
            video_id = latest_video.get('yt_videoid')
            author = latest_video.get('author')
            published_at = datetime.now()
            print(latest_video.title)

            async with async_session() as session:
                video_query = select(YouTubeVideo).where(
                    YouTubeVideo.video_id == video_id,
                    YouTubeVideo.guild_id == channel.guild_id
                )
                video_result = await session.execute(video_query)
                existing_video = video_result.scalar_one_or_none()

                if not existing_video:
                    is_live = "Live" in latest_video.title or "прямая" in latest_video.title.lower()
                    new_video = YouTubeVideo(
                        video_id=video_id,
                        guild_id=channel.guild_id,
                        channel_id=channel.channel_id,
                        title=latest_video.title,
                        published_at=published_at,
                        is_live=is_live,
                    )
                    session.add(new_video)

                    discord_channel = self.bot.get_channel(channel.discord_channel_id)
                    if discord_channel:
                        if is_live:
                            message = (
                                f"🔴 **Прямой эфир на канале [{author}](https://www.youtube.com/channel/{channel.channel_id})!**\n"
                                f"{latest_video.link}"
                            )
                        else:
                            message = (
                                f"🎥 **Новое видео на канале [{author}](https://www.youtube.com/channel/{channel.channel_id})!**\n"
                                f"{latest_video.link}"
                            )
                        await discord_channel.send(message)

                channel_query = select(YouTubeChannel).where(YouTubeChannel.id == channel.id)
                channel_result = await session.execute(channel_query)
                channel_to_update = channel_result.scalar_one()
                channel_to_update.last_checked = datetime.now()
                await session.commit()

        except Exception as e:
            print(f"Ошибка при обработке канала {channel.name}: {e}")

    async def add_channel(self, youtube_channel_id, discord_channel_id, name, guild_id):
        try:
            async with async_session() as session:
                query = select(YouTubeChannel).where(
                    YouTubeChannel.channel_id == youtube_channel_id,
                    YouTubeChannel.discord_channel_id == discord_channel_id,
                    YouTubeChannel.guild_id == guild_id,
                )
                result = await session.execute(query)
                existing_channel = result.scalar_one_or_none()

                if existing_channel:
                    return False

                channel = YouTubeChannel(
                    channel_id=youtube_channel_id,
                    discord_channel_id=discord_channel_id,
                    name=name,
                    guild_id=guild_id,
                )
                session.add(channel)
                await session.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении YouTube канала: {e}")
            return False
