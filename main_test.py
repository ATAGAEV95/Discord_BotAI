import asyncio
import os
import sys

print("Начинаем проверку зависимостей...")
try:
    import tiktoken
    import openai
    from dotenv import load_dotenv
    import discord
    import sqlalchemy
    import pytz
    import apscheduler
    import asyncpg
    import chromadb
    import llama_index.core
    import requests
    import aiohttp
    import googleapiclient
    import PIL
    import httpx
    import mcp
    import tavily
    
    print("Все зависимости успешно загружены.")
except ImportError as e:
    print(f"Импорт не удалось: {e}")
    sys.exit(1)

load_dotenv()
DC_TOKEN_TEST = os.getenv("DC_TOKEN_TEST")

if not DC_TOKEN_TEST:
    print("DC_TOKEN_TEST не найден в переменных окружения. Пропускаем тест подключения к Discord.")
    print("Предупреждение: DC_TOKEN_TEST отсутствует!")
    sys.exit(1)
else:
    print("Начинаем тест подключения к Discord...")
    class TestClient(discord.Client):
        async def on_ready(self):
            if self.user:
                print(f"Вход выполнен как {self.user} (ID: {self.user.id})")
            print("Тест подключения к Discord прошел успешно.")
            await self.close()

    intents = discord.Intents.default()
    client = TestClient(intents=intents)

    try:
        client.run(DC_TOKEN_TEST)
    except Exception as e:
        print(f"Подключение к Discord не удалось: {e}")
        sys.exit(1)

print("Тест скрипта завершен.")
