"""Unit-тесты для app/core/handlers.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.handlers import ai_generate_birthday_congrats, clear_server_history

# ── ai_generate_birthday_congrats ───────────────────────────────


class TestAiGenerateBirthdayCongrats:
    """Тесты для функции ai_generate_birthday_congrats."""

    @pytest.mark.asyncio
    @patch("app.core.handlers.client")
    async def test_returns_generated_text(self, mock_client: MagicMock) -> None:
        """Возвращает сгенерированный текст при успешном вызове API."""
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "С днём рождения, Арби!"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        result = await ai_generate_birthday_congrats("atagaev")
        assert "С днём рождения" in result
        assert "Арби" in result

    @pytest.mark.asyncio
    @patch("app.core.handlers.client")
    async def test_fallback_on_error(self, mock_client: MagicMock) -> None:
        """При ошибке API возвращает fallback-поздравление."""
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

        result = await ai_generate_birthday_congrats("test_user")
        assert "Поздравляем с днём рождения" in result
        assert "🎉" in result


# ── clear_server_history ────────────────────────────────────────


class TestClearServerHistory:
    """Тесты для функции clear_server_history."""

    @pytest.mark.asyncio
    @patch("app.core.handlers.llama_manager")
    async def test_deletes_non_user_documents(self, mock_llama: MagicMock) -> None:
        """Удаляет документы, не являющиеся server_users."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["doc1", "doc2", "doc3"],
            "metadatas": [
                {"document_type": "message"},
                {"document_type": "server_users"},
                {"document_type": "context"},
            ],
        }
        mock_llama.get_server_collection.return_value = mock_collection

        result = await clear_server_history(12345)
        mock_collection.delete.assert_called_once_with(ids=["doc1", "doc3"])
        assert "2" in result
        assert "Удалено" in result

    @pytest.mark.asyncio
    @patch("app.core.handlers.llama_manager")
    async def test_empty_collection(self, mock_llama: MagicMock) -> None:
        """Пустая коллекция — сообщение о пустом индексе."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        mock_llama.get_server_collection.return_value = mock_collection

        result = await clear_server_history(12345)
        assert "пуст" in result

    @pytest.mark.asyncio
    @patch("app.core.handlers.llama_manager")
    async def test_only_server_users(self, mock_llama: MagicMock) -> None:
        """Только документы server_users — ничего не удаляется."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "metadatas": [{"document_type": "server_users"}],
        }
        mock_llama.get_server_collection.return_value = mock_collection

        result = await clear_server_history(12345)
        mock_collection.delete.assert_not_called()
        assert "нет документов" in result

    @pytest.mark.asyncio
    @patch("app.core.handlers.llama_manager")
    async def test_exception_handling(self, mock_llama: MagicMock) -> None:
        """При ошибке — сообщение об ошибке."""
        mock_llama.get_server_collection.side_effect = Exception("DB Error")

        result = await clear_server_history(12345)
        assert "ошибка" in result.lower()
