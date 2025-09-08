import json
import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

load_dotenv()

AI_TOKEN1 = os.getenv("AI_TOKEN1")


class WeatherAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        self.model = init_chat_model(
            "gpt-5-nano",
            model_provider="openai",
            api_key=AI_TOKEN1,
            base_url="https://api.aitunnel.ru/v1/",
            temperature=0,
        )

    def get_weather(self, city: str, flag: bool) -> str:
        """Функция для получения погоды через API"""

        if flag:
            url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={self.api_key}&units=metric&lang=ru"
        else:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric&lang=ru"

        try:
            response = requests.get(url)
            data = response.json()

            if flag:
                if data["cod"] != "200":
                    return f"Не удалось получить погоду для {city}"

                tomorrow = (datetime.now() + timedelta(days=1)).date()
                tomorrow_forecasts = [
                    forecast
                    for forecast in data["list"]
                    if datetime.fromtimestamp(forecast["dt"]).date() == tomorrow
                ]

                if not tomorrow_forecasts:
                    return f"Нет данных на завтра для {city}"

                midday_forecast = min(
                    tomorrow_forecasts, key=lambda x: abs(datetime.fromtimestamp(x["dt"]).hour - 12)
                )
                weather_data = midday_forecast
                prefix = f"Прогноз на завтра в {city}:\n"
            else:
                if data["cod"] != 200:
                    return f"Не удалось получить погоду для {city}"

                weather_data = data
                prefix = f"Погода в {city}: "

            description = weather_data["weather"][0]["description"]
            temp = weather_data["main"]["temp"]
            feels_like = weather_data["main"]["feels_like"]
            humidity = weather_data["main"]["humidity"]
            wind_speed = weather_data["wind"]["speed"]

            return (
                f"{prefix}"
                f"{description}\n"
                f"Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                f"Влажность: {humidity}%\n"
                f"Скорость ветра: {wind_speed} м/с"
            )

        except Exception as e:
            return f"Ошибка при получении погоды: {str(e)}"

    async def should_handle_weather(self, message: str):
        """Определяет, относится ли сообщение к запросу погоды"""
        prompt = f"""
        Определи, является ли этот запрос вопросом о погоде: "{message}".
        Если город не указан то пустую строку написать.
        Ответь в формате JSON: {{"is_weather": true/false, "city": "название города"}}
        """

        try:
            response = await self.model.ainvoke([HumanMessage(prompt)])
            output = response.content
            result = json.loads(output)
            # print(response)
            # print(result)
            return result["is_weather"], result["city"]
        except Exception as e:
            print(f"Ошибка при работе агента погоды: {e}")
            return False, ""
