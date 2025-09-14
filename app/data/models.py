import os

from dotenv import load_dotenv
from sqlalchemy import BigInteger, Column, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA = "public"


def get_engine(schema: str) -> create_async_engine:
    """Создает и возвращает асинхронный движок SQLAlchemy с указанной схемой."""
    return create_async_engine(
        DATABASE_URL,
        connect_args={"server_settings": {"search_path": schema}},
        pool_pre_ping=True,
    )


if SCHEMA is None or SCHEMA == "":
    engine = get_engine("public")
else:
    engine = get_engine(SCHEMA)
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей, поддерживающий асинхронные атрибуты."""

    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(50), nullable=False)
    context = Column(JSONB)
    datetime_insert = Column(DateTime, default=func.now())


class ChannelMessage(Base):
    __tablename__ = "channel_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    author = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())


class Birthday(Base):
    __tablename__ = "birthday"
    user_id = Column(BigInteger, primary_key=True, nullable=False)
    display_name = Column(String(50), nullable=False)
    name = Column(String(50), nullable=False)
    birthday = Column(Date, nullable=False)
    datetime_insert = Column(DateTime, default=func.now())


class UserMessageStats(Base):
    __tablename__ = "user_message_stats"

    user_id = Column(BigInteger, primary_key=True, nullable=False)
    guild_id = Column(BigInteger, primary_key=True, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_guild_message_count", "guild_id", "message_count"),
        Index("idx_user_activity", "last_updated"),
    )


async def init_models() -> None:
    """Создает таблицы в базе данных, если они не существуют."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
