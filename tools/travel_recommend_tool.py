import os
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일에 저장된 환경 변수(API Key)를 시스템으로 불러옵니다.
load_dotenv()

# OpenAI 클라이언트를 초기화합니다. API 키는 환경 변수에서 자동으로 참조됩니다.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_travel_recommendation(destination, duration, people_count, total_budget, selected_themes, companion_type):
    """
    사용자가 입력한 조건들을 바탕으로 OpenAI API를 호출하여 
    맞춤형 동남아 여행 계획 및 추천 결과를 생성하는 핵심 함수입니다.
    """
    
    # 1. API 키 누락 예외 처리: 키가 비어있을 경우 기술적 에러 대신 친절한 안내 문구를 반환합니다.
    if not os.getenv("OPENAI_API_KEY"):
        return (
            "⚠️ [오류] 시스템에 OpenAI API 설정이 완료되지 않았습니다.\n"
            "환경 변수 또는 .env 파일의 API 키 등록 상태를 확인해 주세요."
        )

    # 2. 필수 조건 검증: 도시명 누락 시 UX 요구사항에 따라 친절하게 정보 선택을 유도합니다.
    if not destination or destination.strip() == "":
        return "🤖 어느 동남아 도시로 여행을 떠나고 싶으신가요? 좌측 폼이나 입력창에 도시명을 알려주시면 바로 추천해 드릴게요!"

    # 3. 리스트 형태의 테마를 쉼표 문자열로 보기 좋게 변환합니다.
    themes_string = ", ".join(selected_themes) if selected_themes else "일반 관광 및 자유 테마"

    # 4. 기획서에서 명시한 '답변 출력 형식'을 LLM이 완벽히 준수하도록 페르소나와 구조를 설계합니다.
    system_prompt = (
        "당신은 친절하고 귀여운 동남아 전문 로봇 여행 가이드 'TravelMate'입니다.\n"
        "반드시 다음 요청사항에 맞춰 한국어로 답변을 생성해 주세요.\n\n"
        "[답변 작성 지침]\n"
        "1. 친근하고 전문적인 가이드 말투(~요, ~해보세요!)를 사용하고 적절한 이모지를 섞어주세요.\n"
        "2. 반드시 지정된 7가지 목차 구조를 정확하게 지켜 가독성 높은 마크다운 목록 형태로 출력하세요.\n"
        "3. 사용자가 직관적으로 인지해야 하는 핵심 수치(금액, 기온 등)는 반드시 **굵게(Bold)** 표시하세요.\n"
        "4. 출처 링크가 필요한 항목은 신뢰도 높은 가상의 정보 출처(예: [태국 관광청 공식 가이드])를 예시 형태로 포함하세요."
    )

    user_prompt = f"""
동남아시아 여행 추천 및 일정을 기획해 주세요. 조건은 다음과 같습니다.

[여행 조건]
- 목적지/도시: {destination}
- 일정/기간: {duration}
- 여행 인원: **{people_count}명**
- 총 예산: **{total_budget}만 원** (이 예산 범위 내에서 실현 가능한 가성비/가심비 일정으로 기획할 것)
- 선호 테마: {themes_string}
- 동행자 유형: {companion_type}

[반드시 포함할 출력 형식 및 순서]
1. 추천 여행지: (도시 이름 및 간략한 슬로건)
2. 추천 이유: (동행자 유형과 선호 테마에 초점을 맞춘 맞춤형 이유 3가지)
3. 예상 경비: (항공권, 숙박비, 식비/교통비 항목으로 분류하고 금액은 **굵게** 표시)
4. 추천 관광지와 맛집: (테마에 맞는 랜드마크 및 대표 식당 3~4곳 리스트화)
5. 일자별 여행 일정: (일정 기간에 맞추어 무리 없는 동선으로 아침/점심/저녁 코스 제안)
6. 날씨와 준비물: (목적지의 일반적인 기후 정보를 바탕으로 옷차림과 필수 준비물 추천, 기온 **굵게** 표시)
7. 여행 팁: (해당 동행자와 이동할 때 주의할 점 및 현지 사기 예방 등 꿀팁 제공)
"""

    try:
        # 5. OpenAI Chat Completions API를 호출합니다. (가성비와 성능이 균형 잡힌 gpt-4o-mini 모델 적용)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7 # 일정 수준의 다채롭고 자연스러운 텍스트 출력을 유도합니다.
        )
        
        return response.choices[0].message.content

    except Exception as error:
        # 6. 네트워크 단절 등 API 호출 실패 시 에러가 터져 서버가 멈추지 않도록 예외 처리를 수행합니다.
        return (
            "🤖 죄송해요! 여행 정보를 찾고 분석하는 도중 일시적인 통신 오류가 발생했어요.\n"
            f"잠시 후 다시 시도해 주시면 감사하겠습니다. (오류 내용: {str(error)})"
        )