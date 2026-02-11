import asyncio
import re
from datetime import datetime

from sqlalchemy import and_, delete, func, select, update

from app.data.models import Birthday, ChannelMessage, User, UserMessageStats, async_session
from app.tools.utils import get_rank_description

DB_TIMEOUT = 10


async def get_user_context(user_id: int):
    """Извлекает контекст пользователя из базы данных."""
    async with async_session() as session:
        try:
            query = select(User).where(User.user_id == user_id).order_by(User.id.desc()).limit(1)
            result = await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            user = result.scalar()
            if user:
                return user.context
            else:
                return "Пользователь не найден."
        except TimeoutError:
            raise Exception("Таймаут при получении контекста пользователя.")
        except Exception as e:
            raise Exception(f"Ошибка доступа к базе данных: {e}")


async def save_user_context(user_id: int, name: str, context: list) -> None:
    """Сохраняет контекст пользователя в базе данных."""
    async with async_session() as session:
        try:
            new_user = User(user_id=user_id, name=str(name), context=context[1:])
            session.add(new_user)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except TimeoutError:
            raise Exception("Таймаут при сохранении контекста пользователя.")
        except Exception as e:
            raise Exception(f"Ошибка сохранения в БД: {e}")


async def delete_user_context(user_id: int) -> None:
    """Удаляет контекст пользователя из базы данных."""
    async with async_session() as session:
        try:
            query = delete(User).where(User.user_id == user_id)
            await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except TimeoutError:
            raise Exception("Таймаут при удалении контекста пользователя.")
        except Exception as e:
            raise Exception(f"Ошибка удаления из БД: {e}")


async def save_channel_message(channel_id: int, message_id: int, author: str, content: str) -> None:
    """Сохраняет сообщение канала в базы данных."""
    async with async_session() as session:
        try:
            new_message = ChannelMessage(
                channel_id=channel_id, message_id=message_id, author=author, content=content
            )
            session.add(new_message)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except TimeoutError:
            raise Exception("Таймаут при сохранении сообщения канала.")
        except Exception as e:
            raise Exception(f"Ошибка сохранения сообщения канала в БД: {e}")


async def get_channel_messages(channel_id: int):
    """Извлекает сообщения канала из базы данных."""
    async with async_session() as session:
        try:
            query = select(ChannelMessage).where(ChannelMessage.channel_id == channel_id)
            result = await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            return result.scalars().all()
        except TimeoutError:
            raise Exception("Таймаут при получении сообщений канала.")
        except Exception as e:
            raise Exception(f"Ошибка доступа к базе данных: {e}")


async def delete_channel_messages(channel_id: int) -> None:
    """Удаляет сообщения канала из базы данных."""
    async with async_session() as session:
        try:
            query = delete(ChannelMessage).where(ChannelMessage.channel_id == channel_id)
            await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except TimeoutError:
            raise Exception("Таймаут при удалении сообщений канала.")
        except Exception as e:
            raise Exception(f"Ошибка удаления сообщений канала: {e}")


async def save_birthday(content, display_name, name, user_id) -> None:
    """Сохраняет дату рождения пользователя."""
    try:
        args = content[len("!birthday") :].strip()
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", args):
            raise ValueError("Некорректный формат даты. Используйте DD.MM.YYYY.")
        birthday = datetime.strptime(args, "%d.%m.%Y")
    except Exception:
        raise ValueError("Некорректный формат даты. Используйте DD.MM.YYYY.")

    async with async_session() as session:
        try:
            query = select(Birthday).where(Birthday.user_id == user_id)
            result = await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            birthday_entry = result.scalar()
            if birthday_entry:
                birthday_entry.birthday = birthday
                birthday_entry.display_name = display_name
                birthday_entry.name = name
            else:
                birthday_entry = Birthday(
                    user_id=user_id, display_name=display_name, name=name, birthday=birthday
                )
                session.add(birthday_entry)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except TimeoutError:
            raise Exception("Таймаут при сохранении даты рождения.")
        except Exception as e:
            raise Exception(f"Ошибка при сохранении даты рождения: {e}")


async def update_message_count(user_id: int, name: str, guild_id: int):
    """Обновляет счетчик сообщений пользователя и возвращает информацию о повышении ранга."""
    try:
        async with async_session() as session:
            query = select(UserMessageStats).where(
                UserMessageStats.user_id == user_id, UserMessageStats.guild_id == guild_id
            )
            result = await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            user_stats = result.scalar_one_or_none()

            if user_stats:
                old_count = user_stats.message_count
                old_rank = get_rank_description(old_count)
                new_count = old_count + 1
                new_rank = get_rank_description(new_count)

                stmt = (
                    update(UserMessageStats)
                    .where(
                        UserMessageStats.user_id == user_id, UserMessageStats.guild_id == guild_id
                    )
                    .values(message_count=new_count, last_updated=func.now())
                )
                await asyncio.wait_for(session.execute(stmt), timeout=DB_TIMEOUT)

                rank_up = new_rank["rank_level"] > old_rank["rank_level"]
            else:
                old_rank = get_rank_description(0)
                new_count = 1
                new_rank = get_rank_description(new_count)

                new_stat = UserMessageStats(
                    user_id=user_id, name=name, guild_id=guild_id, message_count=new_count
                )
                session.add(new_stat)

                rank_up = new_rank["rank_level"] > old_rank["rank_level"]

            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)

            return {
                "rank_up": rank_up,
                "old_rank": old_rank["rank_level"],
                "new_rank": new_rank["rank_level"],
                "message_count": new_count,
            }

    except TimeoutError:
        raise Exception("Таймаут при сохранении статистики сообщений.")
    except Exception as e:
        raise Exception(f"Ошибка при сохранении статистики сообщений: {e}")


async def get_rank(user_id: int, guild_id: int) -> int:
    """Получает количество сообщений пользователя на сервере."""
    async with async_session() as session:
        try:
            query = select(UserMessageStats.message_count).where(
                UserMessageStats.user_id == user_id, UserMessageStats.guild_id == guild_id
            )
            result = await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            stats = result.scalar_one_or_none()

            count = stats if stats is not None else 0
            return int(count)
        except TimeoutError:
            raise Exception("Таймаут при получении статистики сообщений.")
        except Exception as e:
            raise Exception(f"Ошибка при получении статистики сообщений: {e}")


async def get_user_rank(user_id: int, guild_id: int) -> int:
    """Получает ранг пользователя в указанном сервере на основе количества сообщений."""
    async with async_session() as session:
        try:
            subquery = (
                select(
                    UserMessageStats.user_id,
                    func.rank()
                    .over(
                        partition_by=UserMessageStats.guild_id,
                        order_by=UserMessageStats.message_count.desc(),
                    )
                    .label("user_rank"),
                )
                .where(UserMessageStats.guild_id == guild_id)
                .subquery()
            )

            query = select(subquery.c.user_rank).where(and_(subquery.c.user_id == user_id))

            result = await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            user_rank = result.scalar_one_or_none()

            return user_rank if user_rank is not None else 0

        except TimeoutError:
            raise Exception("Таймаут при получении ранга пользователя.")
        except Exception as e:
            raise Exception(f"Ошибка при получении ранга пользователя: {e}")
