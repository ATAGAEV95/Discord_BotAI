import re

import tiktoken
import discord

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


rang01 = "Человек"
rang02 = "Начинающий бич"
rang03 = "Радужный бич"
rang04 = "Бич"
rang05 = "Босс бичей"
rang06 = "Бич-император"
all_ranges = f"{rang01}\n{rang02}\n{rang03}\n{rang04}\n{rang05}\n{rang06}"


def darken_color(rgb, factor=0.75):
    """Уменьшает яркость цвета RGB — делает его темнее.
    factor < 1 = темнее, factor > 1 = светлее.
    """
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def get_rank_description(message_count):
    rank_designs = [
        {  # 0 сообщений
            "color": discord.Color.light_grey(),
            "next_threshold": 50,
            "rank_level": 0,
            "text_color": (130, 130, 130),
            "bg_filename": "rang0.jpg",
            "description": rang01
        },
        {  # 1-49
            "color": discord.Color.green(),
            "next_threshold": 50,
            "rank_level": 1,
            "text_color": (44, 255, 109),
            "bg_filename": "rang1.png",
            "description": rang02
        },
        {  # 50-99
            "color": discord.Color.blue(),
            "next_threshold": 100,
            "rank_level": 2,
            "text_color": (76, 142, 255),
            "bg_filename": "rang2.png",
            "description": rang03
        },
        {  # 100-199
            "color": discord.Color.gold(),
            "next_threshold": 200,
            "rank_level": 3,
            "text_color": (255, 215, 0),
            "bg_filename": "rang3.jpg",
            "description": rang04
        },
        {  # 200-499
            "color": discord.Color.purple(),
            "next_threshold": 500,
            "rank_level": 4,
            "text_color": (197, 94, 255),
            "bg_filename": "rang4.jpg",
            "description": rang05
        },
        {  # 500+
            "color": discord.Color.red(),
            "next_threshold": 500,
            "rank_level": 5,
            "text_color": (255, 73, 73),
            "bg_filename": "rang5.jpg",
            "description": rang06
        },
    ]

    if message_count == 0:
        rank = rank_designs[0]
    elif message_count < 50:
        rank = rank_designs[1]
    elif message_count < 100:
        rank = rank_designs[2]
    elif message_count < 200:
        rank = rank_designs[3]
    elif message_count < 500:
        rank = rank_designs[4]
    else:
        rank = rank_designs[5]
    return rank
