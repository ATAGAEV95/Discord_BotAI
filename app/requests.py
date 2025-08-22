import asyncio
from sqlalchemy import select, delete
from app.models import User, async_session, ChannelMessage, Birthday
import re
from datetime import datetime

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
        except asyncio.TimeoutError:
            raise Exception("Таймаут при получении контекста пользователя.")
        except Exception as e:
            raise Exception(f"Ошибка доступа к базе данных: {e}")


async def save_user_context(user_id: int, name: str, context: list):
    """Сохраняет контекст пользователя в базе данных."""
    async with async_session() as session:
        try:
            new_user = User(user_id=user_id, name=str(name), context=context[1:])
            session.add(new_user)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except asyncio.TimeoutError:
            raise Exception("Таймаут при сохранении контекста пользователя.")
        except Exception as e:
            raise Exception(f"Ошибка сохранения в БД: {e}")


async def delete_user_context(user_id: int):
    """Удаляет контекст пользователя из базы данных."""
    async with async_session() as session:
        try:
            query = delete(User).where(User.user_id == user_id)
            await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except asyncio.TimeoutError:
            raise Exception("Таймаут при удалении контекста пользователя.")
        except Exception as e:
            raise Exception(f"Ошибка удаления из БД: {e}")


async def save_channel_message(channel_id: int, message_id: int, author: str, content: str):
    """Сохраняет сообщение канала в базы данных."""
    async with async_session() as session:
        try:
            new_message = ChannelMessage(
                channel_id=channel_id,
                message_id=message_id,
                author=author,
                content=content
            )
            session.add(new_message)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except asyncio.TimeoutError:
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
        except asyncio.TimeoutError:
            raise Exception("Таймаут при получении сообщений канала.")
        except Exception as e:
            raise Exception(f"Ошибка доступа к базе данных: {e}")


async def delete_channel_messages(channel_id: int):
    """Удаляет сообщения канала из базы данных."""
    async with async_session() as session:
        try:
            query = delete(ChannelMessage).where(ChannelMessage.channel_id == channel_id)
            await asyncio.wait_for(session.execute(query), timeout=DB_TIMEOUT)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except asyncio.TimeoutError:
            raise Exception("Таймаут при удалении сообщений канала.")
        except Exception as e:
            raise Exception(f"Ошибка удаления сообщений канала: {e}")


async def save_birthday(content, display_name, user_id):
    """
    Сохраняет дату рождения пользователя.
    Формат команды: !birthday YYYY-MM-DD
    """
    try:
        args = content[len("!birthday"):].strip()
        # Проверяем корректность формата даты (YYYY-MM-DD)
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", args):
            raise ValueError("Некорректный формат даты. Используйте DD.MM.YYYY.")
        birthday = datetime.strptime(args, "%d.%m.%Y")
    except Exception:
        raise ValueError("Некорректный формат даты. Используйте DD.MM.YYYY.")

    async with async_session() as session:
        try:
            # Пробуем обновить дату, если она уже есть
            query = select(Birthday).where(Birthday.user_id == user_id)
            result = await session.execute(query)
            birthday_entry = result.scalar()
            if birthday_entry:
                birthday_entry.birthday = birthday
                birthday_entry.name = display_name  # обновим на всякий случай
            else:
                birthday_entry = Birthday(
                    user_id=user_id,
                    name=display_name,
                    birthday=birthday
                )
                session.add(birthday_entry)
            await asyncio.wait_for(session.commit(), timeout=DB_TIMEOUT)
        except asyncio.TimeoutError:
            raise Exception("Таймаут при сохранении даты рождения.")
        except Exception as e:
            raise Exception(f"Ошибка при сохранении даты рождения: {e}")
