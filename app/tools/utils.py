import re

import discord
import tiktoken

from app.tools.prompt import EMOJI_MAPPING, RANK_NAMES, SYSTEM_PROMPT, USER_DESCRIPTIONS

ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")


def user_prompt(name: str) -> str:
    """Формирует системный промпт для пользователя.

    Если имя совпадает с ключами в P.USER_DESCRIPTIONS.
    """
    if str(name).strip() in USER_DESCRIPTIONS:
        user_info = (
            "Информация по пользователям с name (они должны совпадать побуквенно, "
            "иначе это другой юзер). Но не упоминать об этом постоянно:"
        )
        user_info += f"\n- {name}: {USER_DESCRIPTIONS[name]}"
        prompt = SYSTEM_PROMPT.format(user_info=user_info).strip()
        return prompt
    else:
        cleaned_prompt = re.sub(r"\n\s*5\..*", "", SYSTEM_PROMPT.strip())
        return cleaned_prompt


def enrich_users_context(contexts: list[str], user_descriptions: dict) -> list[str]:
    """Обогащает контекст информацией о пользователях из USER_DESCRIPTIONS."""
    new_contexts = []

    for context in contexts:
        if context.startswith("Список пользователей сервера:"):
            users_str = context.replace("Список пользователей сервера:", "").strip()
            users_list = [user.strip() for user in users_str.split(",")]

            enriched_users = []
            for user in users_list:
                if user in user_descriptions:
                    enriched_users.append(f"{user}: {user_descriptions[user]}")
                else:
                    enriched_users.append(user)

            new_context = "Список пользователей сервера: " + "; ".join(enriched_users)
            new_contexts.append(new_context)
        else:
            new_contexts.append(context)

    return new_contexts


def users_context(contexts: list[str], user_descriptions: dict) -> str:
    """Обогащает контекст информацией о пользователях из USER_DESCRIPTIONS."""
    users_list = [user.strip() for user in contexts]

    enriched_users = []
    for user in users_list:
        if user in user_descriptions:
            enriched_users.append(f"{user}: {user_descriptions[user]}")

    new_context = "Список пользователей сервера: " + "; ".join(enriched_users)
    return new_context


def contains_only_urls(text: str) -> bool:
    """Проверяет, содержит ли текст только ссылки (и пробелы между ними)."""
    url_pattern = re.compile(r"https?://\S+|www\.\S+")
    text_without_urls = url_pattern.sub("", text)
    return not text_without_urls.strip()


def darken_color(rgb: tuple, factor: float = 0.75) -> tuple:
    """Уменьшает яркость цвета RGB — делает его темнее.

    factor < 1 = темнее, factor > 1 = светлее.
    """
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def count_tokens(text: str | None) -> int:
    """Подсчитывает количество токенов в тексте с использованием кодировки GPT-4o-mini."""
    if not isinstance(text, str):
        text = str(text) if text else ""
    return len(ENCODING.encode(text))


async def clean_text(text: str) -> str:
    """Очищает текст от markdown-стилей: **, *, ###, ##, #."""
    cleaned_text = re.sub(r"(\*\*|\*|###|##|#)", "", text)
    return cleaned_text


async def replace_emojis(text: str) -> str:
    """Заменяет текстовые представления эмодзи на реальные Discord-эмодзи."""
    for text_emoji, discord_emoji in EMOJI_MAPPING.items():
        text = text.replace(text_emoji, discord_emoji)
    return text


def get_rank_description(message_count: int) -> dict:
    """Возвращает описание уровня (ранга) пользователя на основе количества сообщений."""
    rank_designs = [
        {  # 0 сообщений
            "color": discord.Color.light_grey(),
            "next_threshold": 50,
            "rank_level": 0,
            "text_color": (130, 130, 130),
            "bg_filename": "rang0.jpg",
            "description": RANK_NAMES[0],
        },
        {  # 1-49
            "color": discord.Color.green(),
            "next_threshold": 50,
            "rank_level": 1,
            "text_color": (44, 255, 109),
            "bg_filename": "rang1.png",
            "description": RANK_NAMES[1],
        },
        {  # 50-99
            "color": discord.Color.blue(),
            "next_threshold": 100,
            "rank_level": 2,
            "text_color": (76, 142, 255),
            "bg_filename": "rang2.png",
            "description": RANK_NAMES[2],
        },
        {  # 100-199
            "color": discord.Color.red(),
            "next_threshold": 200,
            "rank_level": 3,
            "text_color": (255, 73, 73),
            "bg_filename": "rang3.png",
            "description": RANK_NAMES[3],
        },
        {  # 200-499
            "color": discord.Color.purple(),
            "next_threshold": 500,
            "rank_level": 4,
            "text_color": (197, 94, 255),
            "bg_filename": "rang4.png",
            "description": RANK_NAMES[4],
        },
        {  # 500+
            "color": discord.Color.gold(),
            "next_threshold": 500,
            "rank_level": 5,
            "text_color": (255, 215, 0),
            "bg_filename": "rang5.png",
            "description": RANK_NAMES[5],
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


def convert_mcp_tools_to_openai(mcp_tools: list) -> list:
    """Конвертирует MCP инструменты в формат OpenAI."""
    openai_tools = []

    for tool in mcp_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "Инструмент без описания",
                "parameters": tool.inputSchema,
            },
        }
        openai_tools.append(openai_tool)

    return openai_tools
