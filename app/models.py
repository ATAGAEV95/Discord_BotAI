from sqlalchemy import Column, DateTime, BigInteger, String, Text, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
SCHEMA = 'public'

def get_engine(schema: str) -> create_async_engine:
    """Создает и возвращает асинхронный движок SQLAlchemy с указанной схемой."""
    return create_async_engine(
        DATABASE_URL,
        connect_args={"server_settings": {"search_path": schema}})


if SCHEMA is None or SCHEMA == '':
    engine = get_engine('public')
else:
    engine = get_engine(SCHEMA)
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей, поддерживающий асинхронные атрибуты."""

    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(50), nullable=False)
    context = Column(JSONB)
    datetime_insert = Column(DateTime, default=func.now())


class ChannelMessage(Base):
    __tablename__ = 'channel_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    author = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())


class Birthday(Base):
    __tablename__ = 'birthday'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(50), nullable=False)
    birthday = Column(DateTime, nullable=True)
    datetime_insert = Column(DateTime, default=func.now())


async def init_models() -> None:
    """Создает таблицы в базе данных, если они не существуют."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
