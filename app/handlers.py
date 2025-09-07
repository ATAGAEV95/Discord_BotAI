import os
import re

import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from app.llama_integration import LlamaIndexManager

load_dotenv()
llama_manager = LlamaIndexManager()

AI_TOKEN = os.getenv("AI_TOKEN")
AI_TOKEN1 = os.getenv("AI_TOKEN1")

SYSTEM_PROMPT = """
Ты — Discord бот, дерзкий, немного грубый и остроумный. Твои задачи:
1. Общаться с пользователями в Discord-чатах
2. Использовать неформальный стиль общения(использовать мат, но по разному)
3. Избегать сложных технических терминов, если пользователь не попросит
4. Отвечать кратко (2-3 предложения) для удобства чтения в чате
5. Информация по пользователям с name(они должны совпадать по буквено, иначе это другой юзер), но не упоминать об этом постоянно:
    - serious_vlad, это Владислав, позывной Дарт Путин, он админ канала
    - rikka71, это Рикка, у него сильные скиллы в шутерах
    - atagaev, это Арби, создатель бота

Текущая платформа: Discord
"""


client = AsyncOpenAI(
    api_key=AI_TOKEN1,
    base_url="https://api.aitunnel.ru/v1/",
    # api_key=AI_TOKEN,
    # base_url="https://api.proxyapi.ru/openai/v1",
    # api_key='google/gemma-3n-e4b',
    # base_url='http://localhost:1234/v1/'
)

ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")


async def clean_text(text):
    cleaned_text = re.sub(r"(\*\*|\*|__|_|###|##|#)", "", text)
    return cleaned_text


async def clear_server_history(server_id):
    try:
        collection = llama_manager.get_server_collection(server_id)  # Изменяем на серверную коллекцию
        results = collection.get()
        if results and 'ids' in results and results['ids']:
            collection.delete(ids=results['ids'])
            return f"Удалено {len(results['ids'])} документов из индекса сервера {server_id}"
        else:
            return f"Индекс сервера {server_id} уже пуст"
    except Exception as e:
        print(f"Ошибка очистки индекса LlamaIndex: {e}")


def count_tokens(text):
    if not isinstance(text, str):
        text = str(text) if text else ""
    return len(ENCODING.encode(text))


async def ai_generate(text: str, server_id: int, name: str):
    messages = [{"role": "system", "content": SYSTEM_PROMPT.strip()}]

    relevant_contexts = await llama_manager.query_relevant_context(server_id, text, limit=8)

    if relevant_contexts:
        context_message = {
            "role": "system",
            "content": f"Релевантный контекст из истории сервера:\n" + "\n".join(relevant_contexts)
        }
        messages.append(context_message)

    user_msg = {"role": "user", "content": f"[Пользователь: {name}] {text}"}
    messages.append(user_msg)

    try:
        completion = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages,
            temperature=1.2,
            top_p=0.95,
            frequency_penalty=0.3,
            presence_penalty=0.4,
            max_tokens=3500,
        )

        response_text = completion.choices[0].message.content
        cleaned_response_text = await clean_text(response_text)

        messages_to_index = [
            {"role": "user", "content": f"[Пользователь: {name}] {text}"},
            {"role": "assistant", "content": response_text}
        ]
        await llama_manager.index_messages(server_id, messages_to_index)
        print(f"Релевантный {relevant_contexts}")
        print(count_tokens(relevant_contexts))
        print(f"Сообщения {messages}")
        print(count_tokens(messages))
        return cleaned_response_text
    except Exception as e:
        print(f"Ошибка при вызове OpenAI API: {e}")
        return "Произошла ошибка. Пожалуйста, попробуйте позже."


SYSTEM_BIRTHDAY_PROMPT = """
    Ты — веселый Discord-бот. 
    Придумай уникальное, короткое (2-3 предложения) поздравление с днём рождения для пользователя, 
    не повторяйся, используй неформальный стиль, уместный юмор и эмодзи.
    Информация по пользователям с name:
        - serious_vlad, это Владислав, позывной Дарт Путин, он админ канала
        - rikka71, это Рикка, у него сильные скиллы в шутерах
        - atagaev, это Арби, создатель бота
    """


async def ai_generate_birthday_congrats(display_name, name):
    prompt = [
        ChatCompletionSystemMessageParam(role="system", content=SYSTEM_BIRTHDAY_PROMPT.strip()),
        ChatCompletionUserMessageParam(
            role="user", content=f"Сгенерируй креативное поздравление с днем рождения для {name}."
        ),
    ]

    try:
        completion = await client.chat.completions.create(
            model="gpt-5-chat",
            messages=prompt,
            temperature=0.85,  # Оптимальный баланс креативности/когерентности
            top_p=0.95,  # Шире выборка слов
            frequency_penalty=0.3,  # Поощряет новые формулировки
            presence_penalty=0.4,  # Поощряет новые темы
            max_tokens=200,
        )
        text = completion.choices[0].message.content.strip()
        text = await clean_text(text)
        return text
    except Exception as e:
        print(f"[Ошибка генерации поздравления]: {e}")
        return f"Поздравляем {display_name} с днём рождения! 🎉"
