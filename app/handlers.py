import os
import re

import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.requests import save_user_context, get_user_context, delete_user_context

load_dotenv()

AI_TOKEN = os.getenv('AI_TOKEN')
AI_TOKEN1 = os.getenv('AI_TOKEN1')

SYSTEM_PROMPT = """
Ты — Discord бот, дерзкий, немного грубый и остроумный. Твои задачи:
1. Общаться с пользователями в Discord-чатах
2. Использовать неформальный стиль общения(использовать мат, но по разному)
3. Избегать сложных технических терминов, если пользователь не попросит
4. Отвечать кратко (2-3 предложения) для удобства чтения в чате
5. Информация по пользователям с user_id, но не упоминать об этом постоянно:
    - serious_vlad, он админ канала
    - rikka71, у него сильные скиллы в шутерах
    - atagaev, создатель бота

Текущая платформа: Discord
"""


client = AsyncOpenAI(
    # api_key=AI_TOKEN,
    api_key=AI_TOKEN1,
    # base_url="https://api.proxyapi.ru/openai/v1",
    base_url="https://api.aitunnel.ru/v1/",
)

user_history = {}
ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")


async def clean_text(text):
    cleaned_text = re.sub(r'(\*\*|\*|__|_|###|##|#)', '', text)
    return cleaned_text


async def clear_user_history(user_id):
    await delete_user_context(user_id)
    try:
        del user_history[user_id]
    except KeyError:
        print('Такого ключа нет')


def count_tokens(text):
    if not isinstance(text, str):
        text = str(text) if text else ""
    return len(ENCODING.encode(text))


def trim_messages(messages, max_tokens=3500):
    if not messages:
        return messages

    system_message = messages[0] if messages[0]["role"] == "system" else None
    other_messages = messages[1:] if system_message else messages

    total_tokens = sum(count_tokens(msg.get("content", "")) for msg in messages)

    while total_tokens > max_tokens and len(other_messages) > 1:
        removed_message = other_messages.pop(0)
        total_tokens -= count_tokens(removed_message.get("content", ""))

    return [system_message] + other_messages if system_message else other_messages


async def summarize_chunk(messages: list) -> str:
    """Создает суммаризацию для набора сообщений"""
    conversation = "\n".join(
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    )

    from openai.types.chat import (
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam
    )

    summary_prompt = [
        ChatCompletionSystemMessageParam(
            role="system",
            content="Ты компрессор диалогов. Создай КРАТКУЮ сводку (2-3 предложения) на русском, сохраняя:"
                    "\n1. Ключевые факты и решения"
                    "\n2. Имена и особенности пользователей"
        ),
        ChatCompletionUserMessageParam(
            role="user",
            content=f"Суммаризируй этот диалог:\n\n{conversation}"
        )
    ]

    try:
        completion = await client.chat.completions.create(
            # model="grok-4",
            # model = "gemini-2.5-flash-preview-05-20-thinking",
            model="gpt-4.1-mini",
            # model="gpt-4.1",
            messages=summary_prompt,
            max_tokens=300,
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Ошибка суммаризации: {e}")
        return "[Не удалось создать сводку]"


async def ai_generate(text: str, user_id: int, name: str):
    global user_history
    messages = user_history.get(user_id, [])

    if not messages:
        messages.append({"role": "system", "content": SYSTEM_PROMPT.strip()})
        context = await get_user_context(user_id)
        if isinstance(context, list):
            messages.extend(context)

    user_msg = {"role": "user", "content": f"[Пользователь: {name}] {text}"}
    messages.append(user_msg)

    dialog_messages = [msg for msg in messages if msg["role"] != "system"]

    if len(dialog_messages) >= 18:
        to_summarize = dialog_messages[:-10]
        to_keep = dialog_messages[-9:]

        summary_text = await summarize_chunk(to_summarize)

        new_history = [
            messages[0],
            {"role": "system", "content": f"КОНТЕКСТ: {summary_text}"}
        ]
        new_history.extend(to_keep)

        messages = new_history

    messages = trim_messages(messages)

    try:
        completion = await client.chat.completions.create(
            # model="grok-4",
            model = "gpt-4o",
            # model="gpt-4.1-mini",
            # model="gpt-4.1",
            messages=messages,
            max_tokens=4096 - sum(count_tokens(msg.get("content", "")) for msg in messages) - 100
        )

        response_text = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": response_text})
        cleaned_response_text = await clean_text(response_text)

        user_history[user_id] = messages
        print(user_history)
        try:
            await save_user_context(user_id, name, user_history[user_id])
        except Exception as e:
            print(f"Произошла ошибка при сохранении контекста в БД: {e}")
        return cleaned_response_text
    except Exception as e:
        print(f"Ошибка при вызове OpenAI API: {e}")
        return "Произошла ошибка. Пожалуйста, попробуйте позже."
