import os
import re

import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from app.requests import delete_user_context, get_user_context, save_user_context
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
5. Информация по пользователям с user_id, но не упоминать об этом постоянно:
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

user_history = {}
ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")


async def clean_text(text):
    cleaned_text = re.sub(r"(\*\*|\*|__|_|###|##|#)", "", text)
    return cleaned_text


# async def clear_user_history(user_id):
#     try:
#         await delete_user_context(user_id)
#     except Exception as e:
#         print(f"[Ошибка] Удаление контекста: {e}")
#     try:
#         del user_history[user_id]
#     except KeyError:
#         print("Такого ключа нет")

async def clear_user_history(user_id):
    try:
        await delete_user_context(user_id)
    except Exception as e:
        print(f"[Ошибка] Удаление контекста: {e}")
    try:
        del user_history[user_id]
    except KeyError:
        print("Такого ключа нет")

    # Очистка индекса LlamaIndex
    try:
        # Получаем коллекцию пользователя
        collection = llama_manager.get_user_collection(user_id)

        # Получаем все ID документов в коллекции
        results = collection.get()
        if results and 'ids' in results and results['ids']:
            # Удаляем все документы по их ID
            collection.delete(ids=results['ids'])
            print(f"Удалено {len(results['ids'])} документов из индекса пользователя {user_id}")
        else:
            print(f"Индекс пользователя {user_id} уже пуст")

    except Exception as e:
        print(f"Ошибка очистки индекса LlamaIndex: {e}")


def count_tokens(text):
    if not isinstance(text, str):
        text = str(text) if text else ""
    return len(ENCODING.encode(text))


async def summarize_contexts(contexts: list) -> str:
    """Суммаризирует список контекстных сообщений в одну строку."""
    context_text = "\n".join(msg["content"] for msg in contexts)

    prompt = [
        ChatCompletionSystemMessageParam(
            role="system",
            content="""Ты компрессор контекстных сводок. Объедини несколько контекстных сводок 
                    в одну КРАТКУЮ сводку (2-3 предложения) на русском, сохраняя самую важную информацию. 
                    Игнорируй отметки 'КОНТЕКСТ:'""",
        ),
        ChatCompletionUserMessageParam(
            role="user", content=f"Суммаризируй эти контексты:\n\n{context_text}"
        ),
    ]

    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini", messages=prompt, max_tokens=300, temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Ошибка суммаризации контекстов: {e}")
        return "[Не удалось создать сводку контекстов]"


async def summarize_chunk(messages: list) -> str:
    """Создает суммаризацию для набора сообщений"""
    conversation = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)

    summary_prompt = [
        ChatCompletionSystemMessageParam(
            role="system",
            content="Ты компрессор диалогов. Создай КРАТКУЮ сводку (2-3 предложения) на русском, сохраняя:"
            "\n1. Основные темы общения"
            "\n2. Ключевые факты и решения"
            "\n3. Игнорируй приветствия, прощания и пустые реплики",
        ),
        ChatCompletionUserMessageParam(
            role="user", content=f"Суммаризируй этот диалог:\n\n{conversation}"
        ),
    ]

    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            # model="gpt-4.1-mini",
            messages=summary_prompt,
            max_tokens=300,
            temperature=0.1,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Ошибка суммаризации: {e}")
        return "[Не удалось создать сводку]"


async def ai_generate(text: str, user_id: int, name: str):
    # Получаем системный промпт
    messages = [{"role": "system", "content": SYSTEM_PROMPT.strip()}]

    # Поиск релевантного контекста с помощью LlamaIndex
    relevant_contexts = await llama_manager.query_relevant_context(user_id, text, limit=8)

    # Добавление релевантного контекста к сообщениям
    if relevant_contexts:
        context_message = {
            "role": "system",
            "content": f"Релевантный контекст из истории:\n" + "\n".join(relevant_contexts)
        }
        messages.append(context_message)

    # Добавляем текущее сообщение пользователя
    user_msg = {"role": "user", "content": f"[Пользователь: {name}] {text}"}
    messages.append(user_msg)

    try:
        completion = await client.chat.completions.create(
            model="gpt-5-chat",
            messages=messages,
            temperature=0.85,
            top_p=0.95,
            frequency_penalty=0.3,
            presence_penalty=0.4,
            max_tokens=3500,
        )

        response_text = completion.choices[0].message.content
        cleaned_response_text = await clean_text(response_text)

        # Индексация нового сообщения и ответа
        messages_to_index = [
            {"role": "user", "content": text},
            {"role": "assistant", "content": response_text}
        ]
        await llama_manager.index_messages(user_id, messages_to_index)
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
