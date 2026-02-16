import asyncio
from collections.abc import Callable

from discord.ext import commands
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

import app.core.embeds as em
from app.core import handlers
from app.core.ai_config import (
    get_active_provider,
    get_available_providers,
    get_client,
    get_model,
    next_provider,
    set_active_provider,
)
from app.core.bot import DisBot
from app.core.scheduler import send_birthday_congratulations
from app.data.request import get_rank, save_birthday
from app.services.youtube_notifier import YouTubeNotifier
from app.tools.prompt import ROAST_PERSONAS, ROAST_PROMPT, USER_DESCRIPTIONS
from app.tools.utils import clean_text, get_rank_description, replace_emojis

ALLOWED_USERS = {"atagaev"}


def admin_or_owner() -> Callable:
    """Проверка: администратор или разрешённый пользователь."""

    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.name in ALLOWED_USERS:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        raise commands.MissingPermissions(["administrator"])

    return commands.check(predicate)


class BotCommands(commands.Cog):
    """Все команды бота."""

    def __init__(self, bot: DisBot) -> None:
        """Инициализация Cog."""
        self.bot = bot
        self.youtube_notifier = YouTubeNotifier(bot)

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context) -> None:
        """Показать список команд."""
        embed = em.create_help_embed()
        await ctx.send(embed=embed)

    @commands.command(name="rank")
    async def rank_command(self, ctx: commands.Context, arg: str | None = None) -> None:
        """Показать ранг пользователя или список рангов.

        Если указан аргумент "list", отображает список всех рангов.
        В противном случае показывает текущий ранг автора сообщения.
        """
        if arg == "list":
            embed = em.create_rang_list_embed()
            await ctx.send(embed=embed)
            return

        try:
            server_id = ctx.guild.id if ctx.guild else None
            message_count = await get_rank(ctx.author.id, server_id)
            rank_description = get_rank_description(int(message_count))

            avatar_url = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )

            embed, file = await em.create_rang_embed(
                ctx.author.display_name,
                message_count,
                rank_description["description"],
                avatar_url,
                server_id,
                ctx.author.id,
            )
            await ctx.send(embed=embed, file=file)
        except ValueError as ve:
            await ctx.send(str(ve))
        except Exception as e:
            await ctx.send(f"Произошла ошибка при получении статистики: {e}")

    @commands.command(name="birthday")
    async def birthday_command(self, ctx: commands.Context, *, date: str) -> None:
        """Сохранить дату рождения."""
        try:
            await save_birthday(
                f"!birthday {date}",
                ctx.author.display_name,
                ctx.author.name,
                ctx.author.id,
            )
            await ctx.send("Дата рождения сохранена.")
        except ValueError as ve:
            await ctx.send(str(ve))
        except Exception as e:
            await ctx.send(f"Произошла ошибка при сохранении даты рождения: {e}")

    @commands.command(name="check_birthday")
    @commands.guild_only()
    async def manual_birthday_command(self, ctx: commands.Context) -> None:
        """Ручная отправка поздравлений с днем рождения."""
        await send_birthday_congratulations(self.bot)

    @commands.command(name="reset")
    @commands.guild_only()
    async def reset_command(self, ctx: commands.Context) -> None:
        """Очистить историю сервера (только для администраторов)."""
        answer = await handlers.clear_server_history(ctx.guild.id)
        await ctx.send(answer)

    @commands.command(name="update_user")
    @commands.guild_only()
    async def update_user_command(self, ctx: commands.Context) -> None:
        """Обновить список пользователей сервера (только для администраторов)."""
        try:
            server = ctx.guild
            members = server.members
            all_server_users = [f"{member.name}" for member in members if not member.bot]

            await handlers.llama_manager.index_server_users(server.id, all_server_users)

            await ctx.send(
                f"✅ Список пользователей сервера обновлен! "
                f"Добавлено {len(all_server_users)} пользователей."
            )
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {e}")

    @commands.command(name="add_youtube")
    @commands.guild_only()
    @admin_or_owner()
    async def add_youtube_command(
        self, ctx: commands.Context, youtube_id: str, discord_channel_id: int, *, name: str
    ) -> None:
        """Добавить YouTube канал для отслеживания."""
        try:
            channel = self.bot.get_channel(discord_channel_id)
            if channel is None:
                await ctx.send("❌ Канал не найден!")
                return

            success = await self.youtube_notifier.add_channel(
                youtube_id, discord_channel_id, name, ctx.guild.id
            )
            if success:
                await ctx.send("✅ Канал добавлен для отслеживания")
            else:
                await ctx.send("❌ Ошибка при добавлении канала")
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {e}")

    @commands.command(name="youtube")
    @commands.guild_only()
    @admin_or_owner()
    async def youtube_toggle_command(
        self, ctx: commands.Context, action: str, *, name: str
    ) -> None:
        """Включить или отключить отслеживание YouTube канала."""
        action = action.lower()
        if action not in ("on", "off"):
            await ctx.send("❌ Используйте: `!youtube on/off название_канала`")
            return

        active = action == "on"
        result = await self.youtube_notifier.toggle_channel(name, ctx.guild.id, active)

        if result is None:
            await ctx.send(f"❌ Канал **{name}** не найден на этом сервере.")
        elif result:
            status = "включено" if active else "отключено"
            emoji = "✅" if active else "⏸️"
            await ctx.send(f"{emoji} Отслеживание канала **{name}** {status}.")
        else:
            await ctx.send("❌ Ошибка при изменении статуса канала.")

    @commands.command(name="ai")
    @admin_or_owner()
    async def ai_provider_command(self, ctx: commands.Context, name: str | None = None) -> None:
        """Переключить AI-провайдера.

        !ai — переключить на следующего провайдера
        !ai name — переключить на указанного провайдера
        """
        available = get_available_providers()

        if name is None:
            new_provider = next_provider()
            await ctx.send(
                f"🔄 Провайдер переключён на **{new_provider}**\n"
                f"Доступные: {', '.join(available)}"
            )
            return

        if name not in available:
            await ctx.send(
                f"❌ Провайдер **{name}** не найден.\n"
                f"Доступные: {', '.join(available)}"
            )
            return

        if name == get_active_provider():
            await ctx.send(f"ℹ️ Провайдер **{name}** уже активен.")
            return

        set_active_provider(name)
        await ctx.send(f"✅ Провайдер переключён на **{name}**")

    @commands.command(name="toxic")
    async def roast_command(self, ctx: commands.Context, persona: str | None = None) -> None:
        """Прожарка последних сообщений чата.
        
        Использование:
        !toxic - обычная прожарка
        !toxic babka - режим бабки
        !toxic list - список доступных режимов
        """
        try:
            if persona == "list":
                 keys = ", ".join(f"`{k}`" for k in ROAST_PERSONAS.keys())
                 await ctx.send(f"🎭 **Доступные режимы:** {keys}")
                 return

            messages = []
            async for msg in ctx.channel.history(limit=50):
                if len(messages) >= 20:
                    break

                if msg.author == self.bot.user:
                    continue

                content = msg.content
                if content.startswith(ctx.prefix) or content.startswith("!"):
                    continue

                if not content:
                    if msg.attachments:
                        content = "[Пользователь скинул картинку/файл]"
                    elif msg.stickers:
                        content = "[Пользователь отправил стикер]"
                    else:
                        continue  # Пропускаем пустые системные сообщения

                if content.startswith("http"):
                    content = "[Пользователь отправил ссылку]"

                messages.append(f"[{msg.author.name}]: {content}")

            if not messages:
                await ctx.send("Тут слишком тихо, некого прожаривать. 🦗")
                return

            messages.reverse()
            history_text = "\n".join(messages)
            # print(f"DEBUG: Messages for roast:\n{history_text}")
            
            user_info_text = "\n".join([f"- {k}: {v}" for k, v in USER_DESCRIPTIONS.items()])
            
            system_content = ROAST_PROMPT.format(user_info=user_info_text)

            if persona and persona in ROAST_PERSONAS:
                selected_persona = ROAST_PERSONAS[persona]
                system_content += f"\n\nВАЖНОЕ ДОПОЛНЕНИЕ К РОЛИ:\n{selected_persona}"
            elif persona:
                 keys = ", ".join(f"`{k}`" for k in ROAST_PERSONAS.keys())
                 await ctx.send(f"❌ Нет такого режима `{persona}`. Доступные: {keys}")
                 return

            msgs = [
                ChatCompletionSystemMessageParam(role="system", content=system_content),
                ChatCompletionUserMessageParam(
                    role="user", content=f"Вот последние сообщения чата:\n{history_text}"
                ),
            ]

            async with ctx.typing():
                completion = await get_client().chat.completions.create(
                    model=get_model(),
                    messages=msgs,
                    temperature=0.9,
                    max_tokens=600,
                )
                response = completion.choices[0].message.content or ""
                cleaned_response_text = await clean_text(response)
                emoji_response_text = await replace_emojis(cleaned_response_text)
                await ctx.send(emoji_response_text)

        except Exception as e:
            await ctx.send(f"❌ Не удалось прожарить: {e}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Обработка ошибок команд."""
        original_error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            server_id = ctx.guild.id if ctx.guild else None

            # Проверяем, включены ли функции в настройках
            weather_task = (
                handlers.check_weather_intent(ctx.message.content)
                if self.bot.weather_enabled
                else asyncio.sleep(0)
            )
            search_task = (
                handlers.check_search_intent(ctx.message.content)
                if self.bot.search_enabled
                else asyncio.sleep(0)
            )

            tool_weather, tool_search = await asyncio.gather(weather_task, search_task)

            response = await handlers.ai_generate(
                ctx.message.content,
                server_id,
                ctx.author,
                tool_weather,
                tool_search,
                limit=self.bot.context_limit,
            )
            await ctx.send(f"{ctx.author.mention} {response}")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ У вас недостаточно прав для выполнения этой команды.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Неправильное использование команды. "
                f"Используйте: `!{ctx.command.name} {ctx.command.signature}`"
            )
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ Эта команда недоступна в личных сообщениях.")
        elif isinstance(original_error, (ConnectionError, TimeoutError)):
            await ctx.send("❌ Проблема с сетью. Попробуйте позже.")
            from app.services.telegram_notifier import telegram_notifier

            await telegram_notifier.send_message(
                f"⚠️ <b>Сетевая ошибка</b>\n"
                f"Ошибка в команде `{ctx.command.name}`: {original_error}"
            )
        else:
            await ctx.send("❌ Произошла ошибка при выполнении команды.")
            print(f"Command error: {error}")


async def setup(bot: DisBot) -> None:
    """Загрузка Cog в бота."""
    await bot.add_cog(BotCommands(bot))
