"""OpenAI 기반 TravelMate 번역 Tool.

이 파일은 LangChain의 @tool 형태와 app.py의 일반 함수 호출을 모두 지원한다.
.env에 OPENAI_API_KEY가 없으면 번역 기능은 실행되지 않는다.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.translate_tool import clean_text, format_translation_result, normalize_language


load_dotenv(override=True)

OPENAI_TRANSLATION_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4o-mini")


def get_openai_client() -> OpenAI:
    """OPENAI_API_KEY가 없으면 명확히 실패시킨다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(".env에 OPENAI_API_KEY를 입력해야 번역 API를 사용할 수 있습니다.")
    return OpenAI(api_key=api_key)


def request_translation(text: str, target_language: str) -> dict:
    """gpt-4o-mini에 번역을 요청하고 JSON 결과를 반환한다."""
    response = get_openai_client().chat.completions.create(
        model=OPENAI_TRANSLATION_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 동남아 여행 회화 번역 도우미입니다. "
                    "반드시 JSON만 반환하세요. "
                    "필드: translated_text, pronunciation, meaning, situation. "
                    "pronunciation은 반드시 한국어 한글 발음 표기로 작성하세요. "
                    "meaning과 situation도 반드시 한국어로 작성하세요. "
                    "IPA, 로마자 발음, 영어 설명은 사용하지 마세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"목표 언어: {target_language}\n"
                    f"번역할 문장: {text}\n"
                    "여행자가 식당, 숙소, 교통, 길 찾기 상황에서 바로 쓸 수 있게 번역해 주세요."
                ),
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI 번역 응답이 비어 있습니다.")
    return json.loads(content)


def translate_text(text: str, target_language: str = "영어") -> str:
    """app.py에서 호출하는 번역 함수."""
    if not text or not text.strip():
        return "번역할 문장을 입력해 주세요."

    source_text = clean_text(text)
    normalized_language = normalize_language(target_language)
    result = request_translation(source_text, normalized_language)

    return format_translation_result(
        normalized_language,
        {
            "translated_text": result.get("translated_text", "").strip(),
            "pronunciation": result.get("pronunciation", "발음 정보가 없습니다.").strip(),
            "meaning": result.get("meaning", source_text).strip(),
            "situation": result.get("situation", "여행 중 바로 사용할 수 있는 표현입니다.").strip(),
        },
    )


@tool
def translate(text: str, target_language: str = "영어") -> str:
    """여행 문장을 target_language로 번역한다."""
    return translate_text(text, target_language)


if __name__ == "__main__":
    print(translate_text("계산서 주세요", "영어"))
