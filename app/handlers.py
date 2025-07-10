import os
import re

import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

AI_TOKEN = os.getenv('AI_TOKEN')
AI_TOKEN1 = os.getenv('AI_TOKEN1')

SYSTEM_PROMPT = """
Ты — грубый Discord бот. Твои задачи:
1. Общаться с пользователями в Discord-чатах
2. Использовать неформальный стиль общения(использовать мат, но по разному)
3. Избегать сложных технических терминов, если пользователь не попросит
4. Отвечать кратко (1-2 предложения) для удобства чтения в чате
5. Если пишет пользователь с user_id - serious_vlad, то он админ канала
6. Если пишет пользователь с user_id - rikka71, то обращать внимание на его сильные скиллы в шутерах

Текущая платформа: Discord
"""


client = AsyncOpenAI(
    api_key=AI_TOKEN,
    # api_key=AI_TOKEN1,
    base_url="https://api.proxyapi.ru/openai/v1",
    # base_url="https://api.aitunnel.ru/v1/",
)

user_history = {}
ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")


async def clean_text(text):
    cleaned_text = re.sub(r'(\*\*|\*|__|_|`|###|##|#)', '', text)
    return cleaned_text


async def reset_history():
    user_history.clear()


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


async def ai_generate(text: str, user_id: int):
    global user_history
    messages = user_history.get(user_id, [])

    if not messages:
        messages.append({"role": "system", "content": SYSTEM_PROMPT.strip()})

    messages.append({
        "role": "user",
        "content": f"[Пользователь: {user_id}] {text}"
    })

    messages = trim_messages(messages)
    non_system_messages = [msg for msg in messages if msg["role"] != "system"]
    if len(non_system_messages) > 10:
        messages = [messages[0]] + non_system_messages[-9:]

    try:
        completion = await client.chat.completions.create(
            # model="grok-3-mini-beta",
            # model = "gemini-2.5-flash-preview-05-20-thinking",
            # model="gpt-4.1-mini",
            model="gpt-4.1",
            messages=messages,
            max_tokens=4096 - sum(count_tokens(msg.get("content", "")) for msg in messages) - 100
        )

        response_text = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": response_text})
        cleaned_response_text = await clean_text(response_text)

        user_history[user_id] = messages
        # print(count_tokens(messages))
        # print(messages)
        # print(len(messages))
        #return cleaned_response_text + '\n' + '_______________' + '\n' + f'Сообщений: {len(messages)}' + '\n' + \
        #    f'Длина: {len(str(messages))}' + '\n' + f'Ответ: {len(cleaned_response_text)}'
        # total_token_count = sum(count_tokens(msg.get("content", "")) for msg in messages)

        return cleaned_response_text

        # return (cleaned_response_text + '\n' +
        #         '_______________' + '\n' +
        #         f'Сообщений: {len(messages)}' + '\n' +
        #         f'Длина: {len(str(messages))}' + '\n' +
        #         f'Ответ: {len(cleaned_response_text)}' + '\n' +
        #         f'Использовано токенов: {total_token_count}')

    except Exception as e:
        print(f"Ошибка при вызове OpenAI API: {e}")
        return "Произошла ошибка. Пожалуйста, попробуйте позже."
