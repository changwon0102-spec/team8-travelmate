"""TravelMate 통합 실행 앱.

PRD의 Gradio UI 구조를 유지하면서 각 팀원이 만든 tool 파일을 연결한다.
app.py는 사용자 입력을 어떤 tool로 보낼지 정하고, 출력 형식을 통일한다.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Callable

from dotenv import load_dotenv

from tools.translate_tool_api import translate_text
from tools import weather_tool as weather_module


load_dotenv(override=True)

APP_TITLE = "TravelMate 동남아 여행 도우미"
APP_DESCRIPTION = "환율, 경비, 날씨, 여행 추천, 여행 회화 번역을 한 번에 도와드려요."
SUPPORTED_COUNTRIES = ["태국", "베트남", "필리핀", "인도네시아", "말레이시아", "싱가포르"]
CITY_NAMES = list(weather_module.SOUTHEAST_ASIA_CITY_QUERY_MAP.keys())

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
.tm-side, .tm-main {
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
.tm-feature button {
  min-height: 58px;
  white-space: normal;
  border-radius: 12px !important;
  border: 1px solid rgba(15, 159, 154, 0.18) !important;
  box-shadow: 0 8px 18px rgba(38, 50, 56, 0.06);
}
button.primary, .gradio-button.primary {
  background: var(--tm-coral) !important;
  border-color: var(--tm-coral) !important;
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


TOOL_LABELS = {
    "weather": "날씨 Tool 사용",
    "exchange": "환율/경비 Tool 사용",
    "travel": "여행지 추천 Tool 사용",
    "translate": "번역 Tool 사용",
}


def current_reference_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def select_tools(user_input: str) -> list[str]:
    """PRD의 키워드 기반 tool 선택 기준을 app.py에서 통일한다."""
    text = user_input.lower()
    selected_tools: list[str] = []

    if any(keyword in text for keyword in ("번역", "영어로", "태국어로", "베트남어로", "한국어로")):
        selected_tools.append("translate")
    if any(keyword in text for keyword in ("날씨", "기온", "비", "우산", "옷차림")):
        selected_tools.append("weather")
    if any(keyword in text for keyword in ("환율", "달러", "원화", "만원", "경비", "예산", "비용", "1인당", "바트", "동")):
        selected_tools.append("exchange")
    if any(keyword in text for keyword in ("여행지", "추천", "코스", "일정", "맛집", "관광지", "카페", "쇼핑", "커플", "가족", "혼자", "친구")):
        selected_tools.append("travel")

    return selected_tools or ["general"]


def detect_target_language(user_input: str) -> str:
    if "태국어" in user_input:
        return "태국어"
    if "베트남어" in user_input:
        return "베트남어"
    if "한국어" in user_input:
        return "한국어"
    return "영어"


def extract_translation_text(user_input: str, target_language: str) -> str:
    """번역 tool에는 요청 문구를 제거한 문장만 넘긴다."""
    patterns = [
        rf"(.+?)(?:을|를)?\s*{target_language}로\s*번역",
        r"(.+?)(?:을|를)?\s*번역",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input)
        if match:
            return match.group(1).strip()
    return user_input.strip()


def format_tool_response(tool_name: str, title: str, content: str) -> str:
    """PRD의 Tool 배지 + 제목 출력 형식을 통일한다."""
    badge = TOOL_LABELS.get(tool_name, tool_name)
    return f"[{badge}]\n\n{title}\n\n{content}"


def safe_run(tool_name: str, title: str, runner: Callable[[], str]) -> str:
    """개별 tool 오류가 전체 Gradio 앱을 중단시키지 않도록 감싼다."""
    try:
        content = runner()
    except Exception as error:
        content = (
            "요약:\n"
            f"{title} 실행 중 오류가 발생했어요.\n\n"
            "상세 정보:\n"
            f"{error}\n\n"
            "여행 팁:\n"
            ".env API 키, requirements.txt 설치, tool 함수명을 확인해 주세요."
        )
    return format_tool_response(tool_name, title, content)


def run_translate_tool(user_input: str) -> str:
    target_language = detect_target_language(user_input)
    source_text = extract_translation_text(user_input, target_language)
    raw_result = translate_text(source_text, target_language)

    # translate_tool_api.py는 기존 translate_tool.py의 출력 형식을 재사용한다.
    return re.sub(r"^.+? 번역:", "번역 결과:", raw_result, count=1)


def call_weather_tool(function: Callable, payload: dict) -> str:
    """LangChain @tool 객체와 일반 Python 함수를 모두 app.py에서 같은 방식으로 호출한다."""
    if hasattr(function, "invoke"):
        return str(function.invoke(payload))
    return str(function(**payload))


def run_weather_tool(user_input: str) -> str:
    # 새 weather_tool.py는 날짜별 예보/일반 예보/현재 날씨 tool을 나눠 제공한다.
    # app.py에서는 에이전트 대신 해당 tool을 직접 호출해 날씨 API 응답을 안정적으로 받는다.
    city = weather_module.detect_city(user_input)
    requested_dates = weather_module._parse_requested_dates(user_input)

    if requested_dates:
        label = weather_module._date_request_label(user_input, requested_dates)
        weather_result = call_weather_tool(
            weather_module.get_weather_forecast_by_dates,
            {"city": city, "dates": requested_dates, "label": label},
        )
    elif weather_module._wants_forecast(user_input):
        days = weather_module._detect_forecast_days(user_input)
        weather_result = call_weather_tool(
            weather_module.get_weather_forecast,
            {"city": city, "days": days},
        )
    else:
        weather_result = call_weather_tool(
            weather_module.get_current_weather,
            {"city": city},
        )

    weather_result = re.sub(r"appid=[^&\\s)]+", "appid=***", weather_result)

    return (
        "요약:\n"
        "요청한 여행지의 현재 날씨와 준비물 정보를 확인했어요.\n\n"
        "상세 정보:\n"
        f"{weather_result}\n"
        f"- 날씨 조회 기준 시각: **{current_reference_time()}**\n\n"
        "여행 팁:\n"
        "동남아는 실내 냉방이 강한 곳이 많으니 얇은 겉옷을 함께 챙기면 좋아요."
    )


def run_exchange_tool(user_input: str) -> str:
    # exchange_budget_tool.py는 LangChain/LangGraph 에이전트 기반이라 필요한 순간에 import한다.
    from tools.exchange_budget_tool import process_user_query

    result = process_user_query(user_input)
    if result.startswith("에러가 발생했습니다:"):
        return (
            "요약:\n"
            "환율/경비 정보를 가져오는 중 문제가 발생했어요.\n\n"
            "상세 정보:\n"
            f"{result}\n\n"
            "여행 팁:\n"
            "OPENAI_API_KEY와 네트워크 연결 상태를 확인한 뒤 다시 시도해 주세요."
        )
    return result


def run_travel_tool(user_input: str) -> str:
    # travel_recommend_tool.py는 OpenAI Responses API + 웹 검색 공통 함수를 사용한다.
    from tools.travel_recommend_tool import answer_travel_question

    result = answer_travel_question(user_input)
    if "실행 중 오류가 발생했습니다:" in result:
        return (
            "요약:\n"
            "여행 추천 정보를 생성하는 중 문제가 발생했어요.\n\n"
            "상세 정보:\n"
            f"{result}\n\n"
            "여행 팁:\n"
            "OPENAI_API_KEY와 네트워크 연결 상태를 확인한 뒤 다시 시도해 주세요."
        )
    return result


def answer_message(user_input: str) -> str:
    user_input = (user_input or "").strip()
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

    responses: list[str] = []
    for tool_name in selected_tools:
        if tool_name == "translate":
            responses.append(safe_run("translate", "번역", lambda: run_translate_tool(user_input)))
        elif tool_name == "weather":
            responses.append(safe_run("weather", "날씨", lambda: run_weather_tool(user_input)))
        elif tool_name == "exchange":
            responses.append(safe_run("exchange", "환율/경비", lambda: run_exchange_tool(user_input)))
        elif tool_name == "travel":
            responses.append(safe_run("travel", "여행 추천", lambda: run_travel_tool(user_input)))

    return "\n\n---\n\n".join(responses)


def build_contextual_message(message: str, history: list[dict[str, str]] | None) -> str:
    """후속 질문이 이전 여행 조건을 잃지 않도록 최근 사용자 질문을 함께 전달한다."""
    if not history:
        return message

    follow_up_keywords = (
        "그럼",
        "그러면",
        "거기",
        "그곳",
        "그 일정",
        "이 일정",
        "경비",
        "예산",
        "비용",
        "1인당",
        "까지",
        "추가",
        "다시",
    )
    if not any(keyword in message for keyword in follow_up_keywords):
        return message

    previous_user_messages = []
    for item in history:
        if not isinstance(item, dict) or item.get("role") != "user":
            continue

        content = item.get("content", "")
        # Gradio가 일부 메시지를 list/tuple 형태로 넘기는 경우가 있어 문자열만 추린다.
        if isinstance(content, str):
            previous_user_messages.append(content)
        elif isinstance(content, (list, tuple)):
            text_parts = [part for part in content if isinstance(part, str)]
            if text_parts:
                previous_user_messages.append(" ".join(text_parts))

    previous_context = "\n".join(previous_user_messages[-3:])
    if not previous_context:
        return message

    return (
        "이전 대화의 사용자 요청:\n"
        f"{previous_context}\n\n"
        "현재 사용자 요청:\n"
        f"{message}\n\n"
        "위 이전 요청의 여행지, 일정, 인원, 예산 조건을 이어받아 답변해 주세요."
    )


def respond(message: str, history: list[dict[str, str]] | None = None):
    history = history or []
    contextual_message = build_contextual_message(message, history)
    bot_message = answer_message(contextual_message)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": bot_message})
    return "", history


def build_condition_prompt(
    destination: str,
    duration: str,
    people_count: int,
    total_budget: int,
    selected_themes: list[str],
    companion_type: str,
) -> str:
    """왼쪽 조건 입력 UI 값을 자연어 질문으로 바꿔 travel tool에 넘긴다."""
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
    selected_themes: list[str],
    companion_type: str,
    history: list[dict[str, str]] | None = None,
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
        country_badges = " ".join(f"<span class='tm-badge'>{country}</span>" for country in SUPPORTED_COUNTRIES)
        gr.HTML(
            f"""
            <div class="tm-header">
              <h1>TravelMate</h1>
              <p>{APP_DESCRIPTION}</p>
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
                destination = gr.Dropdown(label="여행 국가 또는 도시", choices=CITY_NAMES, value="다낭")
                duration = gr.Dropdown(
                    label="여행 기간",
                    choices=["당일치기", "1박 2일", "2박 3일", "3박 4일", "4박 5일", "일주일"],
                    value="3박 4일",
                )
                people_count = gr.Slider(label="여행 인원", minimum=1, maximum=8, step=1, value=2)
                total_budget = gr.Slider(label="총예산", minimum=30, maximum=300, step=10, value=100, info="만원 기준")
                selected_themes = gr.CheckboxGroup(
                    label="여행 테마",
                    choices=["맛집", "관광", "휴양", "쇼핑", "자연", "액티비티"],
                    value=["맛집", "관광"],
                )
                companion_type = gr.Radio(label="동행자 유형", choices=["혼자", "친구", "커플", "가족"], value="커플")
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
