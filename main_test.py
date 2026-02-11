import os
import sys

# Dependency check
print("Начинаем проверку зависимостей...")
try:
    import aiohttp
    import apscheduler
    import asyncpg
    import chromadb
    import discord
    import googleapiclient
    import httpx
    import llama_index.core

    # import mcp # mcp might not be directly importable as 'mcp', checking usage in valid files might be better but for now let's try standard
    import mcp
    import openai
    import PIL
    import pytz
    import requests
    import sqlalchemy
    import tavily
    import tiktoken
    from dotenv import load_dotenv

    print("Все зависимости успешно загружены.")
except ImportError as e:
    print(f"Импорт не удалось: {e}")
    sys.exit(1)

# Discord connection test
load_dotenv()
DC_TOKEN_TEST = os.getenv("DC_TOKEN_TEST")

if not DC_TOKEN_TEST:
    print("DC_TOKEN_TEST не найден в переменных окружения. Пропускаем тест подключения к Discord.")
    # If we want to fail when token is missing in CI, we should exit with error.
    # But for local run it might not be set. The prompt implies it's for CI usage.
    # "использует DC_TOKEN_TEST: ${{ secrets.DC_TOKEN_TEST }} для подклбчения к дискорду"
    # So it should probably be there during the test command in CI.
    print("Предупреждение: DC_TOKEN_TEST отсутствует!")
    # We will not exit 1 here to allow local runs without token if desired,
    # but in CI it should be present.
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
