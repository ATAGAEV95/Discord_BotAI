import os

import aiohttp


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram."""

    def __init__(self) -> None:
        """Инициализирует клиент Telegram-уведомлений."""
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            print(
                "Telegram уведомления отключены: отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID"
            )

    async def send_message(self, message: str) -> bool:
        """Отправляет сообщение в Telegram."""
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"Ошибка отправки в Telegram: статус {response.status}")
                        return False
        except Exception as e:
            print(f"Ошибка отправки сообщения в Telegram: {e}")
            return False


telegram_notifier = TelegramNotifier()
