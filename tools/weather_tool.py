from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent
except ImportError:
    HumanMessage = None
    SystemMessage = None
    ChatOpenAI = None
    create_react_agent = None

    def tool(func):
        return func


load_dotenv(override=True)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")
DEFAULT_MODEL = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")

SOUTHEAST_ASIA_CITY_QUERY_MAP = {
    "다낭": "Da Nang,VN",
    "호이안": "Hoi An,VN",
    "하노이": "Hanoi,VN",
    "호치민": "Ho Chi Minh,VN",
    "방콕": "Bangkok,TH",
    "치앙마이": "Chiang Mai,TH",
    "푸켓": "Phuket,TH",
    "싱가포르": "Singapore,SG",
    "쿠알라룸푸르": "Kuala Lumpur,MY",
    "코타키나발루": "Kota Kinabalu,MY",
    "발리": "Bali,ID",
    "자카르타": "Jakarta,ID",
    "세부": "Cebu City,PH",
    "마닐라": "Manila,PH",
}


def get_supported_cities_text() -> str:
    return ", ".join(SOUTHEAST_ASIA_CITY_QUERY_MAP.keys())


def detect_city(user_input: str) -> str:
    for city in SOUTHEAST_ASIA_CITY_QUERY_MAP:
        if city in user_input:
            return city
    return "방콕"


def normalize_city(city: str) -> str:
    city = city.strip()
    for supported_city in SOUTHEAST_ASIA_CITY_QUERY_MAP:
        if supported_city in city:
            return supported_city
    return city


def get_openweather_city_query(city: str) -> str:
    city = normalize_city(city)
    return SOUTHEAST_ASIA_CITY_QUERY_MAP.get(city, SOUTHEAST_ASIA_CITY_QUERY_MAP["방콕"])


def _request_openweather(endpoint: str, params: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not OPENWEATHER_API_KEY:
        return None, "`OPENWEATHER_API_KEY`를 `.env` 또는 환경변수에 추가해 주세요."

    url = f"https://api.openweathermap.org/data/2.5/{endpoint}"
    request_params = {
        **params,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "kr",
    }

    try:
        response = requests.get(url, params=request_params, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as error:
        return None, f"OpenWeatherMap API 호출에 실패했어요: {error}"


def _weather_icon_tip(description: str) -> str:
    lowered = description.lower()
    if any(keyword in lowered for keyword in ("rain", "drizzle", "thunderstorm", "비", "소나기")):
        return "우산이나 가벼운 우비를 챙기는 게 좋아요."
    if any(keyword in lowered for keyword in ("clear", "맑음")):
        return "햇볕이 강할 수 있으니 선크림과 모자를 챙겨 주세요."
    if any(keyword in lowered for keyword in ("cloud", "구름", "흐림")):
        return "흐려도 자외선은 강할 수 있어 선크림은 챙기는 편이 좋아요."
    return "현지 이동이 많다면 물과 얇은 겉옷을 함께 챙겨 주세요."


def _make_outfit_tip(temp: float | int | None, humidity: float | int | None, description: str) -> str:
    if temp is None:
        return _weather_icon_tip(description)

    tips = []
    if temp >= 30:
        tips.append("얇고 통풍이 잘 되는 반팔, 린넨 셔츠, 샌들")
    elif temp >= 24:
        tips.append("반팔이나 얇은 셔츠")
    else:
        tips.append("얇은 긴팔이나 가벼운 겉옷")

    if humidity is not None and humidity >= 75:
        tips.append("땀 닦을 손수건")

    tips.append(_weather_icon_tip(description))
    return ", ".join(tips)


def _format_current_weather(city: str, data: dict[str, Any]) -> str:
    weather_description = data.get("weather", [{}])[0].get("description", "정보 없음")
    main = data.get("main", {})
    wind = data.get("wind", {})
    temp = main.get("temp")
    feels_like = main.get("feels_like")
    humidity = main.get("humidity")
    wind_speed = wind.get("speed")
    outfit_tip = _make_outfit_tip(temp, humidity, weather_description)

    return (
        f"{city} 현재 날씨입니다.\n"
        f"- 날씨: {weather_description}\n"
        f"- 현재 기온: {temp}도\n"
        f"- 체감 기온: {feels_like}도\n"
        f"- 습도: {humidity}%\n"
        f"- 바람: {wind_speed}m/s\n"
        f"- 여행 옷차림/준비물: {outfit_tip}\n"
        "실시간 OpenWeatherMap API 기준입니다."
    )


def _group_forecast_by_date(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in data.get("list", []):
        date_text = item.get("dt_txt", "")
        date_key = date_text.split(" ")[0]
        if date_key:
            grouped[date_key].append(item)
    return grouped


def _format_forecast_day_line(date_key: str, items: list[dict[str, Any]]) -> str:
    temps = [item.get("main", {}).get("temp") for item in items if item.get("main", {}).get("temp") is not None]
    humidity_values = [
        item.get("main", {}).get("humidity")
        for item in items
        if item.get("main", {}).get("humidity") is not None
    ]
    descriptions = [
        item.get("weather", [{}])[0].get("description", "정보 없음")
        for item in items
    ]
    rain_probs = [item.get("pop", 0) for item in items]

    min_temp = round(min(temps), 1) if temps else "정보 없음"
    max_temp = round(max(temps), 1) if temps else "정보 없음"
    avg_humidity = round(sum(humidity_values) / len(humidity_values)) if humidity_values else "정보 없음"
    main_description = Counter(descriptions).most_common(1)[0][0] if descriptions else "정보 없음"
    max_rain_percent = round(max(rain_probs) * 100) if rain_probs else 0
    tip = _make_outfit_tip(
        max(temps) if temps else None,
        avg_humidity if isinstance(avg_humidity, int) else None,
        main_description,
    )

    return (
        f"- {date_key}: {main_description}, {min_temp}~{max_temp}도, "
        f"습도 평균 {avg_humidity}%, 강수확률 최대 {max_rain_percent}% / {tip}"
    )


def _format_forecast(city: str, data: dict[str, Any], days: int) -> str:
    grouped = _group_forecast_by_date(data)

    if not grouped:
        return f"{city} 예보 데이터를 찾지 못했어요."

    lines = [f"{city} {days}일 날씨 예보입니다."]
    for date_key, items in list(grouped.items())[:days]:
        lines.append(_format_forecast_day_line(date_key, items))

    lines.append("OpenWeatherMap 5일/3시간 예보 기준이라 5일을 넘는 일정은 현지에서 다시 확인해 주세요.")
    return "\n".join(lines)


def _format_forecast_for_dates(city: str, data: dict[str, Any], requested_dates: list[str], label: str) -> str:
    grouped = _group_forecast_by_date(data)
    if not grouped:
        return f"{city} 예보 데이터를 찾지 못했어요."

    available_dates = set(grouped.keys())
    matched_dates = [date_key for date_key in requested_dates if date_key in available_dates]
    if not matched_dates:
        first_date = min(available_dates)
        last_date = max(available_dates)
        return (
            f"{city} {label} 예보는 OpenWeatherMap 5일 예보 범위에 없어요.\n"
            f"현재 조회 가능한 날짜: {first_date} ~ {last_date}"
        )

    lines = [f"{city} {label} 날씨 예보입니다."]
    for date_key in matched_dates:
        lines.append(_format_forecast_day_line(date_key, grouped[date_key]))

    missing_dates = [date_key for date_key in requested_dates if date_key not in available_dates]
    if missing_dates:
        lines.append(f"참고: {', '.join(missing_dates)} 예보는 아직 OpenWeatherMap 5일 예보 범위에 없어요.")

    lines.append("OpenWeatherMap 5일/3시간 예보 기준입니다.")
    return "\n".join(lines)


def _today() -> date:
    return datetime.now().date()


def _next_weekend_dates(today: date | None = None) -> list[str]:
    today = today or _today()
    days_until_saturday = (5 - today.weekday()) % 7
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)
    return [saturday.isoformat(), sunday.isoformat()]


def _parse_requested_dates(user_input: str, today: date | None = None) -> list[str]:
    today = today or _today()
    requested_dates: list[str] = []

    for match in re.finditer(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", user_input):
        year, month, day = map(int, match.groups())
        try:
            requested_dates.append(date(year, month, day).isoformat())
        except ValueError:
            continue

    last_month: int | None = None
    has_month_expression = "월" in user_input
    for match in re.finditer(r"(?:(\d{1,2})\s*월\s*)?(\d{1,2})\s*일", user_input):
        month_text, day_text = match.groups()
        day = int(day_text)

        if month_text:
            last_month = int(month_text)
            month = last_month
        elif last_month:
            month = last_month
        elif has_month_expression or day >= today.day:
            month = today.month
        else:
            continue

        year = today.year
        try:
            requested_date = date(year, month, day)
        except ValueError:
            continue

        if requested_date < today and not month_text:
            continue
        requested_dates.append(requested_date.isoformat())

    if "내일" in user_input:
        requested_dates.append((today + timedelta(days=1)).isoformat())
    if "모레" in user_input:
        requested_dates.append((today + timedelta(days=2)).isoformat())
    if "이번 주말" in user_input or "이번주말" in user_input or "주말" in user_input:
        requested_dates.extend(_next_weekend_dates(today))

    return list(dict.fromkeys(requested_dates))


def _date_request_label(user_input: str, requested_dates: list[str]) -> str:
    if "이번 주말" in user_input or "이번주말" in user_input or "주말" in user_input:
        return f"이번 주말({', '.join(requested_dates)})"
    return ", ".join(requested_dates)


def _detect_forecast_days(user_input: str) -> int:
    match = re.search(r"(\d+)\s*일", user_input)
    if match:
        return min(max(int(match.group(1)), 1), 5)
    if any(keyword in user_input for keyword in ("주말", "모레", "내일")):
        return 3
    if any(keyword in user_input for keyword in ("이번 주", "이번주", "며칠", "예보")):
        return 5
    return 3


def _wants_forecast(user_input: str) -> bool:
    return any(
        keyword in user_input
        for keyword in ("내일", "모레", "주말", "이번 주", "이번주", "예보", "며칠", "일정", "여행 기간")
    )


@tool
def get_current_weather(city: str) -> str:
    """동남아 지원 도시의 현재 날씨, 기온, 습도, 바람, 옷차림 팁을 조회합니다."""
    city = normalize_city(city)
    if city not in SOUTHEAST_ASIA_CITY_QUERY_MAP:
        return f"`{city}`는 지원 도시가 아니에요. 지원 도시: {get_supported_cities_text()}"

    data, error_message = _request_openweather("weather", {"q": get_openweather_city_query(city)})
    if error_message:
        return error_message
    return _format_current_weather(city, data or {})


@tool
def get_weather_forecast(city: str, days: int = 3) -> str:
    """동남아 지원 도시의 1~5일 날씨 예보와 여행 준비 팁을 조회합니다."""
    city = normalize_city(city)
    if city not in SOUTHEAST_ASIA_CITY_QUERY_MAP:
        return f"`{city}`는 지원 도시가 아니에요. 지원 도시: {get_supported_cities_text()}"

    days = min(max(int(days), 1), 5)
    data, error_message = _request_openweather("forecast", {"q": get_openweather_city_query(city)})
    if error_message:
        return error_message
    return _format_forecast(city, data or {}, days)


@tool
def get_weather_forecast_by_dates(city: str, dates: list[str], label: str = "요청 날짜") -> str:
    """동남아 지원 도시의 특정 날짜별 날씨 예보와 여행 준비 팁을 조회합니다. dates는 YYYY-MM-DD 목록입니다."""
    city = normalize_city(city)
    if city not in SOUTHEAST_ASIA_CITY_QUERY_MAP:
        return f"`{city}`는 지원 도시가 아니에요. 지원 도시: {get_supported_cities_text()}"

    data, error_message = _request_openweather("forecast", {"q": get_openweather_city_query(city)})
    if error_message:
        return error_message
    return _format_forecast_for_dates(city, data or {}, dates, label)


@tool
def get_supported_weather_cities() -> str:
    """날씨 조회가 가능한 동남아 도시 목록을 알려줍니다."""
    return get_supported_cities_text()


WEATHER_TOOLS = [
    get_current_weather,
    get_weather_forecast,
    get_weather_forecast_by_dates,
    get_supported_weather_cities,
]


def create_weather_agent():
    if ChatOpenAI is None or create_react_agent is None:
        raise RuntimeError("langchain-openai와 langgraph가 설치되어 있지 않습니다.")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    llm = ChatOpenAI(model=DEFAULT_MODEL, temperature=0)
    return create_react_agent(llm, tools=WEATHER_TOOLS)


def weather_tool2(user_input: str) -> str:
    """자연어 날씨 질문을 받아 현재 날씨 또는 예보를 답합니다."""
    city = detect_city(user_input)
    requested_dates = _parse_requested_dates(user_input)

    if requested_dates:
        label = _date_request_label(user_input, requested_dates)
        if hasattr(get_weather_forecast_by_dates, "invoke"):
            return get_weather_forecast_by_dates.invoke({"city": city, "dates": requested_dates, "label": label})
        return get_weather_forecast_by_dates(city, requested_dates, label)

    if ChatOpenAI is not None and create_react_agent is not None and os.getenv("OPENAI_API_KEY"):
        agent = create_weather_agent()
        messages = [
            SystemMessage(
                content=(
                    "너는 TravelMate의 동남아 날씨 전용 에이전트야. "
                    "반드시 제공된 날씨 도구만 사용해서 답하고, 현재 날씨/예보/옷차림/준비물 중심으로 한국어로 간결하게 답해."
                )
            ),
            HumanMessage(content=user_input),
        ]
        result = agent.invoke({"messages": messages})
        return result["messages"][-1].content

    if _wants_forecast(user_input):
        days = _detect_forecast_days(user_input)
        if hasattr(get_weather_forecast, "invoke"):
            return get_weather_forecast.invoke({"city": city, "days": days})
        return get_weather_forecast(city, days)

    if hasattr(get_current_weather, "invoke"):
        return get_current_weather.invoke({"city": city})
    return get_current_weather(city)


def answer_weather_question(user_input: str) -> str:
    return weather_tool2(user_input)


if __name__ == "__main__":
    print(weather_tool2("다낭 이번주말 날씨랑 옷차림 알려줘"))
