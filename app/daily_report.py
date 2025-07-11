import os
import asyncio
from datetime import datetime, timedelta
import tiktoken
from openai import AsyncOpenAI
from dotenv import load_dotenv


load_dotenv()

report_client = AsyncOpenAI(
    api_key=os.getenv('AI_TOKEN'),
    base_url="https://api.proxyapi.ru/openai/v1",
)


channel_data = {}
ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")


REPORT_PROMPT = """
Ты аналитик дискорд-сервера. Проанализируй сообщения из канала и создай краткий отчет.
Основные требования:
1. Выдели 2-3 основные темы обсуждения
2. Сохраняй деловой стиль
3. Объем: кратко (1-2 предложения) для удобства чтения в чате

Пример структуры:
Основные темы: 
- [тема]
- [тема]
"""


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


class ReportGenerator:
    def __init__(self, bot):
        self.bot = bot

    async def add_message(self, channel_id: int, message: str, author: str) -> None:
        """Добавляет сообщение в историю канала и управляет таймером"""
        if channel_id not in channel_data:
            channel_data[channel_id] = {
                'messages': [],
                'timer': None,
                'last_message_time': datetime.utcnow()
            }

        channel_data[channel_id]['messages'].append({
            'content': message,
            'author': author,
            'timestamp': datetime.utcnow()
        })

        channel_data[channel_id]['last_message_time'] = datetime.utcnow()
        if channel_data[channel_id]['timer'] and not channel_data[channel_id]['timer'].done():
            try:
                channel_data[channel_id]['timer'].cancel()
            except:
                pass

        if len(channel_data[channel_id]['messages']) >= 5:
            channel_data[channel_id]['timer'] = asyncio.create_task(
                self.start_report_timer(channel_id)
            )

    async def start_report_timer(self, channel_id: int):
        """Запускает 60-минутный таймер для формирования отчета"""
        try:
            await asyncio.sleep(30)

            if channel_id not in channel_data:
                return

            last_time = channel_data[channel_id]['last_message_time']
            if (datetime.utcnow() - last_time) < timedelta(seconds=30):
                return

            await self.generate_and_send_report(channel_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Ошибка в таймере для канала {channel_id}: {e}")

    async def generate_and_send_report(self, channel_id: int):
        """Генерирует и отправляет отчет для канала"""
        if channel_id not in channel_data or len(channel_data[channel_id]['messages']) < 5:
            return

        messages_text = "\n".join(
            f"[{msg['timestamp'].strftime('%H:%M')}] {msg['author']}: {msg['content']}"
            for msg in channel_data[channel_id]['messages']
        )

        messages = [
            {"role": "system", "content": REPORT_PROMPT},
            {"role": "user", "content": f"Сообщения из канала:\n{messages_text}"}
        ]

        total_tokens = sum(count_tokens(msg["content"]) for msg in messages)
        max_tokens = min(3500 - total_tokens, 500)

        try:
            response = await report_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                max_tokens=max_tokens
            )
            report = response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка генерации отчета: {e}")
            report = "Ошибка генерации отчета"

        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(f"**Отчет по активности:**\n{report}")
        except Exception as e:
            print(f"Ошибка отправки отчета в канал {channel_id}: {e}")

        if channel_id in channel_data:
            del channel_data[channel_id]
