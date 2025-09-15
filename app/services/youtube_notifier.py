import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import select

from app.data.models import YouTubeChannel, YouTubeVideo, async_session

load_dotenv()


class YouTubeNotifier:
    def __init__(self, bot):
        self.bot = bot
        self.youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))

    async def check_new_videos(self):
        """Проверяет новые видео на всех отслеживаемых каналах"""
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
        """Проверяет новые видео для конкретного канала и публикует только последнее"""
        try:
            req = self.youtube.search().list(
                channelId=channel.channel_id,
                order="date",
                part="snippet",
                type="video",
                maxResults=1,
            )
            response = await asyncio.to_thread(req.execute)

            if not response.get("items"):
                return

            item = response["items"][0]
            video_id = item["id"]["videoId"]

            async with async_session() as session:
                video_query = select(YouTubeVideo).where(YouTubeVideo.video_id == video_id)
                video_result = await session.execute(video_query)
                existing_video = video_result.scalar_one_or_none()

                if not existing_video:
                    new_video = YouTubeVideo(
                        video_id=video_id,
                        channel_id=channel.channel_id,
                        title=item["snippet"]["title"],
                        published_at=datetime.strptime(
                            item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"
                        ),
                    )
                    session.add(new_video)
                    await session.commit()

                    discord_channel = self.bot.get_channel(channel.discord_channel_id)
                    if discord_channel:
                        await discord_channel.send(
                            f"🎥 **Новое видео на канале [{channel.name}](https://www.youtube.com/channel/{channel.channel_id})!**\n"
                            f"https://www.youtube.com/watch?v={video_id}"
                        )
                channel_query = select(YouTubeChannel).where(YouTubeChannel.id == channel.id)
                channel_result = await session.execute(channel_query)
                channel_to_update = channel_result.scalar_one()
                channel_to_update.last_checked = datetime.now()
                await session.commit()

        except HttpError as e:
            print(f"YouTube API error: {e}")
        except Exception as e:
            print(f"Ошибка при обработке канала {channel.name}: {e}")

    async def add_channel(self, youtube_channel_id, discord_channel_id, name):
        """Добавляет новый канал для отслеживания"""
        try:
            async with async_session() as session:
                query = select(YouTubeChannel).where(YouTubeChannel.channel_id == youtube_channel_id)
                result = await session.execute(query)
                existing_channel = result.scalar_one_or_none()

                if existing_channel:
                    return False

                channel = YouTubeChannel(
                    channel_id=youtube_channel_id, discord_channel_id=discord_channel_id, name=name
                )
                session.add(channel)
                await session.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении YouTube канала: {e}")
            return False
