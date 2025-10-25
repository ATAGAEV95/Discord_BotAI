import asyncio
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from app.data.request import delete_channel_messages, get_channel_messages, save_channel_message
from app.tools.prompt import UPDATED_REPORT_PROMPT

load_dotenv()

AI_TOKEN_PROXYAPI = os.getenv("AI_TOKEN")
AI_TOKEN_AITUNNEL = os.getenv("AI_TOKEN1")
AI_TOKEN_POLZA = os.getenv("AI_TOKEN_POLZA")
proxyapi = "https://api.proxyapi.ru/openai/v1"
aitunnel = "https://api.aitunnel.ru/v1/"
polza = "https://api.polza.ai/api/v1"

report_client = AsyncOpenAI(
    api_key=AI_TOKEN_AITUNNEL,
    base_url=aitunnel,
)


class ReportGenerator:
    """Класс ReportGenerator используется для накопления сообщений в Discord-канале и автоматической отправки
    отчета о содержимом канала после 60 минут без активности, при достижении порогового количества сообщений.
    """

    def __init__(self, bot):
        self.bot = bot
        self.channel_data = {}
        self.locks = {}

    def get_lock(self, channel_id):
        if channel_id not in self.locks:
            self.locks[channel_id] = asyncio.Lock()
        return self.locks[channel_id]

    async def add_message(self, channel_id: int, message: str, author: str, message_id: int) -> None:
        """Добавляет сообщение в историю канала и обновляет время последней активности.
        При достижении или превышении количества 15 сообщений запускается задача на отправку отчета через 60 минут.
        """
        lock = self.get_lock(channel_id)
        async with lock:
            try:
                await save_channel_message(channel_id, message_id, author, message)
            except Exception as e:
                print(f"Ошибка при сохранении сообщения в канал {channel_id}: {e}")

            if channel_id not in self.channel_data:
                self.channel_data[channel_id] = {
                    "messages": [],
                    "timer": None,
                    "last_message_time": datetime.now(),
                }

            self.channel_data[channel_id]["messages"].append(
                {"id": message_id, "content": message, "author": author, "timestamp": datetime.now()}
            )

            self.channel_data[channel_id]["last_message_time"] = datetime.now()
            if (
                self.channel_data[channel_id]["timer"]
                and not self.channel_data[channel_id]["timer"].done()
            ):
                try:
                    self.channel_data[channel_id]["timer"].cancel()
                except Exception as e:
                    print(f"Ошибка при отмене таймера для канала {channel_id}: {e}")

            try:
                db_messages = await get_channel_messages(channel_id)
            except Exception as e:
                print(f"Ошибка при получении сообщений из канала {channel_id}: {e}")
                db_messages = []

            cache_count = len(self.channel_data[channel_id]["messages"])
            db_count = len(db_messages)

            if cache_count >= 15 or db_count >= 15:
                self.channel_data[channel_id]["timer"] = asyncio.create_task(
                    self.start_report_timer(channel_id)
                )

    async def start_report_timer(self, channel_id: int):
        """Запускает задачу, которая ожидает 60 минут. Если после последнего сообщения прошло
        не менее 60 минут без активности, то генерируется и отправляется аналитический отчет.
        """
        await asyncio.sleep(3600)
        lock = self.get_lock(channel_id)
        async with lock:
            if channel_id not in self.channel_data:
                return

            last_time = self.channel_data[channel_id]["last_message_time"]
            if (datetime.now() - last_time) < timedelta(minutes=60):
                return

        await self.generate_and_send_report(channel_id)

    async def generate_and_send_report(self, channel_id: int):
        """Генерирует аналитический отчет на основе накопленных сообщений с использованием GPT-модели
        и отправляет его в канал.
        """
        lock = self.get_lock(channel_id)
        async with lock:
            try:
                messages = await get_channel_messages(channel_id)
            except Exception as e:
                print(
                    f"Ошибка при получении сообщений для генерации отчета в канале {channel_id}: {e}"
                )
                return

            if not messages or len(messages) < 15:
                return

            messages_text = "\n".join(
                f"[ID:{msg.message_id}] {msg.author}: {msg.content}" for msg in messages
            )

            message = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=UPDATED_REPORT_PROMPT,
                ),
                ChatCompletionUserMessageParam(
                    role="user", content=f"Сообщения из канала:\n{messages_text}"
                ),
            ]

            try:
                response = await report_client.chat.completions.create(
                    model="gpt-5-mini", messages=message, temperature=0.0, top_p=0.01, max_tokens=500
                )
                report = response.choices[0].message.content
            except Exception as e:
                print(f"Ошибка генерации отчета: {e}")
                report = "Ошибка генерации отчета"

            if "ID:" in report:
                channel = self.bot.get_channel(channel_id)
                guild_id = channel.guild.id if channel and hasattr(channel, "guild") else "UNKNOWN"

                for msg in messages:
                    msg_id = str(msg.message_id)
                    if f"[ID:{msg_id}]" in report:
                        link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                        report = report.replace(f"[ID:{msg_id}]", f"[ссылка]({link})")

            try:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(report)
            except Exception as e:
                print(f"Ошибка отправки отчета в канал {channel_id}: {e}")

            try:
                await delete_channel_messages(channel_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщений из канала {channel_id}: {e}")

            if channel_id in self.channel_data:
                del self.channel_data[channel_id]
                if channel_id in self.locks:
                    del self.locks[channel_id]
