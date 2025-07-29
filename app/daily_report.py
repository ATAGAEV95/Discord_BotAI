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


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


class ReportGenerator:
    """Генерирует и управляет отчетами о сообщениях в Discord-боте."""

    def __init__(self, bot):
        """Инициализирует экземпляр класса ReportGenerator."""
        self.bot = bot

    async def add_message(self, channel_id: int, message: str, author: str, message_id: int) -> None:
        """Добавляет сообщение в историю отчетов."""
        if channel_id not in channel_data:
            channel_data[channel_id] = {
                'messages': [],
                'timer': None,
                'last_message_time': datetime.now()
            }

        channel_data[channel_id]['messages'].append({
            'id': message_id,
            'content': message,
            'author': author,
            'timestamp': datetime.now()
        })

        channel_data[channel_id]['last_message_time'] = datetime.now()
        if channel_data[channel_id]['timer'] and not channel_data[channel_id]['timer'].done():
            try:
                channel_data[channel_id]['timer'].cancel()
            except:
                pass

        if len(channel_data[channel_id]['messages']) >= 10:
            channel_data[channel_id]['timer'] = asyncio.create_task(
                self.start_report_timer(channel_id)
            )

    async def start_report_timer(self, channel_id: int):
        """Запускает 60-минутный таймер для формирования отчета"""
        try:
            await asyncio.sleep(3600)

            if channel_id not in channel_data:
                return

            last_time = channel_data[channel_id]['last_message_time']
            if (datetime.now() - last_time) < timedelta(minutes=60):
                return

            await self.generate_and_send_report(channel_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Ошибка в таймере для канала {channel_id}: {e}")

    async def generate_and_send_report(self, channel_id: int):
        """Генерирует и отправляет отчет для канала"""
        if channel_id not in channel_data or len(channel_data[channel_id]['messages']) < 10:
            return

        messages_text = "\n".join(
            f"[ID:{msg['id']}] [{msg['timestamp'].strftime('%H:%M')}] {msg['author']}: {msg['content']}"
            for msg in channel_data[channel_id]['messages']
        )

        UPDATED_REPORT_PROMPT = """
        Ты аналитик дискорд-сервера. Проанализируй сообщения и выдели ОСНОВНЫЕ темы обсуждения. 
        Жесткие правила:
        1. Только ключевые темы! Игнорируй: 
           - Технические реплики ("опа", "нормально так") 
           - Уточняющие вопросы
           - Второстепенные ответвления
        2. Максимально обобщай смежные аспекты в ОДНУ тему. Объединяй сообщения в одну тему, если они:
           - Относятся к одному корневому сообщению (трейлер, новость, мем)
           - Обсуждают один объект (игра, персонаж, событие)
           - Развивают одну ключевую идею (критика, сравнение, совет)
        3. Для КАЖДОЙ темы укажи ID первого сообщения в формате [ID:123456789]
        4. Объем: очень кратко (в двух-трех словах) для удобства чтения в чате

        Пример структуры:
        - [тема] [ID:123456789]
        - [тема] [ID:987654321]

        Ключевые принципы группировки:
        • Сообщения = ответы на один стимул → ОДНА тема
        • Разные аспекты одного объекта → ОДНА тема
        • Реакции + мнения + шутки по одной теме → ОДНА тема
        """

        messages = [
            {"role": "system", "content": UPDATED_REPORT_PROMPT},
            {"role": "user", "content": f"Сообщения из канала:\n{messages_text}"}
        ]

        total_tokens = sum(count_tokens(msg["content"]) for msg in messages)
        max_tokens = min(3500 - total_tokens, 500)

        try:
            response = await report_client.chat.completions.create(
                model="gpt-4.1",
                # model="gpt-4.1-mini",
                messages=messages,
                max_tokens=max_tokens
            )
            report = response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка генерации отчета: {e}")
            report = "Ошибка генерации отчета"

        if "ID:" in report:
            channel = self.bot.get_channel(channel_id)
            guild_id = channel.guild.id if channel and hasattr(channel, 'guild') else "UNKNOWN"

            for msg in channel_data[channel_id]['messages']:
                msg_id = str(msg['id'])
                if f"[ID:{msg_id}]" in report:
                    link = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
                    report = report.replace(f"[ID:{msg_id}]", f"[ссылка]({link})")

        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(report)
        except Exception as e:
            print(f"Ошибка отправки отчета в канал {channel_id}: {e}")

        if channel_id in channel_data:
            del channel_data[channel_id]
