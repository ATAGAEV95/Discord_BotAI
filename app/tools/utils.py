import re

import tiktoken

from app.tools.prompt import EMOJI_MAPPING


ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")


def contains_only_urls(text):
    """Проверяет, содержит ли текст только ссылки (и пробелы между ними)"""
    url_pattern = re.compile(r"https?://\S+|www\.\S+")
    text_without_urls = url_pattern.sub("", text)
    return not text_without_urls.strip()


def count_tokens(text):
    if not isinstance(text, str):
        text = str(text) if text else ""
    return len(ENCODING.encode(text))


async def clean_text(text):
    cleaned_text = re.sub(r"(\*\*|\*|__|###|##|#)", "", text)
    return cleaned_text


async def replace_emojis(text):
    """Заменяет текстовые представления эмодзи на реальные Discord-эмодзи"""
    for text_emoji, discord_emoji in EMOJI_MAPPING.items():
        text = text.replace(text_emoji, discord_emoji)
    return text


def get_rang_description(message_count: int) -> str:
    """Возвращает ранг в стиле Гачи в зависимости от количества сообщений."""
    if message_count == 0:
        return "Начинающий гачи-кун ♂️ (0 сообщений)"
    elif message_count < 10:
        return f"Ученик гачи-мастера ♂️ ({message_count} сообщений)"
    elif message_count < 50:
        return f"Опытный гачи-боец ♂️ ({message_count} сообщений)"
    elif message_count < 100:
        return f"Мастер гачи-движений ♂️ ({message_count} сообщений)"
    elif message_count < 200:
        return f"Легенда гачи-клуба ♂️ ({message_count} сообщений)"
    elif message_count < 500:
        return f"Бог гачи-мира ♂️ ({message_count} сообщений)"
    else:
        return f"Император вселенной гачи ♂️ ({message_count} сообщений)"