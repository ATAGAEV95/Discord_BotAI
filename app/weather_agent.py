import os
from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage
import requests
import json
from dotenv import load_dotenv


load_dotenv()


class WeatherAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=os.getenv("AI_TOKEN1"),
            base_url="https://api.aitunnel.ru/v1/",
            model="gpt-5-nano",
            temperature=0
        )

        self.tools = [
            Tool(
                name="get_weather",
                func=self.get_weather,
                description="Получение погоды для указанного города"
            )
        ]

        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            agent_kwargs={
                'system_message': SystemMessage(
                    content="Ты помогаешь определять, нужно ли получать погоду из API или использовать общую модель. Отвечай только JSON.")
            }
        )

    def get_weather(self, city: str) -> str:
        """Функция для получения погоды через API"""
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"

        try:
            response = requests.get(url)
            data = response.json()

            if data['cod'] != 200:
                return f"Не удалось получить погоду для {city}"

            # Извлекаем данные о погоде
            description = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            wind_speed = data['wind']['speed']

            return (f"Погода в {city}: {description}\n"
                    f"Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    f"Влажность: {humidity}%\n"
                    f"Скорость ветра: {wind_speed} м/с")

        except Exception as e:
            return f"Ошибка при получении погоды: {str(e)}"

    async def should_handle_weather(self, message: str):
        """Определяет, относится ли сообщение к запросу погоды"""
        prompt = f"""
        Определи, является ли этот запрос вопросом о погоде: "{message}".
        Ответь в формате JSON: {{"is_weather": true/false, "city": "название города"}}
        """

        try:
            response = await self.agent.ainvoke({"input": prompt})
            print(response)
            output = response.get("output", "")
            result = json.loads(output)
            print(result)
            return result["is_weather"], result["city"]
        except Exception as e:
            print(f"Ошибка при работе агента погоды: {e}")
            return False, ""
