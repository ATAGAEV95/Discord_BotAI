import discord
from discord.ext import commands

from app.core.scheduler import start_scheduler
from app.data.models import init_models
from app.services.daily_report import ReportGenerator
from app.services.telegram_notifier import telegram_notifier
from app.tools.utils import contains_only_urls


class DisBot(commands.Bot):
    """Кастомный класс бота Discord."""

    def __init__(
        self,
        command_prefix: str,
        intents: discord.Intents,
        help_command: commands.HelpCommand | None = None,
    ):
        """Инициализация бота."""
        super().__init__(
            command_prefix=command_prefix, intents=intents, help_command=help_command
        )
        self.report_generator: ReportGenerator | None = None

    async def setup_hook(self) -> None:
        """Загрузка расширений (Cogs) при старте бота."""
        await self.load_extension("app.cogs.commands")
        await self.load_extension("app.cogs.ranks")

    async def on_ready(self) -> None:
        """Инициализация при подключении бота к Discord."""
        await init_models()
        self.report_generator = ReportGenerator(self)
        start_scheduler(self)
        print("Бот успешно подключился к Discord")

    async def on_disconnect(self) -> None:
        """Обработка отключения от Discord."""
        print("Бот отключился от Discord")
        await telegram_notifier.send_message(
            "⚠️ <b>Discord бот отключился</b>\nСоединение с Discord потеряно"
        )

    async def on_resumed(self) -> None:
        """Обработка восстановления соединения с Discord."""
        print("Соединение с Discord восстановлено")
        await telegram_notifier.send_message(
            "✅ <b>Discord бот восстановил соединение</b>\nРабота продолжается"
        )

    async def on_message(self, message: discord.Message) -> None:
        """Обработка входящих сообщений."""
        if message.author.bot:
            return

        if len(message.content) > 1000:
            if message.content.startswith("!"):
                await message.channel.send(
                    f"Сообщение слишком длинное: {len(message.content)} символов! "
                    "Максимальная длина - 1000 символов."
                )
            return

        if not message.content.startswith("!"):
            if not message.content.strip():
                return

            if contains_only_urls(message.content):
                return

            if self.report_generator is not None:
                await self.report_generator.add_message(
                    message.channel.id,
                    message.content,
                    message.author.display_name,
                    message.id,
                )
            return

        await self.process_commands(message)
