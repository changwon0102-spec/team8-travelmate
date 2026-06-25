from __future__ import annotations

import re

from tools.openai_live_tool import ask_openai


TOOL_NAME = "여행지 추천 Tool 사용"

DESTINATIONS = [
    "방콕",
    "다낭",
    "하노이",
    "호치민",
    "푸켓",
    "치앙마이",
    "싱가포르",
    "쿠알라룸푸르",
    "코타키나발루",
    "발리",
    "세부",
    "보라카이",
    "나트랑",
    "호이안",
]


def _first_match(text: str, candidates: list[str], default: str) -> str:
    for candidate in candidates:
        if candidate in text:
            return candidate
    return default


def _detect_duration(text: str) -> str:
    match = re.search(r"(\d+)\s*박\s*(\d+)\s*일", text)
    if match:
        return f"{match.group(1)}박 {match.group(2)}일"
    match = re.search(r"(\d+)\s*일", text)
    if match:
        return f"{match.group(1)}일"
    return "미정"


def _detect_people_count(text: str) -> int:
    match = re.search(r"(\d+)\s*명", text)
    if match:
        return int(match.group(1))
    if "가족" in text:
        return 4
    if "커플" in text:
        return 2
    if "혼자" in text or "나홀로" in text:
        return 1
    return 2


def _detect_budget(text: str) -> str:
    match = re.search(r"(\d+(?:,\d{3})*)\s*만원", text)
    if match:
        return f"{match.group(1)}만원"
    match = re.search(r"(\d+(?:,\d{3})*)\s*원", text)
    if match:
        return f"{match.group(1)}원"
    return "미정"


def _detect_themes(text: str) -> list[str]:
    theme_keywords = {
        "맛집": "맛집",
        "관광": "관광",
        "카페": "카페",
        "쇼핑": "쇼핑",
        "자연": "자연",
        "힐링": "힐링",
        "액티비티": "액티비티",
        "야경": "야경",
        "해변": "해변",
        "바다": "해변",
    }
    themes = [theme for keyword, theme in theme_keywords.items() if keyword in text]
    return themes or ["관광", "맛집"]


def _detect_companion_type(text: str) -> str:
    if "혼자" in text or "나홀로" in text:
        return "혼자여행"
    if "가족" in text:
        return "가족여행"
    if "커플" in text:
        return "커플여행"
    if "친구" in text:
        return "친구여행"
    return "자유여행"


def _build_travel_prompt(
    destination: str,
    duration: str,
    people_count: int,
    total_budget: str,
    selected_themes: list[str],
    companion_type: str,
    original_question: str,
) -> str:
    return f"""
사용자 원문:
{original_question}

추출한 여행 조건:
- 목적지/지역: {destination}
- 기간: {duration}
- 인원: {people_count}명
- 예산: {total_budget}
- 테마: {", ".join(selected_themes)}
- 동행 유형: {companion_type}

요청:
1. 최신 여행 정보, 영업/휴무 가능성, 이동 동선, 최근 인기 장소를 웹 검색으로 확인해 추천해 주세요.
2. 추천 여행지, 추천 이유, 예상 경비, 맛집/관광지/카페/쇼핑/자연 명소 중 조건에 맞는 장소를 포함해 주세요.
3. 기간이 있으면 일자별 코스를 제안하고, 기간이 미정이면 2박 3일 기준 예시 코스를 제안해 주세요.
4. 날씨나 성수기, 현지 이동 주의사항처럼 현재성이 중요한 내용은 최신 확인 기준임을 표시해 주세요.
5. 한국어로, 초보 여행자가 바로 이해할 수 있게 답변하세요.
""".strip()


def generate_travel_recommendation(
    destination,
    duration,
    people_count,
    total_budget,
    selected_themes,
    companion_type,
):
    """조건 기반 여행 추천을 OpenAI 웹 검색 기반으로 생성합니다."""
    prompt = _build_travel_prompt(
        destination=destination or "동남아",
        duration=duration or "미정",
        people_count=int(people_count or 2),
        total_budget=f"{total_budget}만원" if isinstance(total_budget, int) else str(total_budget or "미정"),
        selected_themes=list(selected_themes or ["관광", "맛집"]),
        companion_type=companion_type or "자유여행",
        original_question="조건 입력 UI에서 생성된 여행 추천 요청",
    )
    return ask_openai(
        tool_name=TOOL_NAME,
        user_input=prompt,
        instructions=(
            "당신은 TravelMate의 동남아 여행 추천 도구입니다. "
            "웹 검색으로 최신 여행 정보를 확인하고, 일정/예산/테마/동행 유형에 맞춘 실용적인 코스를 제안하세요. "
            "확인하지 못한 정보는 단정하지 말고 확인 필요라고 표시하세요."
        ),
        use_web_search=True,
        max_output_tokens=1400,
    )


def answer_travel_question(user_input):
    text = (user_input or "").strip()
    destination = _first_match(text, DESTINATIONS, "동남아")
    prompt = _build_travel_prompt(
        destination=destination,
        duration=_detect_duration(text),
        people_count=_detect_people_count(text),
        total_budget=_detect_budget(text),
        selected_themes=_detect_themes(text),
        companion_type=_detect_companion_type(text),
        original_question=text,
    )
    return ask_openai(
        tool_name=TOOL_NAME,
        user_input=prompt,
        instructions=(
            "당신은 TravelMate의 동남아 여행 추천 도구입니다. "
            "웹 검색으로 최신 여행 정보와 장소 정보를 확인한 뒤 답변하세요. "
            "사용자 조건을 우선하고, 추천 이유와 주의사항을 함께 제시하세요."
        ),
        use_web_search=True,
        max_output_tokens=1400,
    )
