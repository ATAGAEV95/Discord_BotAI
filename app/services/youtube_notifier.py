import asyncio
import os
from datetime import datetime, timedelta

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

            video_ids = [item["id"]["videoId"] for item in response["items"]]

            video_req = self.youtube.videos().list(
                id=",".join(video_ids), part="snippet,liveStreamingDetails"
            )
            video_response = await asyncio.to_thread(video_req.execute)

            async with async_session() as session:
                for item in video_response.get("items", []):
                    video_id = item["id"]

                    video_query = select(YouTubeVideo).where(
                        YouTubeVideo.video_id == video_id, YouTubeVideo.guild_id == channel.guild_id
                    )
                    video_result = await session.execute(video_query)
                    existing_video = video_result.scalar_one_or_none()

                    if not existing_video:
                        is_live = "liveStreamingDetails" in item
                        live_status = item.get("snippet", {}).get("liveBroadcastContent", "none")
                        is_current_live = is_live and live_status == "live"
                        is_upcoming_live = is_live and live_status == "upcoming"

                        new_video = YouTubeVideo(
                            video_id=video_id,
                            guild_id=channel.guild_id,
                            channel_id=channel.channel_id,
                            title=item["snippet"]["title"],
                            published_at=datetime.strptime(
                                item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            is_live=is_current_live or is_upcoming_live,
                        )
                        session.add(new_video)

                        discord_channel = self.bot.get_channel(channel.discord_channel_id)
                        if discord_channel:
                            if is_current_live:
                                message = (
                                    f"🔴 **Прямой эфир на канале [{channel.name}](https://www.youtube.com/channel/{channel.channel_id})!**\n"
                                    f"https://www.youtube.com/watch?v={video_id}"
                                )
                            elif is_upcoming_live:
                                scheduled_time = item.get("liveStreamingDetails", {}).get(
                                    "scheduledStartTime"
                                )
                                if scheduled_time:
                                    scheduled_dt = datetime.strptime(
                                        scheduled_time, "%Y-%m-%dT%H:%M:%SZ"
                                    )
                                    message = (
                                        f"📅 **Запланирован стрим на канале [{channel.name}](https://www.youtube.com/channel/{channel.channel_id})!**\n"
                                        f"⏰ Начало: {(scheduled_dt + timedelta(hours=3)).strftime('%d.%m.%Y в %H:%M')} MSK\n"
                                        f"https://www.youtube.com/watch?v={video_id}"
                                    )
                                else:
                                    message = (
                                        f"📅 **Запланирован стрим на канале [{channel.name}](https://www.youtube.com/channel/{channel.channel_id})!**\n"
                                        f"https://www.youtube.com/watch?v={video_id}"
                                    )
                            else:
                                message = (
                                    f"🎥 **Новое видео на канале [{channel.name}](https://www.youtube.com/channel/{channel.channel_id})!**\n"
                                    f"https://www.youtube.com/watch?v={video_id}"
                                )

                            await discord_channel.send(message)

                channel_query = select(YouTubeChannel).where(YouTubeChannel.id == channel.id)
                channel_result = await session.execute(channel_query)
                channel_to_update = channel_result.scalar_one()
                channel_to_update.last_checked = datetime.now()
                await session.commit()

        except HttpError as e:
            print(f"YouTube API error: {e}")
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"Ошибка отправки сообщения в канал {channel.name}: {e}")
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
