import os
import re

import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

AI_TOKEN = os.getenv('AI_TOKEN')


client = AsyncOpenAI(
    api_key=AI_TOKEN,
    base_url="https://api.proxyapi.ru/openai/v1",
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
    total_tokens = sum(count_tokens(msg.get("content", "")) for msg in messages)

    while total_tokens > max_tokens and len(messages) > 1:
        removed_message = messages.pop(0)
        total_tokens -= count_tokens(removed_message.get("content", ""))

    return messages


async def ai_generate(text: str, user_id: int):
    global user_history
    messages = user_history.get(user_id, [])

    messages.append({"role": "user", "content": text})

    messages = trim_messages(messages)
    if len(messages) >= 26:
        messages = messages[-24:]

    try:
        completion = await client.chat.completions.create(
            # model="gpt-4.1-nano",
            # model = "gpt-4o-mini",
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
        total_token_count = sum(count_tokens(msg.get("content", "")) for msg in messages)

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
