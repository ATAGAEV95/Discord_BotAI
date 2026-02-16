"""Unit-тесты для app/services/daily_report.py."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.daily_report import ReportGenerator


class TestReportGeneratorGetLock:
    """Тесты метода get_lock."""

    def test_creates_new_lock(self) -> None:
        """Создает новый Lock для нового канала."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        rg = ReportGenerator(bot=bot)
        lock = rg.get_lock(12345)
        assert isinstance(lock, asyncio.Lock)

    def test_reuses_existing_lock(self) -> None:
        """Возвращает тот же Lock при повторном вызове для того же канала."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        rg = ReportGenerator(bot=bot)
        lock1 = rg.get_lock(12345)
        lock2 = rg.get_lock(12345)
        assert lock1 is lock2

    def test_different_channels_different_locks(self) -> None:
        """Разные каналы — разные Lock'и."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        rg = ReportGenerator(bot=bot)
        lock1 = rg.get_lock(111)
        lock2 = rg.get_lock(222)
        assert lock1 is not lock2


class TestReportGeneratorInit:
    """Тесты инициализации ReportGenerator."""

    def test_initial_state(self) -> None:
        """Начальное состояние — пустые словари."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        bot.report_time_limit = 60
        rg = ReportGenerator(bot=bot)
        assert rg.bot is bot
        assert rg.channel_data == {}
        assert rg.locks == {}


class TestReportGeneratorAddMessage:
    """Тесты метода add_message."""

    @pytest.mark.asyncio
    @patch("app.services.daily_report.get_channel_messages", new_callable=AsyncMock, return_value=[])
    @patch("app.services.daily_report.save_channel_message", new_callable=AsyncMock)
    async def test_initializes_channel_data(
        self, mock_save: AsyncMock, mock_get: AsyncMock
    ) -> None:
        """Первое сообщение инициализирует channel_data для канала."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        rg = ReportGenerator(bot=bot)
        await rg.add_message(100, "привет", "user1", 1)

        assert 100 in rg.channel_data
        assert len(rg.channel_data[100]["messages"]) == 1
        assert rg.channel_data[100]["messages"][0]["content"] == "привет"
        assert rg.channel_data[100]["messages"][0]["author"] == "user1"

    @pytest.mark.asyncio
    @patch("app.services.daily_report.get_channel_messages", new_callable=AsyncMock, return_value=[])
    @patch("app.services.daily_report.save_channel_message", new_callable=AsyncMock)
    async def test_accumulates_messages(
        self, mock_save: AsyncMock, mock_get: AsyncMock
    ) -> None:
        """Несколько сообщений накапливаются."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        rg = ReportGenerator(bot=bot)
        await rg.add_message(100, "привет", "user1", 1)
        await rg.add_message(100, "мир", "user2", 2)

        assert len(rg.channel_data[100]["messages"]) == 2

    @pytest.mark.asyncio
    @patch("app.services.daily_report.get_channel_messages", new_callable=AsyncMock, return_value=[])
    @patch("app.services.daily_report.save_channel_message", new_callable=AsyncMock)
    async def test_calls_save_channel_message(
        self, mock_save: AsyncMock, mock_get: AsyncMock
    ) -> None:
        """Вызывает save_channel_message для сохранения в БД."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        rg = ReportGenerator(bot=bot)
        await rg.add_message(100, "привет", "user1", 42)

        mock_save.assert_called_once_with(100, 42, "user1", "привет")
