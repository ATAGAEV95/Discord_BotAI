from sqlalchemy import select, delete

from app.models import User, async_session


async def get_user_context(user_id: int):
    """Извлекает контекст пользователя из базы данных."""
    async with async_session() as session:
        query = select(User).where(User.user_id == user_id).order_by(User.id.desc()).limit(1)
        user = await session.execute(query)
        user = user.scalar()
        if user:
            return user.context
        else:
            return "Пользователь не найден."


async def save_user_context(user_id: int, name: str, context: list):
    """Сохраняет контекст пользователя в базе данных."""
    async with async_session() as session:
        try:
            new_user = User(user_id=user_id, name=str(name), context=context[1:])
            session.add(new_user)
            await session.commit()
        except Exception as e:
            raise Exception(f"База данных недоступна: {e}")

async def delete_user_context(user_id: int):
    """Удаляет контекст пользователя из базы данных."""
    async with async_session() as session:
        query = delete(User).where(User.user_id == user_id)
        await session.execute(query)
        await session.commit()
