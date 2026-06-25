import os

import requests
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# 동남아 날씨 조회 Tool
# ---------------------------------------------------------------------------
# 역할:
# 1. 사용자 질문에서 동남아 도시명을 찾습니다.
# 2. OpenWeatherMap API로 현재 날씨를 가져옵니다.
# 3. 동남아 여행에 맞는 옷차림과 준비물 팁을 함께 안내합니다.
#
# 지원 도시:
# - 다낭, 호이안, 하노이, 호치민
# - 방콕, 치앙마이, 푸켓
# - 싱가포르
# - 쿠알라룸푸르, 코타키나발루
# - 발리, 자카르타
# - 세부, 마닐라
#
# .env에 권장하는 키 이름:
#   OPENWEATHER_API_KEY=...
#
# 호환을 위해 WEATHER_API_KEY도 함께 읽습니다.
# ---------------------------------------------------------------------------


load_dotenv(override=True)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY") or os.getenv("WEATHER_API_KEY")

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


def get_supported_cities_text():
    """지원하는 동남아 도시 목록을 한 줄 문자열로 만듭니다."""
    return ", ".join(SOUTHEAST_ASIA_CITY_QUERY_MAP.keys())


def detect_city(user_input):
    """질문 안에서 동남아 도시명을 찾습니다."""
    for city in SOUTHEAST_ASIA_CITY_QUERY_MAP:
        if city in user_input:
            return city

    # 도시명이 없을 때는 동남아 대표 여행지인 방콕을 기본값으로 사용합니다.
    return "방콕"


def get_openweather_city_query(city):
    """OpenWeatherMap에 보낼 도시 검색어를 반환합니다."""
    return SOUTHEAST_ASIA_CITY_QUERY_MAP.get(city, SOUTHEAST_ASIA_CITY_QUERY_MAP["방콕"])


def get_weather(city):
    """OpenWeatherMap API로 현재 날씨 데이터를 가져옵니다."""
    if city not in SOUTHEAST_ASIA_CITY_QUERY_MAP:
        return None, (
            f"`{city}`는 현재 동남아 날씨 Tool 지원 도시가 아니에요.\n"
            f"지원 도시: {get_supported_cities_text()}"
        )

    if not OPENWEATHER_API_KEY:
        return None, (
            f"{city} 날씨를 가져오려면 `.env`에 `OPENWEATHER_API_KEY`를 추가해 주세요.\n"
            f"지원 도시: {get_supported_cities_text()}"
        )

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": get_openweather_city_query(city),
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "kr",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as error:
        return None, f"{city} 날씨 API 호출에 실패했어요: {error}"


def make_southeast_asia_tip(temp, humidity, weather_description):
    """동남아 여행 기준의 옷차림과 준비물 팁을 만듭니다."""
    outfit_tip = "통풍이 잘 되는 반팔, 얇은 셔츠, 편한 샌들이 좋아요."
    packing_tips = ["선크림", "모자", "휴대용 물병"]

    if temp is not None and temp >= 30:
        outfit_tip = "한낮에는 많이 더울 수 있어 얇고 밝은색 옷을 추천해요."
        packing_tips.append("휴대용 선풍기")

    if humidity is not None and humidity >= 75:
        packing_tips.append("땀 닦을 손수건")

    rainy_keywords = ["비", "소나기", "rain", "thunderstorm", "drizzle"]
    if any(keyword in weather_description.lower() for keyword in rainy_keywords):
        packing_tips.append("작은 우산 또는 우비")

    return outfit_tip, ", ".join(packing_tips)


def format_weather(city, data):
    """API 응답 JSON을 사용자가 읽기 쉬운 문장으로 바꿉니다."""
    weather_description = data.get("weather", [{}])[0].get("description", "정보 없음")
    temp = data.get("main", {}).get("temp")
    feels_like = data.get("main", {}).get("feels_like")
    humidity = data.get("main", {}).get("humidity")
    wind_speed = data.get("wind", {}).get("speed")

    outfit_tip, packing_tip = make_southeast_asia_tip(temp, humidity, weather_description)

    return (
        f"{city} 현재 날씨입니다.\n"
        f"- 날씨: {weather_description}\n"
        f"- 현재 기온: {temp}도\n"
        f"- 체감 기온: {feels_like}도\n"
        f"- 습도: {humidity}%\n"
        f"- 바람: {wind_speed}m/s\n"
        f"- 동남아 옷차림: {outfit_tip}\n"
        f"- 추천 준비물: {packing_tip}\n"
        "실시간 OpenWeatherMap API 기준입니다."
    )


def weather_tool(user_input):
    """사용자의 동남아 날씨 질문에 답합니다."""
    city = detect_city(user_input)
    data, error_message = get_weather(city)
    if error_message:
        return error_message
    return format_weather(city, data)


# 기존 app.py나 예전 코드에서 쓰던 함수명과도 연결해 둡니다.
def answer_weather_question(user_input):
    return weather_tool(user_input)




if __name__ == "__main__":
    print(weather_tool("다낭 날씨 알려줘"))
