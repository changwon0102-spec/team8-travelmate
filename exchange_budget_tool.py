"""TravelMate 환율 및 경비 계산 도구.

이 모듈은 환율 변환과 여행 경비 계산을 위한 기본 함수들을 제공합니다.
초기 버전에서는 고정 환율과 항목 합산 기반 계산을 사용합니다.
최종 버전에서는 외부 API 연동으로 최신 환율을 가져오는 방식으로 확장할 수 있습니다.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

# 기본 환율 (KRW 기준) - 초기 버전 샘플 데이터
DEFAULT_EXCHANGE_RATES: Dict[str, float] = {
    "KRW": 1.0,
    "USD": 1380.0,
    "EUR": 1500.0,
    "JPY": 10.2,
    "CNY": 190.0,
    "THB": 38.0,
    "VND": 0.058,
    "IDR": 0.093,
    "MYR": 300.0,
    "SGD": 1020.0,
    "PHP": 24.0,
}

SUPPORTED_CURRENCIES = set(DEFAULT_EXCHANGE_RATES)

DEFAULT_EXCHANGE_API_URL = "https://api.exchangerate.host/latest"
DEFAULT_BASE_CURRENCY = "KRW"
DEFAULT_EXCHANGE_API_KEY_ENV = "EXCHANGE_API_KEY"
DEFAULT_EXCHANGE_API_URL_ENV = "EXCHANGE_API_URL"


def normalize_currency_code(currency: str) -> str:
    """통화 코드를 표준 형식으로 변환합니다."""
    return currency.strip().upper()


def load_dotenv(dotenv_path: Optional[str] = None) -> Dict[str, str]:
    """`.env 파일을 읽어 딕셔너리로 반환합니다."""
    if dotenv_path is None:
        dotenv_path = Path.cwd() / ".env"
    else:
        dotenv_path = Path(dotenv_path)

    if not dotenv_path.exists():
        return {}

    dotenv_pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
    values: Dict[str, str] = {}
    with dotenv_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = dotenv_pattern.match(line)
            if not match:
                continue

            key, value = match.group(1), match.group(2)
            if value.startswith("\"") and value.endswith("\""):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            values[key] = value

    return values


def get_dotenv_value(key: str, dotenv_path: Optional[str] = None) -> Optional[str]:
    """`.env` 파일에서 키 값을 가져옵니다."""
    dotenv_values = load_dotenv(dotenv_path=dotenv_path)
    value = dotenv_values.get(key)
    if value:
        return value.strip()
    return None


def get_api_key_from_dotenv(
    api_key_env: str = DEFAULT_EXCHANGE_API_KEY_ENV,
    dotenv_path: Optional[str] = None,
) -> Optional[str]:
    """`.env` 파일에서 API 키를 가져옵니다."""
    return get_dotenv_value(api_key_env, dotenv_path=dotenv_path)


DEFAULT_OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL_ENV = "OPENAI_DEFAULT_MODEL"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def get_openai_api_key(dotenv_path: Optional[str] = None) -> Optional[str]:
    """`.env` 파일에서 OpenAI API 키를 가져옵니다."""
    return get_dotenv_value("OPENAI_API_KEY", dotenv_path=dotenv_path)


def get_openai_model(dotenv_path: Optional[str] = None) -> str:
    """`.env` 파일에서 OpenAI 모델 이름을 가져옵니다."""
    return get_dotenv_value(DEFAULT_OPENAI_MODEL_ENV, dotenv_path=dotenv_path) or DEFAULT_OPENAI_MODEL


def call_openai_api(prompt: str, model: Optional[str] = None, dotenv_path: Optional[str] = None) -> str:
    """OpenAI Responses API를 호출하고 텍스트 응답을 반환합니다."""
    api_key = get_openai_api_key(dotenv_path=dotenv_path)
    if not api_key:
        raise RuntimeError(".env에서 OPENAI_API_KEY를 찾을 수 없습니다.")

    model = model or get_openai_model(dotenv_path=dotenv_path)
    body = json.dumps({"model": model, "input": prompt}).encode("utf-8")
    request = urllib.request.Request(
        DEFAULT_OPENAI_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OpenAI API 호출에 실패했습니다: {exc}") from exc

    if not data:
        raise RuntimeError("OpenAI 응답이 비어 있습니다.")

    if isinstance(data, dict):
        if output_text := data.get("output_text"):
            return output_text
        if output := data.get("output"):
            if isinstance(output, list) and output:
                text_parts = []
                for item in output:
                    if isinstance(item, dict) and "content" in item:
                        content = item["content"]
                        if isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and part.get("type") == "output_text":
                                    text_parts.append(part.get("text", ""))
                        elif isinstance(content, str):
                            text_parts.append(content)
                if text_parts:
                    return "\n".join(text_parts)
        if choices := data.get("choices"):
            if isinstance(choices, list) and choices:
                choice = choices[0]
                if message := choice.get("message"):
                    return message.get("content", "")
                return choice.get("text", "")

    raise RuntimeError("OpenAI 응답에서 텍스트를 추출할 수 없습니다.")


def extract_rate_from_openai_text(text: str) -> float:
    """OpenAI 응답에서 숫자 환율을 추출합니다."""
    text = text.strip()
    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and "rate" in payload:
            return float(payload["rate"])
    except ValueError:
        pass

    cleaned = text.replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if match:
        return float(match.group(1))

    raise ValueError("OpenAI 응답에서 환율 숫자를 찾을 수 없습니다.")


def fetch_hana_bank_rate_via_openai(
    from_currency: str = "USD",
    to_currency: str = "KRW",
    model: Optional[str] = None,
    dotenv_path: Optional[str] = None,
) -> float:
    """OpenAI API를 통해 하나은행 매매기준율을 조회합니다."""
    prompt = (
        "하나은행 매매기준율을 실시간으로 조회하여 USD/KRW 환율을 JSON으로 반환하세요. "
        "결과는 다음 형식으로만 작성하십시오: {\"rate\": 숫자, \"currency_pair\": \"USD/KRW\", \"source\": \"하나은행\"}. "
        "실시간 조회가 불가능하면 error 필드를 포함한 JSON을 반환하세요."
    )
    response_text = call_openai_api(prompt, model=model, dotenv_path=dotenv_path)
    return extract_rate_from_openai_text(response_text)


def convert_currency_using_hana_bank(
    amount: float,
    from_currency: str,
    to_currency: str,
    model: Optional[str] = None,
    dotenv_path: Optional[str] = None,
) -> float:
    """하나은행 매매기준율로 통화를 변환합니다. 현재는 USD/KRW만 지원합니다."""
    from_code = normalize_currency_code(from_currency)
    to_code = normalize_currency_code(to_currency)

    if {from_code, to_code} != {"USD", "KRW"}:
        raise ValueError("현재 하나은행 환율 변환은 USD/KRW 간 변환만 지원합니다.")

    rate = fetch_hana_bank_rate_via_openai(from_currency=from_currency, to_currency=to_currency, model=model, dotenv_path=dotenv_path)
    if from_code == "USD" and to_code == "KRW":
        return amount * rate
    return amount / rate


def fetch_exchange_rates_from_api(
    base_currency: str = DEFAULT_BASE_CURRENCY,
    symbols: Optional[str] = None,
    api_url: str = DEFAULT_EXCHANGE_API_URL,
    api_key: Optional[str] = None,
) -> Dict[str, float]:
    """외부 API에서 환율 데이터를 가져옵니다."""
    base = normalize_currency_code(base_currency)
    query = {"base": base}
    if symbols:
        query["symbols"] = symbols
    endpoint = f"{api_url}?{urllib.parse.urlencode(query)}"

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        # 일부 OpenAPI는 query parameter 방식으로 API 키를 받기도 합니다.
        if "access_key=" not in api_url and "api_key=" not in api_url:
            endpoint += f"&access_key={urllib.parse.quote(api_key)}"

    request = urllib.request.Request(endpoint, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)

        if not data.get("success", True):
            raise ValueError("환율 API 응답에 실패했습니다.")

        rates = data.get("rates")
        if not isinstance(rates, dict):
            raise ValueError("환율 API 응답 형식이 올바르지 않습니다.")

        return {normalize_currency_code(k): float(v) for k, v in rates.items()}
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"환율 API를 가져오는 데 실패했습니다: {exc}") from exc


def get_exchange_rates(
    base_currency: str = DEFAULT_BASE_CURRENCY,
    symbols: Optional[str] = None,
    use_api: bool = True,
    api_url: Optional[str] = None,
    api_key_env: str = DEFAULT_EXCHANGE_API_KEY_ENV,
    dotenv_path: Optional[str] = None,
) -> Dict[str, float]:
    """환율 데이터를 반환합니다. API 요청 실패 시 기본 데이터를 대체로 사용합니다."""
    if use_api:
        api_url = api_url or os.getenv(DEFAULT_EXCHANGE_API_URL_ENV, DEFAULT_EXCHANGE_API_URL)
        api_key = get_api_key_from_dotenv(api_key_env=api_key_env, dotenv_path=dotenv_path)
        try:
            rates = fetch_exchange_rates_from_api(
                base_currency=base_currency,
                symbols=symbols,
                api_url=api_url,
                api_key=api_key,
            )
            rates[normalize_currency_code(base_currency)] = 1.0
            return rates
        except RuntimeError:
            pass

    return DEFAULT_EXCHANGE_RATES


def get_exchange_rate(from_currency: str, to_currency: str, rates: Optional[Dict[str, float]] = None) -> float:
    """기준 환율 데이터를 사용해 from_currency에서 to_currency로 변환하는 환율을 계산합니다."""
    if rates is None:
        rates = DEFAULT_EXCHANGE_RATES

    from_code = normalize_currency_code(from_currency)
    to_code = normalize_currency_code(to_currency)

    if from_code not in rates:
        raise ValueError(f"지원하지 않는 통화: {from_currency}")
    if to_code not in rates:
        raise ValueError(f"지원하지 않는 통화: {to_currency}")

    from_rate = rates[from_code]
    to_rate = rates[to_code]

    # base_currency 기준 환율을 사용하므로, from_currency -> base -> to_currency 변환
    return from_rate / to_rate


def convert_currency(amount: float, from_currency: str, to_currency: str, rates: Optional[Dict[str, float]] = None) -> float:
    """금액을 하나의 통화에서 다른 통화로 변환합니다."""
    rate = get_exchange_rate(from_currency, to_currency, rates)
    return amount * rate


def format_currency(amount: float, currency: str) -> str:
    """통화 코드에 따라 보기 좋은 문자열로 변환합니다."""
    code = normalize_currency_code(currency)
    if code == "KRW":
        return f"{amount:,.0f}원"
    if code == "JPY":
        return f"{amount:,.0f}엔"
    if code == "USD":
        return f"${amount:,.2f}"
    if code == "EUR":
        return f"€{amount:,.2f}"
    if code == "THB":
        return f"฿{amount:,.2f}"
    if code == "CNY":
        return f"¥{amount:,.2f}"
    if code == "SGD":
        return f"S${amount:,.2f}"
    return f"{amount:,.2f} {code}"


@dataclass
class ExpenseSummary:
    total: float
    per_person: Optional[float]
    budget_gap: Optional[float]
    budget_message: str


def calculate_total_expenses(expense_items: Dict[str, float]) -> float:
    """여행 경비 항목을 모두 합산합니다."""
    return sum(expense_items.values())


def calculate_per_person(total_expense: float, persons: int) -> float:
    """총 경비를 인원 수로 나누어 1인당 비용을 계산합니다."""
    if persons <= 0:
        raise ValueError("인원 수는 1 이상이어야 합니다.")
    return total_expense / persons


def assess_budget(total_expense: float, budget: Optional[float] = None) -> Tuple[Optional[float], str]:
    """예산 적합성을 간단히 판단하고 메시지를 반환합니다."""
    if budget is None:
        return None, "예산을 입력하지 않았습니다. 필요한 총비용을 확인하세요."

    gap = budget - total_expense
    if gap >= 0:
        return gap, f"입력한 예산으로 충분합니다. 남은 예산은 약 {gap:,.0f}원입니다."
    return gap, f"예산이 부족합니다. 추가로 약 {abs(gap):,.0f}원이 필요합니다."


def build_expense_report(
    expense_items: Dict[str, float],
    persons: int = 1,
    budget: Optional[float] = None,
    currency: str = "KRW",
) -> ExpenseSummary:
    """경비 보고서를 생성합니다."""
    total = calculate_total_expenses(expense_items)
    per_person = calculate_per_person(total, persons) if persons > 0 else None
    budget_gap, budget_message = assess_budget(total, budget)
    return ExpenseSummary(total=total, per_person=per_person, budget_gap=budget_gap, budget_message=budget_message)


def sample_currency_conversion(use_api: bool = True, dotenv_path: Optional[str] = None) -> str:
    """샘플 환율 변환 결과를 문자열로 반환합니다."""
    amount = 100
    from_currency = "USD"
    to_currency = "KRW"
    rates = get_exchange_rates(
        base_currency="KRW",
        symbols=",".join(sorted(SUPPORTED_CURRENCIES)),
        use_api=use_api,
        dotenv_path=dotenv_path,
    )
    converted = convert_currency(amount, from_currency, to_currency, rates=rates)
    source = "API" if use_api else "기본 데이터"
    return f"{amount} {from_currency}는 약 {format_currency(converted, to_currency)}입니다. (환율 출처: {source})"


def sample_expense_summary() -> str:
    """샘플 경비 계산 예제를 문자열로 반환합니다."""
    expenses = {
        "숙박비": 400_000,
        "식비": 200_000,
        "교통비": 100_000,
        "관광비": 150_000,
        "쇼핑비": 80_000,
    }
    summary = build_expense_report(expenses, persons=4, budget=1_000_000)
    per_person_str = f"1인당 약 {format_currency(summary.per_person, 'KRW')}입니다." if summary.per_person is not None else "인원 정보를 확인하세요."
    return (
        f"총 예상 경비는 {format_currency(summary.total, 'KRW')}입니다. "
        f"{per_person_str} {summary.budget_message}"
    )


if __name__ == "__main__":
    load_dotenv()
    print("[TravelMate 환율 / 경비 계산 도구 샘플]")
    print(sample_currency_conversion(use_api=True, dotenv_path=".env"))
    print(sample_expense_summary())
