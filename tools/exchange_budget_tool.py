import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# ==========================================
# 1. 환경 설정 및 .env 로드
# ==========================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ==========================================
# 2. 에이전트 도구(Tools) 정의
# ==========================================

def get_live_exchange_rate(base_currency: str = "USD") -> Dict[str, float]:
    """
    OpenAI API Key만을 가지고 있을 때 실시간 환율을 가져오는 신뢰할 수 있는 무료 공공 API를 활용합니다.
    """
    url = f"https://open.er-api.com/v6/latest/{base_currency}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("rates", {})
    except Exception:
        pass
    
    return {}

@tool
def detect_local_currency(location_or_country: str) -> str:
    """
    사용자가 언급한 도시, 지역, 국가명을 기반으로 해당 국가에서 사용하는 표준 화폐 코드(ISO 4217)를 조회합니다.
    
    입력:
        location_or_country (str): 도시명 또는 국가명 (예: '방콕', '태국', '하노이', '베트남', '도쿄', '일본', '유럽' 등)
    출력:
        해당 지역의 화폐 코드 (예: 'THB', 'VND', 'JPY', 'EUR' 등)
    """
    # 동남아 주요 여행지 및 인기 여행 국가/도시 통화 매핑 테이블
    currency_map = {
        # 태국
        "태국": "THB", "방콕": "THB", "푸켓": "THB", "치앙마이": "THB", "파타야": "THB", "THB": "THB", "바트": "THB",
        # 베트남
        "베트남": "VND", "하노이": "VND", "호치민": "VND", "다낭": "VND", "나트랑": "VND", "푸꾸옥": "VND", "VND": "VND", "동": "VND",
        # 일본
        "일본": "JPY", "도쿄": "JPY", "오사카": "JPY", "교토": "JPY", "후쿠오카": "JPY", "삿포로": "JPY", "JPY": "JPY", "엔": "JPY", "엔화": "JPY",
        # 필리핀
        "필리핀": "PHP", "마닐라": "PHP", "세부": "PHP", "보라카이": "PHP", "PHP": "PHP", "페소": "PHP",
        # 싱가포르
        "싱가포르": "SGD", "싱가폴": "SGD", "SGD": "SGD",
        # 대만
        "대만": "TWD", "타이베이": "TWD", "TWD": "TWD",
        # 말레이시아
        "말레이시아": "MYR", "쿠알라룸푸르": "MYR", "코타키나발루": "MYR", "MYR": "MYR", "링깃": "MYR",
        # 미국 및 기본 달러권
        "미국": "USD", "하와이": "USD", "괌": "USD", "USD": "USD", "달러": "USD",
        # 유럽
        "유럽": "EUR", "프랑스": "EUR", "독일": "EUR", "이탈리아": "EUR", "스페인": "EUR", "파리": "EUR", "EUR": "EUR", "유로": "EUR",
        # 한국
        "한국": "KRW", "서울": "KRW", "제주": "KRW", "KRW": "KRW", "원": "KRW", "원화": "KRW"
    }
    
    # 입력값 전처리 (공백 제거 및 소문자 변환 등)
    clean_input = location_or_country.strip().replace(" ", "")
    
    # 매핑 테이블에서 매칭되는 항목 찾기
    for key, val in currency_map.items():
        if key in clean_input or clean_input in key:
            return val
            
    return "UNKNOWN"

@tool
def calculate_currency_exchange(amount: float, from_currency: str, to_currency: str) -> str:
    """
    환율을 변환합니다. (원화[KRW], 달러[USD], 엔화[JPY], 유로[EUR], 바트[THB], 동[VND] 등 통화 변환 가능)
    
    입력:
        amount (float): 변환할 금액
        from_currency (str): 원본 통화 코드 (예: 'KRW', 'USD', 'JPY')
        to_currency (str): 변환할 통화 코드 (예: 'THB', 'VND', 'USD')
    """
    rates = get_live_exchange_rate("USD")
    
    # 백업 환율 데이터 (네트워크 지연이나 외부 API 장애 시 작동하는 보정용 최신 환율)
    backup_rates = {
        "USD": 1.0,
        "KRW": 1380.0,
        "JPY": 155.0,
        "EUR": 0.92,
        "THB": 35.5,
        "VND": 25400.0,
        "PHP": 58.0,
        "SGD": 1.35,
        "TWD": 32.5,
        "MYR": 4.7
    }
    
    active_rates = rates if rates else backup_rates
    
    # 대소문자 구분 방지
    from_curr = from_currency.upper()
    to_curr = to_currency.upper()
    
    if from_curr not in active_rates or to_curr not in active_rates:
        return f"지원하지 않거나 일시적으로 조회가 불가능한 통화입니다. 입력값: {from_curr} -> {to_curr}"
    
    # 기준 통화(USD)로 환산 후 목표 통화로 계산
    result = (amount / active_rates[from_curr]) * active_rates[to_curr]
    return f"{amount} {from_curr}는 약 {result:,.2f} {to_curr}입니다."

@tool
def calculate_total_and_per_person_budget(expenses: dict, num_people: int) -> str:
    """
    항공권, 숙박비, 식비, 교통비, 관광비 등의 항목별 경비를 합산하여 총 경비와 1인당 경비를 계산합니다.
    
    입력:
        expenses (dict): {'lodging': 300000, 'food': 150000, ...} 형태의 항목별 경비 정보
        num_people (int): 여행 인원 수
    """
    total = sum(float(val) for val in expenses.values() if str(val).replace('.', '', 1).isdigit())
    per_person = total / num_people if num_people > 0 else total
    
    return f"총 경비: {total:,.0f}원, 1인당 예상 경비: {per_person:,.0f}원 (인원: {num_people}명)"

@tool
def analyze_budget_suitability(total_budget: float, planned_expenses: float, days: int) -> str:
    """
    사용자의 전체 예산과 계획된 총 경비를 비교하여 예산 적합성을 판단합니다.
    
    입력:
        total_budget (float): 여행자가 설정한 총 예산 (원화 기준)
        planned_expenses (float): 계획된 항목별 경비 합계 (원화 기준)
        days (int): 여행 전체 일정 일수 (예: 3, 5 등)
    """
    if days <= 0:
        return "여행 일정은 최소 1일 이상이어야 합니다."
        
    if planned_expenses > total_budget:
        excess = planned_expenses - total_budget
        return (f"🚨 예산 초과 주의: 계획된 경비({planned_expenses:,.0f}원)가 "
                f"총 예산({total_budget:,.0f}원)을 {excess:,.0f}원 초과합니다. 예산 조정이 필요할 수 있습니다.")
    
    avg_daily = planned_expenses / days
    return (f"✅ 예산 적정: 계획된 경비({planned_expenses:,.0f}원)는 총 예산({total_budget:,.0f}원) 범위 내에 있습니다. "
            f"여행 기간({days}일) 동안 하루 평균 약 {avg_daily:,.0f}원 사용 예정입니다.")

@tool
def categorize_expenses(flight: float, lodging: float, food: float, transport: float, activity: float) -> str:
    """
    항공권, 숙박, 식비, 교통, 관광비 등으로 분류된 항목별 경비 내역을 정리하여 안내합니다.
    
    입력:
        flight (float): 항공권 비용
        lodging (float): 숙박비
        food (float): 식비
        transport (float): 교통비
        activity (float): 관광/액티비티 비용
    """
    total = flight + lodging + food + transport + activity
    
    report = (
        f"📋 항목별 경비 요약 안내:\n"
        f"- ✈️ 항공권: {flight:,.0f}원\n"
        f"- 🏨 숙박비: {lodging:,.0f}원\n"
        f"- 🍕 식비: {food:,.0f}원\n"
        f"- 🚗 교통비: {transport:,.0f}원\n"
        f"- 🎟️ 관광비: {activity:,.0f}원\n"
        f"---------------------------\n"
        f"💰 합계: {total:,.0f}원"
    )
    return report

# 에이전트에게 할당할 도구 세트 (detect_local_currency 추가)
exchange_budget_tools = [
    detect_local_currency,
    calculate_currency_exchange, 
    calculate_total_and_per_person_budget, 
    analyze_budget_suitability, 
    categorize_expenses
]

# ==========================================
# 3. 에이전트 오케스트레이션 및 프롬프트
# ==========================================

llm = ChatOpenAI(model="gpt-4o", temperature=0)

agent_executor = create_react_agent(
    model=llm,
    tools=exchange_budget_tools,
    prompt="""당신은 TravelMate 여행 도우미입니다. 
    사용자의 여행 경비 및 환율 관련 질문을 받으면, 다음 도구들을 적절하게 체인 형식으로 연동하여 답변하세요.
    
    [도구 사용 시나리오 및 절차]
    1. 사용자가 특정 '국가'나 '도시/지역'(예: 방콕, 베트남, 다낭, 일본 등)을 언급하며 환율 변환이나 예산 계산을 요청하는 경우:
       - 먼저 `detect_local_currency` 도구를 호출하여 해당 국가/도시의 화폐 코드를 찾아내십시오.
       - 찾아낸 화폐 코드(예: THB, VND 등)를 바탕으로 `calculate_currency_exchange`를 호출하여 정확하게 환율 계산 결과를 제공하세요.
       - 만약 한국 원화(KRW) 기준으로 변환하고자 하는 경우, 출발 통화는 `KRW`가 됩니다.
       
    2. 사용자가 비용 항목들을 직접 나열하면 이를 Python 딕셔너리 형태로 정제하여 `calculate_total_and_per_person_budget` 도구에 전달하세요.
    3. 전체 예산과 계획한 비용들의 항목(또는 합산 금액), 그리고 여행 일수가 모두 파악된다면, `analyze_budget_suitability` 도구를 함께 연동 호출하여 계획의 적합성을 체계적으로 판단하세요.
    4. 인원수가 질문에 포함되어 있다면 최종 답변에서 반드시 1인당 예상 경비를 명확하게 안내해 주어야 합니다.
    
    [주의사항]
    - 도시나 국가명이 문맥에 등장하면 지레짐작하지 말고, `detect_local_currency`를 통해 표준 코드를 조회한 뒤 환율 계산기에 넘겨주어 실수를 방지하십시오."""
)

# ==========================================
# 4. 질의응답 및 실행 흐름 제어 함수
# ==========================================

def process_user_query(query: str) -> str:
    """
    사용자의 자연어 질문을 받아 에이전트를 실행하고 최종 답변을 반환합니다.
    """
    try:
        response = agent_executor.invoke({
            "messages": [("human", query)]
        })
        return response["messages"][-1].content
    except Exception as e:
        return f"에러가 발생했습니다: {str(e)}"
