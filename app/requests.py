import asyncio
from sqlalchemy import select, delete
from app.models import User, async_session

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
