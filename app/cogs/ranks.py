import discord
from discord.ext import commands

import app.core.embeds as em
from app.data.request import update_message_count
from app.tools.utils import get_rank_description


class Ranks(commands.Cog):
    """Ког для системы рангов."""

    def __init__(self, bot: commands.Bot):
        """Инициализация кога."""
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Обработка сообщений для начисления опыта."""
        if message.author.bot:
            return

        # Игнорируем команды
        if message.content.startswith(self.bot.command_prefix):
            return

        server_id = message.guild.id if message.guild else None

        try:
            rank_info = await update_message_count(message.author.id, message.author.name, server_id)

            if rank_info["rank_up"]:
                new_rank_description = get_rank_description(rank_info["message_count"])
                avatar_url = (
                    message.author.avatar.url
                    if message.author.avatar
                    else message.author.default_avatar.url
                )

                embed, file = await em.create_rang_embed(
                    message.author.display_name,
                    rank_info["message_count"],
                    new_rank_description["description"],
                    avatar_url,
                    server_id,
                    message.author.id,
                )

                await message.channel.send(
                    f"🎉 **{message.author.mention}** повысил свой ранг!", embed=embed, file=file
                )

        except Exception as e:
            print(f"Произошла ошибка при обновлении статистики: {e}")


async def setup(bot: commands.Bot) -> None:
    """Загрузка кога."""
    await bot.add_cog(Ranks(bot))
