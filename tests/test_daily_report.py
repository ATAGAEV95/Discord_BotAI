"""Unit-тесты для app/services/daily_report.py."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.daily_report import ChannelState, ReportGenerator


class TestReportGeneratorGetState:
    """Тесты метода get_state."""

    def test_creates_new_state(self) -> None:
        """Создает новый ChannelState для нового канала."""
        bot = MagicMock()
        rg = ReportGenerator(bot=bot)
        state = rg.get_state(12345)
        assert isinstance(state, ChannelState)
        assert isinstance(state.lock, asyncio.Lock)
        assert state.messages == []

    def test_reuses_existing_state(self) -> None:
        """Возвращает тот же ChannelState при повторном вызове."""
        bot = MagicMock()
        rg = ReportGenerator(bot=bot)
        state1 = rg.get_state(12345)
        state2 = rg.get_state(12345)
        assert state1 is state2

    def test_different_channels_different_states(self) -> None:
        """Разные каналы — разные объекты состояния."""
        bot = MagicMock()
        rg = ReportGenerator(bot=bot)
        state1 = rg.get_state(111)
        state2 = rg.get_state(222)
        assert state1 is not state2


class TestReportGeneratorInit:
    """Тесты инициализации ReportGenerator."""

    def test_initial_state(self) -> None:
        """Начальное состояние — пустой словарь каналов."""
        bot = MagicMock()
        rg = ReportGenerator(bot=bot)
        assert rg.bot is bot
        assert rg.channels == {}


class TestReportGeneratorAddMessage:
    """Тесты метода add_message."""

    @pytest.mark.asyncio
    @patch("app.services.daily_report.get_channel_messages", new_callable=AsyncMock, return_value=[])
    @patch("app.services.daily_report.save_channel_message", new_callable=AsyncMock)
    async def test_initializes_channel_state(
        self, mock_save: AsyncMock, mock_get: AsyncMock
    ) -> None:
        """Первое сообщение инициализирует состояние канала."""
        bot = MagicMock()
        bot.report_msg_limit = 15
        rg = ReportGenerator(bot=bot)
        await rg.add_message(100, "привет", "user1", 1)

        assert 100 in rg.channels
        state = rg.channels[100]
        assert len(state.messages) == 1
        assert state.messages[0]["content"] == "привет"
        assert state.messages[0]["author"] == "user1"

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

        assert len(rg.channels[100].messages) == 2

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
