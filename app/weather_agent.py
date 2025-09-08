import os
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
import requests
import json
from dotenv import load_dotenv


load_dotenv()

AI_TOKEN1 = os.getenv("AI_TOKEN1")


class WeatherAgent:
    def __init__(self):
        self.model = init_chat_model("gpt-5-nano",
                                model_provider="openai",
                                api_key=AI_TOKEN1,
                                base_url="https://api.aitunnel.ru/v1/",
                                temperature=0)

    def get_weather(self, city: str) -> str:
        """Функция для получения погоды через API"""
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"

        try:
            response = requests.get(url)
            data = response.json()

            if data['cod'] != 200:
                return f"Не удалось получить погоду для {city}"

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
            response = await self.model.ainvoke([HumanMessage(prompt)])
            print(response)
            output = response.content
            result = json.loads(output)
            print(result)
            return result["is_weather"], result["city"]
        except Exception as e:
            print(f"Ошибка при работе агента погоды: {e}")
            return False, ""
