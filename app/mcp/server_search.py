import logging
import os
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import AsyncTavilyClient

# Загружаем переменные окружения из файла .env
load_dotenv()

# Настраиваем логирование (важно для STDIO серверов - не использовать print!)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Создаем экземпляр MCP сервера с именем "search"
mcp = FastMCP("search")

# Загружаем SEARCH_API из переменных окружения
logger.info("Загружаем SEARCH_API из переменных окружения")
SEARCH_API = os.getenv("SEARCH_API")

if not SEARCH_API:
    logger.error("SEARCH_API не найден в переменных окружения")
    SEARCH_API = "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"
else:
    logger.info("SEARCH_API найден в переменных окружения (длина: %d)", len(SEARCH_API))

client = AsyncTavilyClient(SEARCH_API)


async def make_search_request(endpoint: str) -> dict[str, Any] | None:
    """Вспомогательная функция для выполнения поискового запроса к Tavily API.

    Args:
        endpoint: Текстовый запрос

    Returns:
        JSON ответ от API или None в случае ошибки

    """
    # Проверяем наличие API ключа
    if not SEARCH_API:
        logger.error("SEARCH_API не найден в переменных окружения")
        return None

    try:
        response = await client.search(
            query=endpoint,
            include_answer="advanced",
            include_raw_content="text",
            country="russia",
            include_favicon=False,
        )
        return response
    except Exception as e:
        logger.error(f"Ошибка при запросе к API: {str(e)}")
        return None


@mcp.tool()
async def get_current_search(text: str) -> str:
    """Получить описание поискового запроса.

    Args:
        text: Поисковой запрос

    Returns:
        Строка с описанием поискового запроса

    """
    logger.info(f"Поиск: {text}")

    # Выполняем запрос к API
    data = await make_search_request(text)

    # Обработка ошибок
    if not data:
        return f"❌ Поиск для '{text}' не удался."

    # Извлекаем данные из ответа
    try:
        # Основная информация
        result = data["answer"]

        logger.info(f"Успешно выполнен поиск по {text}")
        return result

    except KeyError as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        return f"❌ Ошибка при обработке данных о поиске: {str(e)}"


# Запуск сервера
if __name__ == "__main__":
    logger.info("Run server MCP search...")
    mcp.run(transport="stdio")
