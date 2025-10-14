import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from app.services.llama_integration import LlamaIndexManager
from app.tools.prompt import SYSTEM_BIRTHDAY_PROMPT, USER_DESCRIPTIONS
from app.tools.utils import (
    clean_text,
    count_tokens,
    enrich_users_context,
    replace_emojis,
    user_prompt,
)

load_dotenv()
llama_manager = LlamaIndexManager()

AI_TOKEN = os.getenv("AI_TOKEN")
AI_TOKEN1 = os.getenv("AI_TOKEN1")


client = AsyncOpenAI(
    api_key=AI_TOKEN1,
    base_url="https://api.aitunnel.ru/v1/",
    # api_key=AI_TOKEN,
    # base_url="https://api.proxyapi.ru/openai/v1",
    # api_key='google/gemma-3n-e4b',
    # base_url='http://localhost:1234/v1/'
)


async def clear_server_history(server_id):
    """Очищает историю сообщений сервера в индексе LlamaIndex,
    оставляя только документы типа 'server_users'."""
    try:
        collection = llama_manager.get_server_collection(server_id)
        results = collection.get()
        if results and "ids" in results and results["ids"]:
            ids_to_delete = []
            metadatas = results.get("metadatas", [])

            for i, metadata in enumerate(metadatas):
                if metadata.get("document_type") != "server_users":
                    ids_to_delete.append(results["ids"][i])

            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                return f"Удалено {len(ids_to_delete)} документов из индекса сервера {server_id}"
            else:
                return f"В индексе сервера {server_id} нет документов для удаления (кроме списка пользователей)"
        else:
            return f"Индекс сервера {server_id} уже пуст"
    except Exception as e:
        print(f"Ошибка очистки индекса LlamaIndex: {e}")
        return f"Произошла ошибка при очистке индекса: {e}"


async def ai_generate(text: str, server_id: int, name: str) -> str:
    """Генерирует ответ от AI на основе контекста сервера и текущего сообщения пользователя."""
    messages = [{"role": "system", "content": user_prompt(f"{name}")}]
    relevant_contexts = await llama_manager.query_relevant_context(server_id, text, limit=16)
    relevant_contexts = enrich_users_context(relevant_contexts, USER_DESCRIPTIONS)

    if relevant_contexts:
        context_message = {
            "role": "system",
            "content": "Релевантный контекст из истории сервера:\n" + "\n".join(relevant_contexts),
        }
        messages.append(context_message)

    user_msg = {"role": "user", "content": f"[Пользователь: {name}] {text}"}
    messages.append(user_msg)

    try:
        openai_messages = []
        for msg in messages:
            if msg["role"] == "system":
                openai_messages.append(
                    ChatCompletionSystemMessageParam(role="system", content=msg["content"])
                )
            elif msg["role"] == "user":
                openai_messages.append(
                    ChatCompletionUserMessageParam(role="user", content=msg["content"])
                )

        completion = await client.chat.completions.create(
            model="gpt-5-chat",
            messages=openai_messages,
            temperature=0.8,
            top_p=0.8,
            frequency_penalty=0.1,
            presence_penalty=0.2,
            max_tokens=3500,
        )

        response_text = completion.choices[0].message.content
        cleaned_response_text = await clean_text(response_text)
        emoji_response_text = await replace_emojis(cleaned_response_text)

        messages_to_index = [
            {"role": "user", "content": f"[Пользователь: {name}] {text}"},
            {"role": "assistant", "content": cleaned_response_text},
        ]
        await llama_manager.index_messages(server_id, messages_to_index)
        print(f"Релевантный {relevant_contexts}")
        print(count_tokens(relevant_contexts))
        print(f"Сообщения {messages}")
        print(count_tokens(messages))
        return emoji_response_text
    except Exception as e:
        print(f"Ошибка при вызове OpenAI API: {e}")
        return "Произошла ошибка. Пожалуйста, попробуйте позже."


async def ai_generate_birthday_congrats(display_name, name):
    """Генерирует креативное поздравление с днём рождения для пользователя."""
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
            temperature=0.8,  # Оптимальный баланс креативности/когерентности
            top_p=0.8,  # Шире выборка слов
            frequency_penalty=0.1,  # Поощряет новые формулировки
            presence_penalty=0.2,  # Поощряет новые темы
            max_tokens=400,
        )
        text = completion.choices[0].message.content.strip()
        text = await clean_text(text)
        return text
    except Exception as e:
        print(f"[Ошибка генерации поздравления]: {e}")
        return f"Поздравляем {display_name} с днём рождения! 🎉"
