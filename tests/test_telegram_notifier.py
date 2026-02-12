"""Unit-тесты для app/services/telegram_notifier.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.telegram_notifier import TelegramNotifier

_PATCH_SESSION = "app.services.telegram_notifier.aiohttp.ClientSession"


class TestTelegramNotifierInit:
    """Тесты инициализации TelegramNotifier."""

    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test_token", "TELEGRAM_CHAT_ID": "123"})
    def test_enabled_with_env_vars(self) -> None:
        """С валидными env-переменными — enabled=True."""
        notifier = TelegramNotifier()
        assert notifier.enabled is True
        assert notifier.bot_token == "test_token"
        assert notifier.chat_id == "123"

    @patch.dict("os.environ", {}, clear=True)
    def test_disabled_without_env_vars(self) -> None:
        """Без env-переменных — enabled=False."""
        notifier = TelegramNotifier()
        assert notifier.enabled is False


class TestTelegramNotifierSendMessage:
    """Тесты метода send_message."""

    @pytest.mark.asyncio
    async def test_disabled_returns_false(self) -> None:
        """Disabled notifier возвращает False без HTTP-запроса."""
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        notifier.enabled = False
        result = await notifier.send_message("тест")
        assert result is False

    @pytest.mark.asyncio
    async def test_enabled_success(self) -> None:
        """Успешная отправка — возвращает True."""
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        notifier.enabled = True
        notifier.bot_token = "test_token"
        notifier.chat_id = "123"

        mock_response = MagicMock()
        mock_response.status = 200

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response

        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_post_cm

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session_instance

        with patch(_PATCH_SESSION, return_value=mock_session_cm):
            result = await notifier.send_message("тест")
            assert result is True

    @pytest.mark.asyncio
    async def test_enabled_error_returns_false(self) -> None:
        """Ошибка HTTP → возвращает False."""
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        notifier.enabled = True
        notifier.bot_token = "test_token"
        notifier.chat_id = "123"

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(_PATCH_SESSION, return_value=mock_session):
            result = await notifier.send_message("тест")
            assert result is False

    @pytest.mark.asyncio
    async def test_network_exception_returns_false(self) -> None:
        """Исключение при отправке → False."""
        notifier = TelegramNotifier.__new__(TelegramNotifier)
        notifier.enabled = True
        notifier.bot_token = "test_token"
        notifier.chat_id = "123"

        mock_session = AsyncMock()
        mock_session.post.side_effect = ConnectionError("Нет сети")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(_PATCH_SESSION, return_value=mock_session):
            result = await notifier.send_message("тест")
            assert result is False
