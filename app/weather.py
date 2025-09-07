import os
from langgraph.prebuilt import create_react_agent
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from langchain_community.tools import OpenWeatherMapQueryRun
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

AI_TOKEN1 = os.getenv("AI_TOKEN1")

model = init_chat_model("gpt-4.1-mini",
                        model_provider="openai",
                        api_key=AI_TOKEN1,
                        base_url="https://api.aitunnel.ru/v1/")

OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

# Создаем инструмент правильно
weather_tool = OpenWeatherMapQueryRun(api_wrapper=OpenWeatherMapAPIWrapper(openweathermap_api_key=OPENWEATHERMAP_API_KEY))

tools = [weather_tool]

agent = create_react_agent(model, tools)

# Входные данные должны быть в правильном формате
input_data = {
    "messages": [
        {
            "role": "user",
            "content": "What's the weather like in London?"
        }
    ]
}

result = agent.invoke(input_data)

for message in reversed(result["messages"]):
    if hasattr(message, 'content') and message.content and not hasattr(message, 'tool_calls'):
        response = message.content
        break
else:
    response = "Не удалось получить ответ"

print(response)