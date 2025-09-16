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

# rang01 = "Человек <:Harold:1101900626268532860>"
# rang02 = "Начинающий бич <:Gay:1101900779033469028>"
# rang03 = "Радужный бич <:ScreamingFinka:444039191865851915>"
# rang04 = "Бич <:Gachi1:469464559959277578>"
# rang05 = "Босс бичей <:Illuminati:469465507179790336>"
# rang06 = "Бич-император <:Gachi2:469464898620096512>"
rang01 = "Человек"
rang02 = "Начинающий бич"
rang03 = "Радужный бич"
rang04 = "Бич"
rang05 = "Босс бичей"
rang06 = "Бич-император"
all_ranges = f"{rang01}\n{rang02}\n{rang03}\n{rang04}\n{rang05}\n{rang06}"


def get_rang_description(message_count: int) -> str:
    """Возвращает ранг в стиле Гачи без количества сообщений."""
    if message_count == 0:
        return rang01
    elif message_count < 50:
        return rang02
    elif message_count < 100:
        return rang03
    elif message_count < 200:
        return rang04
    elif message_count < 500:
        return rang05
    else:
        return rang06


def darken_color(rgb, factor=0.75):
    """Уменьшает яркость цвета RGB — делает его темнее.
    factor < 1 = темнее, factor > 1 = светлее."""
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)
