from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


DEFAULT_MODEL = "gpt-4o-mini"


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인해 주세요.")
    return OpenAI(api_key=api_key)


def _get_model() -> str:
    return os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def _extract_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def ask_openai(
    tool_name: str,
    user_input: str,
    instructions: str = "",
    use_web_search: bool = False,
    max_output_tokens: int = 1200,
) -> str:
    """OpenAI Responses API를 호출해 도구 응답 텍스트를 반환합니다."""
    client = _get_client()
    request: dict[str, Any] = {
        "model": _get_model(),
        "instructions": instructions,
        "input": user_input,
        "max_output_tokens": max_output_tokens,
    }

    if use_web_search:
        request["tools"] = [{"type": "web_search_preview"}]

    try:
        response = client.responses.create(**request)
        answer = _extract_text(response)
        if not answer:
            return f"{tool_name}이 응답을 생성했지만 텍스트 결과가 비어 있습니다."
        return answer
    except Exception as error:
        return f"{tool_name} 실행 중 오류가 발생했습니다: {error}"
