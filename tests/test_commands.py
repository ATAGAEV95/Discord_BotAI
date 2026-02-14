"""Unit-тесты для app/cogs/commands.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord.ext import commands

from app.cogs.commands import BotCommands


@pytest.fixture
def mock_bot() -> MagicMock:
    """Фикстура для мока бота."""
    return MagicMock(spec=commands.Bot)


@pytest.fixture
def mock_ctx() -> AsyncMock:
    """Фикстура для мока контекста команды."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.name = "test_user"
    ctx.author.display_name = "Test User"
    ctx.author.id = 12345
    ctx.author.avatar.url = "http://avatar.url"
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 67890
    ctx.guild.name = "Test Guild"
    ctx.message = MagicMock(spec=discord.Message)
    ctx.message.content = ""
    return ctx


@pytest.fixture
def cog(mock_bot: MagicMock) -> BotCommands:
    """Фикстура для инициализации Cog."""
    return BotCommands(mock_bot)


# ── help_command ────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.cogs.commands.em.create_help_embed")
async def test_help_command(
    mock_create_help: MagicMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Команда !help отправляет embed."""
    mock_embed = MagicMock()
    mock_create_help.return_value = mock_embed

    await cog.help_command.callback(cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(embed=mock_embed)


# ── rank_command ────────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.cogs.commands.get_rank", new_callable=AsyncMock)
@patch("app.cogs.commands.em.create_rang_embed", new_callable=AsyncMock)
async def test_rank_command_show_user(
    mock_create_embed: AsyncMock,
    mock_get_rank: AsyncMock,
    cog: BotCommands,
    mock_ctx: AsyncMock,
) -> None:
    """Команда !rank показывает ранг пользователя."""
    mock_get_rank.return_value = 50
    mock_embed = MagicMock()
    mock_file = MagicMock()
    mock_create_embed.return_value = (mock_embed, mock_file)

    await cog.rank_command.callback(cog, mock_ctx)

    mock_get_rank.assert_called_once_with(12345, 67890)
    mock_ctx.send.assert_called_once_with(embed=mock_embed, file=mock_file)


@pytest.mark.asyncio
@patch("app.cogs.commands.em.create_rang_list_embed")
async def test_rank_command_list(
    mock_create_list: MagicMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Команда !rank list показывает список рангов."""
    mock_embed = MagicMock()
    mock_create_list.return_value = mock_embed

    await cog.rank_command.callback(cog, mock_ctx, arg="list")

    mock_ctx.send.assert_called_once_with(embed=mock_embed)


@pytest.mark.asyncio
@patch("app.cogs.commands.get_rank", new_callable=AsyncMock)
async def test_rank_command_error(
    mock_get_rank: AsyncMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Обработка ошибки в !rank."""
    mock_get_rank.side_effect = Exception("DB Error")

    await cog.rank_command.callback(cog, mock_ctx)

    mock_ctx.send.assert_called_with("Произошла ошибка при получении статистики: DB Error")


# ── birthday_command ────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.cogs.commands.save_birthday", new_callable=AsyncMock)
async def test_birthday_command_success(
    mock_save: AsyncMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Команда !birthday сохраняет дату."""
    await cog.birthday_command.callback(cog, mock_ctx, date="12.05")

    mock_save.assert_called_once_with("!birthday 12.05", "Test User", "test_user", 12345)
    mock_ctx.send.assert_called_with("Дата рождения сохранена.")


@pytest.mark.asyncio
@patch("app.cogs.commands.save_birthday", new_callable=AsyncMock)
async def test_birthday_command_value_error(
    mock_save: AsyncMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Ошибка валидации даты в !birthday."""
    mock_save.side_effect = ValueError("Неверный формат")

    await cog.birthday_command.callback(cog, mock_ctx, date="invalid")

    mock_ctx.send.assert_called_with("Неверный формат")


# ── manual_birthday_command ─────────────────────────────────────


@pytest.mark.asyncio
@patch("app.cogs.commands.send_birthday_congratulations", new_callable=AsyncMock)
async def test_manual_birthday_command(
    mock_send: AsyncMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Команда !check_birthday вызывает рассылку."""
    await cog.manual_birthday_command.callback(cog, mock_ctx)
    mock_send.assert_called_once_with(cog.bot)


# ── reset_command ───────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.core.handlers.clear_server_history")
async def test_reset_command(
    mock_clear: AsyncMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Команда !reset очищает историю."""
    mock_clear.return_value = "История очищена"
    await cog.reset_command.callback(cog, mock_ctx)

    mock_clear.assert_called_once_with(67890)
    mock_ctx.send.assert_called_with("История очищена")


# ── update_user_command ─────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.core.handlers.llama_manager.index_server_users", new_callable=AsyncMock)
async def test_update_user_command(
    mock_index: AsyncMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """Команда !update_user индексирует пользователей."""
    member = MagicMock()
    member.name = "user1"
    member.bot = False
    mock_ctx.guild.members = [member]

    await cog.update_user_command.callback(cog, mock_ctx)

    mock_index.assert_called_once_with(67890, ["user1"])
    assert "Список пользователей сервера обновлен" in mock_ctx.send.call_args[0][0]


# ── ai_provider_command ─────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.cogs.commands.get_available_providers")
@patch("app.cogs.commands.next_provider")
async def test_ai_provider_next(
    mock_next: MagicMock,
    mock_available: MagicMock,
    cog: BotCommands,
    mock_ctx: AsyncMock,
) -> None:
    """!ai без аргументов переключает на следующего провайдера."""
    mock_available.return_value = ["prov1", "prov2"]
    mock_next.return_value = "prov2"

    await cog.ai_provider_command.callback(cog, mock_ctx, name=None)

    mock_next.assert_called_once()
    mock_ctx.send.assert_called()
    assert "prov2" in mock_ctx.send.call_args[0][0]


@pytest.mark.asyncio
@patch("app.cogs.commands.get_available_providers")
@patch("app.cogs.commands.set_active_provider")
async def test_ai_provider_set_valid(
    mock_set: MagicMock,
    mock_available: MagicMock,
    cog: BotCommands,
    mock_ctx: AsyncMock,
) -> None:
    """!ai name устанавливает провайдера."""
    mock_available.return_value = ["prov1", "prov2"]

    await cog.ai_provider_command.callback(cog, mock_ctx, name="prov1")

    mock_set.assert_called_once_with("prov1")
    assert "переключён на **prov1**" in mock_ctx.send.call_args[0][0]


@pytest.mark.asyncio
@patch("app.cogs.commands.get_available_providers")
async def test_ai_provider_invalid(
    mock_available: MagicMock, cog: BotCommands, mock_ctx: AsyncMock
) -> None:
    """!ai invalid сообщает об ошибке."""
    mock_available.return_value = ["prov1", "prov2"]

    await cog.ai_provider_command.callback(cog, mock_ctx, name="invalid")

    assert "не найден" in mock_ctx.send.call_args[0][0]


# ── youtube_commands ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_youtube_command_success(cog: BotCommands, mock_ctx: AsyncMock) -> None:
    """!add_youtube добавляет канал."""
    cog.youtube_notifier.add_channel = AsyncMock(return_value=True)
    cog.bot.get_channel.return_value = MagicMock()

    await cog.add_youtube_command.callback(
        cog, mock_ctx, youtube_id="yt123", discord_channel_id=111, name="MyChannel"
    )

    cog.youtube_notifier.add_channel.assert_called_once()
    mock_ctx.send.assert_called_with("✅ Канал добавлен для отслеживания")


@pytest.mark.asyncio
async def test_youtube_toggle_command(cog: BotCommands, mock_ctx: AsyncMock) -> None:
    """!youtube on/off переключает статус."""
    cog.youtube_notifier.toggle_channel = AsyncMock(return_value=True)

    await cog.youtube_toggle_command.callback(cog, mock_ctx, action="off", name="MyChannel")

    cog.youtube_notifier.toggle_channel.assert_called_once_with("MyChannel", 67890, False)
    assert "отключено" in mock_ctx.send.call_args[0][0]


# ── on_command_error ────────────────────────────────────────────


@pytest.mark.asyncio
@patch("app.core.handlers.check_weather_intent", new_callable=AsyncMock)
@patch("app.core.handlers.check_search_intent", new_callable=AsyncMock)
@patch("app.core.handlers.ai_generate", new_callable=AsyncMock)
async def test_on_command_not_found_generates_ai_response(
    mock_ai: AsyncMock,
    mock_search: AsyncMock,
    mock_weather: AsyncMock,
    cog: BotCommands,
    mock_ctx: AsyncMock,
) -> None:
    """Неизвестная команда вызывает AI-генерацию."""
    error = commands.CommandNotFound()
    mock_ctx.message.content = "Как дела?"
    mock_ai.return_value = "Нормально"
    mock_weather.return_value = None
    mock_search.return_value = None

    await cog.on_command_error(mock_ctx, error)

    mock_ai.assert_called_once()
    mock_ctx.send.assert_called()
    assert "Нормально" in mock_ctx.send.call_args[0][0]


@pytest.mark.asyncio
async def test_on_missing_permissions(cog: BotCommands, mock_ctx: AsyncMock) -> None:
    """Ошибка прав доступа."""
    error = commands.MissingPermissions(["administrator"])
    await cog.on_command_error(mock_ctx, error)
    assert "недостаточно прав" in mock_ctx.send.call_args[0][0]
