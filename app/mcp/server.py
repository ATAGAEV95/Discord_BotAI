import os
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import logging


logging.getLogger("fastmcp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
load_dotenv()


mcp = FastMCP("weather")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


async def make_weather_request(endpoint: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """
    Вспомогательная функция для выполнения запросов к OpenWeatherMap API

    Args:
        endpoint: Конечная точка API (например, "weather" или "forecast")
        params: Параметры запроса

    Returns:
        JSON ответ от API или None в случае ошибки
    """
    if not OPENWEATHER_API_KEY:
        return None

    params["appid"] = OPENWEATHER_API_KEY
    params["lang"] = "ru"

    url = f"{OPENWEATHER_BASE_URL}/{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError:
        return None
    except Exception:
        return None


@mcp.tool()
async def get_current_weather(city: str, units: str = "metric") -> str:
    """
    Получить текущую погоду для указанного города

    Args:
        city: Название города на русском или английском (например, "Москва" или "Moscow")
        units: Система измерения - "metric" (Цельсий) или "imperial" (Фаренгейт)

    Returns:
        Строка с описанием текущей погоды
    """
    params = {
        "q": city,
        "units": units
    }

    data = await make_weather_request("weather", params)

    if not data:
        return f"❌ Не удалось получить погоду для города '{city}'. Проверьте название города."

    if "cod" in data and data["cod"] != 200:
        return f"❌ Ошибка API: {data.get('message', 'Неизвестная ошибка')}"

    try:
        main = data["main"]
        weather = data["weather"][0]
        wind = data["wind"]

        temp_unit = "°C" if units == "metric" else "°F"
        wind_unit = "м/с" if units == "metric" else "миль/ч"

        result = f"""
🌍 Погода в городе {data['name']}, {data['sys']['country']}

🌡️ Температура: {main['temp']:.1f}{temp_unit}
🤔 Ощущается как: {main['feels_like']:.1f}{temp_unit}
📊 Мин/Макс: {main['temp_min']:.1f}{temp_unit} / {main['temp_max']:.1f}{temp_unit}

☁️ Условия: {weather['description'].capitalize()}
💧 Влажность: {main['humidity']}%
🎚️ Давление: {main['pressure']} гПа
💨 Ветер: {wind['speed']} {wind_unit}, направление {wind.get('deg', 'н/д')}°
        """.strip()

        return result

    except KeyError as e:
        return f"❌ Ошибка при обработке данных: {str(e)}"


@mcp.tool()
async def get_forecast(city: str, days: int = 3, units: str = "metric") -> str:
    """
    Получить прогноз погоды на несколько дней

    Args:
        city: Название города на русском или английском
        days: Количество дней для прогноза (1-5)
        units: Система измерения - "metric" (Цельсий) или "imperial" (Фаренгейт)

    Returns:
        Строка с прогнозом погоды
    """
    days = min(max(days, 1), 5)

    params = {
        "q": city,
        "units": units,
        "cnt": days * 8
    }

    data = await make_weather_request("forecast", params)

    if not data:
        return f"❌ Не удалось получить прогноз для города '{city}'."

    if "cod" not in data or data["cod"] != "200":
        return f"❌ Ошибка API: {data.get('message', 'Неизвестная ошибка')}"

    try:
        temp_unit = "°C" if units == "metric" else "°F"

        forecasts = []
        current_date = None
        day_data = []

        for item in data["list"]:
            date = item["dt_txt"].split()[0]

            if current_date != date:
                if day_data:
                    forecasts.append(format_day_forecast(day_data, temp_unit))
                    if len(forecasts) >= days:
                        break

                current_date = date
                day_data = [item]
            else:
                day_data.append(item)

        if day_data and len(forecasts) < days:
            forecasts.append(format_day_forecast(day_data, temp_unit))

        result = f"📅 Прогноз погоды для {data['city']['name']}, {data['city']['country']}\n\n"
        result += "\n\n".join(forecasts)

        return result

    except Exception as e:
        return f"❌ Ошибка при обработке данных прогноза: {str(e)}"


def format_day_forecast(day_data: list, temp_unit: str) -> str:
    """
    Форматирует прогноз на один день

    Args:
        day_data: Список данных о погоде за день (каждые 3 часа)
        temp_unit: Символ единицы температуры

    Returns:
        Отформатированная строка с прогнозом
    """
    date = day_data[0]["dt_txt"].split()[0]

    temps = [item["main"]["temp"] for item in day_data]
    avg_temp = sum(temps) / len(temps)
    min_temp = min(temps)
    max_temp = max(temps)

    descriptions = [item["weather"][0]["description"] for item in day_data]
    most_common_desc = max(set(descriptions), key=descriptions.count)

    avg_humidity = sum(item["main"]["humidity"] for item in day_data) / len(day_data)
    avg_wind = sum(item["wind"]["speed"] for item in day_data) / len(day_data)

    return f"""
📆 {date}
🌡️ Средняя температура: {avg_temp:.1f}{temp_unit}
📊 Мин/Макс: {min_temp:.1f}{temp_unit} / {max_temp:.1f}{temp_unit}
☁️ Условия: {most_common_desc.capitalize()}
💧 Влажность: {avg_humidity:.0f}%
💨 Ветер: {avg_wind:.1f} м/с
    """.strip()


if __name__ == "__main__":
    mcp.run(transport="stdio")