"""TravelMate 통합 실행 앱.

각 팀원이 만든 tools 모듈을 최대한 그대로 사용하고, 이 파일에서는
사용자 입력을 어떤 tool로 보낼지만 결정한다.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, List, Sequence

from dotenv import load_dotenv

from tools.exchange_budget_tool import (
    DEFAULT_EXCHANGE_RATES,
    build_expense_report,
    convert_currency,
    format_currency,
    sample_currency_conversion,
    sample_expense_summary,
)
from tools.translate_tool_api import translate_text
from tools.weather_tool import SOUTHEAST_ASIA_CITY_QUERY_MAP, weather_tool


load_dotenv(override=True)

APP_TITLE = "TravelMate 동남아 여행 도우미"
APP_DESCRIPTION = "환율, 경비, 날씨, 여행 추천, 여행 회화 번역을 한 번에 도와드려요."
SUPPORTED_COUNTRY_BADGES = ["태국", "베트남", "필리핀", "인도네시아", "말레이시아", "싱가포르"]

CUSTOM_CSS = """
:root {
  --tm-teal: #0f9f9a;
  --tm-teal-dark: #087d79;
  --tm-coral: #ff775f;
  --tm-sand: #fff7e8;
  --tm-bg: #f7fbfb;
  --tm-text: #263238;
}
body, .gradio-container {
  background: var(--tm-bg) !important;
  color: var(--tm-text);
}
.tm-header {
  padding: 22px 24px;
  border-radius: 16px;
  background: linear-gradient(135deg, #e9fbf8 0%, #fff5e8 100%);
  box-shadow: 0 10px 30px rgba(15, 159, 154, 0.12);
}
.tm-header h1 {
  margin: 0 0 6px;
  font-size: 32px;
  letter-spacing: 0;
}
.tm-header p {
  margin: 0 0 12px;
  font-size: 16px;
}
.tm-badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tm-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid rgba(15, 159, 154, 0.22);
  color: var(--tm-teal-dark);
  padding: 5px 10px;
  font-size: 13px;
  font-weight: 700;
}
.tm-side {
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid rgba(15, 159, 154, 0.14);
  box-shadow: 0 10px 24px rgba(38, 50, 56, 0.08);
  padding: 16px;
}
.tm-robot {
  border-radius: 14px;
  background: var(--tm-sand);
  padding: 16px;
  border: 1px solid rgba(255, 119, 95, 0.2);
}
.tm-robot-face {
  width: 76px;
  height: 64px;
  margin-bottom: 12px;
  border-radius: 22px;
  background: #e8fffb;
  border: 3px solid var(--tm-teal);
  position: relative;
}
.tm-robot-face::before {
  content: "";
  position: absolute;
  left: 18px;
  top: 24px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--tm-teal-dark);
  box-shadow: 28px 0 0 var(--tm-teal-dark);
}
.tm-robot-face::after {
  content: "";
  position: absolute;
  left: 27px;
  bottom: 14px;
  width: 22px;
  height: 5px;
  border-radius: 999px;
  background: var(--tm-coral);
}
.tm-robot h3 {
  margin: 0 0 8px;
  font-size: 18px;
}
.tm-robot p {
  margin: 0;
  line-height: 1.55;
}
.tm-section-title {
  margin: 18px 0 8px;
  font-size: 15px;
  font-weight: 800;
}
.tm-main {
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid rgba(15, 159, 154, 0.12);
  box-shadow: 0 10px 24px rgba(38, 50, 56, 0.08);
  padding: 16px;
}
button.primary, .gradio-button.primary {
  background: var(--tm-coral) !important;
  border-color: var(--tm-coral) !important;
}
.tm-feature button {
  min-height: 58px;
  white-space: normal;
  border-radius: 12px !important;
  border: 1px solid rgba(15, 159, 154, 0.18) !important;
  box-shadow: 0 8px 18px rgba(38, 50, 56, 0.06);
}
textarea {
  border-radius: 12px !important;
}
@media (max-width: 780px) {
  .tm-header h1 {
    font-size: 26px;
  }
  .tm-side, .tm-main {
    padding: 12px;
  }
}
"""

CITY_NAMES = tuple(SOUTHEAST_ASIA_CITY_QUERY_MAP.keys())

CURRENCY_KEYWORDS: Dict[str, str] = {
    "싱가포르달러": "SGD",
    "베트남동": "VND",
    "달러": "USD",
    "usd": "USD",
    "불": "USD",
    "엔화": "JPY",
    "엔": "JPY",
    "유로": "EUR",
    "바트": "THB",
    "루피아": "IDR",
    "링깃": "MYR",
    "페소": "PHP",
    "만원": "KRW",
    "원화": "KRW",
    "원": "KRW",
    "동": "VND",
}

TARGET_CURRENCY_BY_COUNTRY = {
    "태국": "THB",
    "방콕": "THB",
    "치앙마이": "THB",
    "푸켓": "THB",
    "베트남": "VND",
    "다낭": "VND",
    "호이안": "VND",
    "하노이": "VND",
    "호치민": "VND",
    "필리핀": "PHP",
    "세부": "PHP",
    "마닐라": "PHP",
    "싱가포르": "SGD",
    "말레이시아": "MYR",
    "쿠알라룸푸르": "MYR",
    "코타키나발루": "MYR",
    "인도네시아": "IDR",
    "발리": "IDR",
    "자카르타": "IDR",
}

THEME_KEYWORDS = {
    "맛집": "맛집",
    "음식": "맛집",
    "먹거리": "맛집",
    "관광": "관광지",
    "관광지": "관광지",
    "명소": "관광지",
    "카페": "카페",
    "쇼핑": "쇼핑",
    "자연": "자연",
    "바다": "자연",
    "역사": "역사·문화",
    "문화": "역사·문화",
    "액티비티": "액티비티",
    "체험": "액티비티",
    "야경": "야경",
}


def select_tools(user_input: str) -> List[str]:
    """키워드 기반으로 실행할 tool 목록을 고른다."""
    text = user_input.lower()
    selected: List[str] = []

    if any(keyword in text for keyword in ("번역", "영어로", "태국어로", "베트남어로", "한국어로")):
        selected.append("translate")

    if any(keyword in text for keyword in ("날씨", "기온", "비", "우산", "옷차림")):
        selected.append("weather")

    if any(keyword in text for keyword in ("환율", "달러", "원화", "만원", "경비", "예산", "비용", "1인당", "바트", "동")):
        selected.append("exchange")

    if any(keyword in text for keyword in ("여행지", "추천", "코스", "일정", "맛집", "관광지", "카페", "쇼핑", "커플", "가족", "혼자", "친구")):
        selected.append("travel")

    return selected or ["general"]


def detect_city(user_input: str) -> str:
    for city in CITY_NAMES:
        if city in user_input:
            return city
    return "방콕"


def detect_themes(user_input: str) -> List[str]:
    themes = []
    for keyword, theme in THEME_KEYWORDS.items():
        if keyword in user_input and theme not in themes:
            themes.append(theme)
    return themes or ["맛집", "관광지"]


def detect_companion_type(user_input: str) -> str:
    if any(keyword in user_input for keyword in ("혼자", "혼행")):
        return "혼자여행"
    if any(keyword in user_input for keyword in ("가족", "아이", "부모님")):
        return "가족여행"
    if any(keyword in user_input for keyword in ("커플", "연인", "데이트")):
        return "커플여행"
    if any(keyword in user_input for keyword in ("친구", "우정")):
        return "친구와 여행"
    return "자유 여행"


def detect_duration(user_input: str) -> str:
    match = re.search(r"(\d+)\s*박\s*(\d+)\s*일", user_input)
    if match:
        return f"{match.group(1)}박 {match.group(2)}일"

    match = re.search(r"(\d+)\s*일", user_input)
    if match:
        return f"{match.group(1)}일"

    if "주말" in user_input:
        return "2박 3일"
    return "2박 3일"


def detect_people_count(user_input: str) -> int:
    match = re.search(r"(\d+)\s*명", user_input)
    if match:
        return max(1, int(match.group(1)))

    companion_type = detect_companion_type(user_input)
    if companion_type == "혼자여행":
        return 1
    if companion_type == "커플여행":
        return 2
    if companion_type == "가족여행":
        return 4
    return 2


def detect_budget_manwon(user_input: str) -> int:
    match = re.search(r"(\d+)\s*(?:만\s*원|만원)", user_input)
    if match:
        return int(match.group(1))
    return 100


def current_reference_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def run_travel_tool(user_input: str) -> str:
    destination = detect_city(user_input)
    duration = detect_duration(user_input)
    people_count = detect_people_count(user_input)
    total_budget = detect_budget_manwon(user_input)
    selected_themes = detect_themes(user_input)
    companion_type = detect_companion_type(user_input)

    if not os.getenv("OPENAI_API_KEY"):
        return build_local_travel_recommendation(
            destination=destination,
            duration=duration,
            people_count=people_count,
            total_budget=total_budget,
            selected_themes=selected_themes,
            companion_type=companion_type,
        )

    try:
        from tools.travel_recommend_tool import generate_travel_recommendation

        return generate_travel_recommendation(
            destination=destination,
            duration=duration,
            people_count=people_count,
            total_budget=total_budget,
            selected_themes=selected_themes,
            companion_type=companion_type,
        )
    except ImportError as error:
        return (
            "OpenAI 기반 여행 추천 패키지를 불러오지 못해 기본 추천으로 안내할게요.\n\n"
            f"{build_local_travel_recommendation(destination, duration, people_count, total_budget, selected_themes, companion_type)}\n\n"
            f"참고 오류: {error}"
        )


def build_local_travel_recommendation(
    destination: str,
    duration: str,
    people_count: int,
    total_budget: int,
    selected_themes: Sequence[str],
    companion_type: str,
) -> str:
    """OpenAI 키가 없어도 프로젝트가 바로 시연되도록 기본 추천을 만든다."""
    themes = ", ".join(selected_themes)
    total_budget_krw = total_budget * 10_000
    expense_items = {
        "항공권": total_budget_krw * 0.45,
        "숙박비": total_budget_krw * 0.25,
        "식비/교통비": total_budget_krw * 0.20,
        "관광/예비비": total_budget_krw * 0.10,
    }
    summary = build_expense_report(expense_items, persons=people_count, budget=total_budget_krw)

    return (
        "추천 여행지:\n"
        f"{destination} - {duration} 일정으로 다녀오기 좋은 동남아 대표 여행지예요.\n\n"
        "추천 이유:\n"
        f"- {companion_type} 기준으로 동선이 비교적 단순해요.\n"
        f"- 요청하신 테마({themes})를 일정에 섞기 좋아요.\n"
        f"- 총 예산 **{format_currency(total_budget_krw, 'KRW')}** 안에서 항공권과 숙소를 조절하기 쉬워요.\n\n"
        "예상 경비:\n"
        f"- 항공권: **{format_currency(expense_items['항공권'], 'KRW')}**\n"
        f"- 숙박비: **{format_currency(expense_items['숙박비'], 'KRW')}**\n"
        f"- 식비/교통비: **{format_currency(expense_items['식비/교통비'], 'KRW')}**\n"
        f"- 관광/예비비: **{format_currency(expense_items['관광/예비비'], 'KRW')}**\n"
        f"- 총 예상 경비: **{format_currency(summary.total, 'KRW')}**\n"
        f"- 1인당 예상 경비: **{format_currency(summary.per_person or 0, 'KRW')}**\n"
        f"- 예산 판단: {summary.budget_message}\n\n"
        "추천 테마:\n"
        f"{themes}\n\n"
        "여행 형태별 추천 포인트:\n"
        f"{companion_type} 기준으로 이동 거리를 줄이고, 식사와 휴식 시간을 넉넉하게 잡는 구성이 좋아요.\n\n"
        "테마별 추천 장소:\n"
        "- 맛집: 현지 음식점, 야시장, 해산물 식당\n"
        "- 관광지: 대표 랜드마크, 전망 명소, 시장\n"
        "- 휴식: 숙소 근처 산책 코스와 카페\n\n"
        "추천 일정:\n"
        f"- 1일차: {destination} 도착, 숙소 체크인, 근처 맛집 방문\n"
        "- 2일차: 대표 관광지와 현지 음식 중심 일정\n"
        "- 3일차: 쇼핑 또는 카페, 여유로운 산책 후 귀국 준비\n\n"
        "여행 팁:\n"
        "- 실시간 항공권과 숙소 가격에 따라 예산 차이가 커질 수 있어요.\n"
        "- 더 정교한 AI 추천을 쓰려면 `.env`에 `OPENAI_API_KEY`를 추가해 주세요."
    )


def detect_target_language(user_input: str) -> str:
    if "태국어" in user_input:
        return "태국어"
    if "베트남어" in user_input:
        return "베트남어"
    if "한국어" in user_input:
        return "한국어"
    return "영어"


def extract_translation_text(user_input: str, target_language: str) -> str:
    patterns = [
        rf"(.+?)(?:을|를)?\s*{target_language}로\s*번역",
        r"(.+?)(?:을|를)?\s*번역",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input)
        if match:
            return match.group(1).strip()
    return user_input


def run_translate_tool(user_input: str) -> str:
    target_language = detect_target_language(user_input)
    text = extract_translation_text(user_input, target_language)
    return translate_text(text, target_language)


def normalize_currency_keyword(keyword: str) -> str:
    return CURRENCY_KEYWORDS.get(keyword.lower(), keyword.upper())


def detect_currency(user_input: str, default: str = "KRW") -> str:
    lowered = user_input.lower()
    amount_unit_patterns = [
        (r"\d+(?:\.\d+)?\s*(?:만\s*원|만원|원)", "KRW"),
        (r"\d+(?:\.\d+)?\s*(?:달러|usd|불)", "USD"),
        (r"\d+(?:\.\d+)?\s*(?:엔화|엔)", "JPY"),
        (r"\d+(?:\.\d+)?\s*유로", "EUR"),
        (r"\d+(?:\.\d+)?\s*바트", "THB"),
        (r"\d+(?:\.\d+)?\s*(?:베트남동|동)", "VND"),
        (r"\d+(?:\.\d+)?\s*루피아", "IDR"),
        (r"\d+(?:\.\d+)?\s*링깃", "MYR"),
        (r"\d+(?:\.\d+)?\s*싱가포르달러", "SGD"),
        (r"\d+(?:\.\d+)?\s*페소", "PHP"),
    ]
    for pattern, code in amount_unit_patterns:
        if re.search(pattern, lowered):
            return code

    for keyword, code in CURRENCY_KEYWORDS.items():
        if keyword in lowered:
            return code
    return default


def detect_target_currency(user_input: str, from_currency: str) -> str:
    lowered = user_input.lower()
    if any(keyword in user_input for keyword in ("원화", "한국 돈", "한국돈", "원으로")):
        return "KRW"

    for keyword, currency in TARGET_CURRENCY_BY_COUNTRY.items():
        if keyword in user_input and currency != from_currency:
            return currency

    for keyword, currency in CURRENCY_KEYWORDS.items():
        if keyword in lowered and currency != from_currency:
            return currency

    if from_currency == "KRW":
        return "USD"
    return "KRW"


def detect_amount(user_input: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(만\s*원|만원)", user_input)
    if match:
        return float(match.group(1)) * 10_000

    match = re.search(r"(\d+(?:\.\d+)?)", user_input)
    if match:
        return float(match.group(1))

    return 100.0


def run_exchange_tool(user_input: str) -> str:
    if any(keyword in user_input for keyword in ("경비", "예산", "비용", "1인당")) and not any(
        keyword in user_input for keyword in ("환율", "달러", "바트", "동", "원화")
    ):
        return sample_expense_summary()

    if not any(keyword in user_input for keyword in CURRENCY_KEYWORDS) and "환율" not in user_input:
        return sample_currency_conversion(use_api=False)

    amount = detect_amount(user_input)
    from_currency = detect_currency(user_input)
    to_currency = detect_target_currency(user_input, from_currency)

    try:
        converted = convert_currency(amount, from_currency, to_currency, rates=DEFAULT_EXCHANGE_RATES)
    except ValueError as error:
        return f"환율 계산 중 확인이 필요해요: {error}"

    return (
        "요약:\n"
        f"입력한 금액 **{format_currency(amount, from_currency)}**은 약 **{format_currency(converted, to_currency)}**입니다.\n\n"
        "상세 정보:\n"
        "- 환율 출처: 프로젝트 기본 환율 데이터\n"
        f"- 환율 조회 기준 시각: **{current_reference_time()}**\n"
        f"- 변환 방향: {from_currency} -> {to_currency}\n\n"
        "여행 팁:\n"
        "실제 환전 시점의 환율과 수수료는 달라질 수 있으니 출국 전 은행이나 환전 앱에서 한 번 더 확인해 주세요."
    )


def run_weather_tool(user_input: str) -> str:
    city = detect_city(user_input)
    raw_result = weather_tool(user_input)

    return (
        "요약:\n"
        f"{city} 날씨와 여행 준비 정보를 확인했어요.\n\n"
        "상세 정보:\n"
        f"{raw_result}\n"
        f"- 날씨 조회 기준 시각: **{current_reference_time()}**\n\n"
        "여행 팁:\n"
        "동남아는 실내 냉방이 강한 곳이 많으니 얇은 겉옷을 함께 챙기면 좋아요."
    )


def run_translation_tool(user_input: str) -> str:
    target_language = detect_target_language(user_input)
    text = extract_translation_text(user_input, target_language)
    raw_result = translate_text(text, target_language)
    raw_result = re.sub(r"^.+? 번역:", "번역 결과:", raw_result, count=1)

    if "사용 상황:" in raw_result:
        return raw_result

    return f"{raw_result}\n\n사용 상황:\n식당, 카페, 숙소, 교통 상황에서 필요한 표현을 짧게 말할 때 유용해요."


def tool_badge(tool_name: str) -> str:
    labels = {
        "translate": "번역 Tool 사용",
        "weather": "날씨 Tool 사용",
        "exchange": "환율/경비 Tool 사용",
        "travel": "여행지 추천 Tool 사용",
    }
    return f"[{labels.get(tool_name, tool_name)}]"


def format_tool_response(tool_name: str, title: str, content: str) -> str:
    return f"{tool_badge(tool_name)}\n\n{title}\n\n{content}"


def answer_message(user_input: str) -> str:
    user_input = user_input.strip()
    if not user_input:
        return "질문을 입력해 주세요."

    selected_tools = select_tools(user_input)
    if selected_tools == ["general"]:
        return (
            "요약:\n"
            "아직 어떤 기능을 사용할지 판단하지 못했어요.\n\n"
            "상세 정보:\n"
            "TravelMate에서 사용할 수 있는 질문 예시는 다음과 같아요.\n"
            "- 방콕 날씨 알려줘\n"
            "- 100달러는 원화로 얼마야?\n"
            "- 다낭 3박 4일 가족여행 코스 추천해줘\n"
            "- 계산서 주세요를 영어로 번역해줘\n\n"
            "여행 팁:\n"
            "도시명, 기간, 예산, 원하는 테마를 함께 적으면 더 정확하게 답할 수 있어요."
        )

    responses = []
    for tool_name in selected_tools:
        if tool_name == "translate":
            responses.append(format_tool_response(tool_name, "번역", run_translation_tool(user_input)))
        elif tool_name == "weather":
            responses.append(format_tool_response(tool_name, "날씨", run_weather_tool(user_input)))
        elif tool_name == "exchange":
            responses.append(format_tool_response(tool_name, "환율/경비", run_exchange_tool(user_input)))
        elif tool_name == "travel":
            responses.append(format_tool_response(tool_name, "여행 추천", run_travel_tool(user_input)))

    return "\n\n---\n\n".join(responses)


def respond(message: str, history: List[Dict[str, str]] | None = None):
    history = history or []
    bot_message = answer_message(message)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": bot_message})
    return "", history


def build_condition_prompt(
    destination: str,
    duration: str,
    people_count: int,
    total_budget: int,
    selected_themes: Sequence[str],
    companion_type: str,
) -> str:
    themes = ", ".join(selected_themes) if selected_themes else "관광, 맛집"
    return (
        f"{destination} {duration} {people_count}명 "
        f"예산 {total_budget}만원 {companion_type} "
        f"{themes} 중심 코스 추천해줘"
    )


def respond_from_conditions(
    destination: str,
    duration: str,
    people_count: int,
    total_budget: int,
    selected_themes: Sequence[str],
    companion_type: str,
    history: List[Dict[str, str]] | None = None,
):
    prompt = build_condition_prompt(
        destination=destination,
        duration=duration,
        people_count=int(people_count),
        total_budget=int(total_budget),
        selected_themes=selected_themes,
        companion_type=companion_type,
    )
    return respond(prompt, history)


def create_app():
    import gradio as gr

    with gr.Blocks(title=APP_TITLE) as demo:
        country_badges = " ".join(f"<span class='tm-badge'>{country}</span>" for country in SUPPORTED_COUNTRY_BADGES)
        gr.HTML(
            f"""
            <div class="tm-header">
              <h1>TravelMate</h1>
              <p>동남아 여행에 필요한 정보를 한 번에 확인하세요.</p>
              <div class="tm-badge-row">{country_badges}</div>
            </div>
            """
        )

        with gr.Row():
            with gr.Column(scale=1, min_width=280, elem_classes="tm-side"):
                gr.HTML(
                    """
                    <div class="tm-robot">
                      <div class="tm-robot-face"></div>
                      <h3>안녕하세요! 저는 TravelMate예요.</h3>
                      <p>여행 일정, 예산, 날씨, 환율, 번역까지 도와드릴게요.</p>
                    </div>
                    """
                )
                gr.Markdown("### 여행 조건")
                destination = gr.Dropdown(
                    label="여행 국가 또는 도시",
                    choices=list(CITY_NAMES),
                    value="다낭",
                )
                duration = gr.Dropdown(
                    label="여행 기간",
                    choices=["당일치기", "1박 2일", "2박 3일", "3박 4일", "4박 5일", "일주일"],
                    value="3박 4일",
                )
                people_count = gr.Slider(
                    label="여행 인원",
                    minimum=1,
                    maximum=8,
                    step=1,
                    value=2,
                )
                total_budget = gr.Slider(
                    label="총예산",
                    minimum=30,
                    maximum=300,
                    step=10,
                    value=100,
                    info="만원 기준",
                )
                selected_themes = gr.CheckboxGroup(
                    label="여행 테마",
                    choices=["맛집", "관광", "휴양", "쇼핑", "자연", "액티비티"],
                    value=["맛집", "관광"],
                )
                companion_type = gr.Radio(
                    label="동행자 유형",
                    choices=["혼자", "친구", "커플", "가족"],
                    value="커플",
                )
                condition_button = gr.Button("조건으로 추천 받기", variant="primary")

            with gr.Column(scale=2, min_width=360, elem_classes="tm-main"):
                gr.Markdown("### 빠른 기능")
                with gr.Row(elem_classes="tm-feature"):
                    exchange_button = gr.Button("환율·경비 계산")
                    travel_button = gr.Button("여행지 검색")
                    translate_button = gr.Button("여행 회화 번역")
                    weather_button = gr.Button("날씨 조회")

                chatbot = gr.Chatbot(height=520, placeholder="TravelMate가 여행 정보를 찾고 있어요. 질문을 입력해 주세요.")
                user_input = gr.Textbox(
                    label="질문",
                    placeholder="예: 다낭 날씨 보고 3박 4일 가족여행 코스 추천해줘",
                    lines=2,
                )

                with gr.Row():
                    submit_button = gr.Button("보내기", variant="primary")
                    clear_button = gr.Button("초기화")

                gr.Examples(
                    examples=[
                        "방콕 이번 주말 날씨 알려줘.",
                        "100만 원을 태국 바트로 환산해줘.",
                        "다낭 3박 4일 맛집 여행 코스 추천해줘.",
                        "계산서 주세요를 베트남어로 번역해줘.",
                        "예산 150만 원으로 갈 만한 동남아 여행지 추천해줘.",
                    ],
                    inputs=user_input,
                )

        exchange_button.click(lambda: "100만 원을 태국 바트로 환산해줘.", outputs=user_input)
        travel_button.click(lambda: "다낭 3박 4일 맛집 여행 코스 추천해줘.", outputs=user_input)
        translate_button.click(lambda: "계산서 주세요를 베트남어로 번역해줘.", outputs=user_input)
        weather_button.click(lambda: "방콕 이번 주말 날씨 알려줘.", outputs=user_input)

        condition_button.click(
            respond_from_conditions,
            inputs=[destination, duration, people_count, total_budget, selected_themes, companion_type, chatbot],
            outputs=[user_input, chatbot],
        )
        submit_button.click(respond, inputs=[user_input, chatbot], outputs=[user_input, chatbot])
        user_input.submit(respond, inputs=[user_input, chatbot], outputs=[user_input, chatbot])
        clear_button.click(lambda: [], outputs=chatbot)

    return demo


if __name__ == "__main__":
    app = create_app()
    app.launch(theme="soft", css=CUSTOM_CSS)
