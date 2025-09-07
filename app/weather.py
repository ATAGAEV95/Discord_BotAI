import os
from langgraph.prebuilt import create_react_agent
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Ваши кастомные настройки API
AI_TOKEN1 = os.getenv("AI_TOKEN1")
base_url = "https://api.aitunnel.ru/v1/"

# Создаем экземпляр ChatOpenAI с кастомными настройками
llm = ChatOpenAI(
    model="gpt-4.1-mini",  # или "gpt-5-chat" в зависимости от доступности
    openai_api_key=AI_TOKEN1,
    base_url=base_url,
    temperature=0
)

# Инициализируем инструмент погоды
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
weather = OpenWeatherMapAPIWrapper(openweathermap_api_key=OPENWEATHERMAP_API_KEY)

# Создаем инструменты
tools = [weather]

# Создаем агента с кастомной моделью
agent = create_react_agent(llm, tools)