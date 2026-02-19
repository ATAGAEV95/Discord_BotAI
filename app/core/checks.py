"""Проверки прав доступа для команд бота."""

from collections.abc import Callable

from discord.ext import commands

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
