import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from app.services.llama_integration import LlamaIndexManager
from app.tools.prompt import SYSTEM_NEWYEAR_PROMPT, USER_DESCRIPTIONS
from app.tools.utils import clean_text, users_context, replace_emojis

load_dotenv()
llama_manager = LlamaIndexManager()

AI_TOKEN_PROXYAPI = os.getenv("AI_TOKEN")
AI_TOKEN_AITUNNEL = os.getenv("AI_TOKEN1")
AI_TOKEN_POLZA = os.getenv("AI_TOKEN_POLZA")
proxyapi = "https://api.proxyapi.ru/openai/v1"
aitunnel = "https://api.aitunnel.ru/v1/"
polza = "https://api.polza.ai/api/v1"

client = AsyncOpenAI(
    api_key=AI_TOKEN_POLZA,
    base_url=polza,
)


async def ai_generate_new_year_congrats(names):
    """Генерирует креативное поздравление с Новым годом для пользователей."""
    relevant_contexts = users_context(names, USER_DESCRIPTIONS)
    print(relevant_contexts)
    print(names)
    current_date = datetime.now()
    date_minus_month = current_date - timedelta(days=30)
    date_plus_month = current_date + timedelta(days=30)
    old_year = date_minus_month.year
    new_year = date_plus_month.year
    print(old_year, new_year)
    prompt = [
        ChatCompletionSystemMessageParam(role="system", content=SYSTEM_NEWYEAR_PROMPT.strip()),
        ChatCompletionUserMessageParam(
            role="user", content=f"{relevant_contexts}. Новый год {new_year}. Старый год {old_year}."
        ),
    ]

    try:
        completion = await client.chat.completions.create(
            model="openai/gpt-5-chat",
            messages=prompt,
            temperature=1,  # Оптимальный баланс креативности/когерентности
            top_p=0.8,  # Шире выборка слов
            frequency_penalty=0.1,  # Поощряет новые формулировки
            presence_penalty=0.2,  # Поощряет новые темы
            max_tokens=2000,
        )
        text = completion.choices[0].message.content.strip()
        cleaned_response_text = await clean_text(text)
        emoji_response_text = await replace_emojis(cleaned_response_text)
        return emoji_response_text
    except Exception as e:
        print(f"[Ошибка генерации поздравления]: {e}")
        return "Поздравляем всех пользователей с Новым Годом!!!! 🎉"
