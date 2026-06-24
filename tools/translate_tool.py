"""
TravelMate translation tool.

초기 버전은 외부 API 없이 자주 쓰는 여행 문장 샘플을 반환한다.
나중에 Papago, Google Translate, DeepL 같은 번역 API 호출로 교체할 수 있다.
"""

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func


LANGUAGE_ALIASES = {
    "영어": "english",
    "english": "english",
    "태국어": "thai",
    "thai": "thai",
    "베트남어": "vietnamese",
    "vietnamese": "vietnamese",
    "한국어": "korean",
    "korean": "korean",
}


LANGUAGE_LABELS = {
    "english": "영어",
    "thai": "태국어",
    "vietnamese": "베트남어",
    "korean": "한국어",
}


TRANSLATION_SAMPLES = {
    ("화장실이 어디에 있나요", "thai"): {
        "translated_text": "ห้องน้ำอยู่ที่ไหน?",
        "pronunciation": "홍남 유 티나이?",
        "meaning": "화장실은 어디에 있나요?",
        "situation": "길 찾기, 식당, 관광지에서 사용할 수 있는 표현",
    },
    ("계산서 주세요", "english"): {
        "translated_text": "Could I have the bill, please?",
        "pronunciation": "쿠드 아이 해브 더 빌, 플리즈?",
        "meaning": "계산서 주세요.",
        "situation": "식당이나 카페에서 계산을 요청할 때 사용하는 표현",
    },
    ("계산서 주세요", "vietnamese"): {
        "translated_text": "Cho tôi xin hóa đơn.",
        "pronunciation": "쪼 또이 씬 화 돈",
        "meaning": "계산서 주세요.",
        "situation": "식당이나 카페에서 계산을 요청할 때 사용하는 표현",
    },
    ("안녕하세요", "thai"): {
        "translated_text": "สวัสดี",
        "pronunciation": "싸왓디",
        "meaning": "안녕하세요.",
        "situation": "인사할 때 사용하는 기본 표현",
    },
    ("안녕하세요", "vietnamese"): {
        "translated_text": "Xin chào",
        "pronunciation": "씬 짜오",
        "meaning": "안녕하세요.",
        "situation": "인사할 때 사용하는 기본 표현",
    },
}


def normalize_language(language):
    """
    사용자가 입력한 언어명을 내부 코드로 변환한다.
    """
    if not language:
        return "english"

    return LANGUAGE_ALIASES.get(language.strip().lower(), language.strip().lower())


def clean_text(text):
    """
    번역할 문장에서 요청 표현을 제거한다.
    """
    cleaned_text = text.strip()

    remove_words = [
        "번역해줘",
        "번역해 주세요",
        "번역",
        "영어로",
        "태국어로",
        "베트남어로",
        "한국어로",
        ".",
        "?",
        "!",
    ]

    for word in remove_words:
        cleaned_text = cleaned_text.replace(word, "")

    cleaned_text = cleaned_text.strip()
    if cleaned_text.endswith(("을", "를")):
        cleaned_text = cleaned_text[:-1]

    return cleaned_text.strip()


def format_translation_result(target_language, result):
    """
    번역 결과를 챗봇 답변 형식으로 정리한다.
    """
    language_label = LANGUAGE_LABELS.get(target_language, target_language)

    response = [
        f"{language_label} 번역:",
        result["translated_text"],
        "",
        "읽는 법:",
        result.get("pronunciation", "발음 정보가 없습니다."),
        "",
        "뜻:",
        result.get("meaning", result["translated_text"]),
    ]

    if result.get("situation"):
        response.extend(["", "사용 상황:", result["situation"]])

    return "\n".join(response)


def _translate_impl(text, target_language="영어"):
    """
    사용자가 입력한 여행 문장을 원하는 언어로 번역한다.
    """
    if not text or not text.strip():
        return "번역할 문장을 입력해 주세요."

    normalized_language = normalize_language(target_language)
    source_text = clean_text(text)
    sample_key = (source_text, normalized_language)

    if sample_key in TRANSLATION_SAMPLES:
        return format_translation_result(
            normalized_language,
            TRANSLATION_SAMPLES[sample_key],
        )

    language_label = LANGUAGE_LABELS.get(normalized_language, target_language)

    return (
        f"{language_label} 번역:\n"
        "현재 샘플 데이터에 없는 문장입니다.\n\n"
        "안내:\n"
        "초기 버전에서는 자주 쓰는 여행 표현만 번역할 수 있습니다.\n"
        "나중에 번역 API를 연결하면 입력한 문장을 실시간으로 번역할 수 있습니다."
    )


@tool
def translate(text, target_language="영어"):
    """
    사용자가 입력한 여행 문장을 원하는 언어로 번역한다.

    Args:
        text: 번역할 문장
        target_language: 번역할 언어. 예: 영어, 태국어, 베트남어, 한국어

    Returns:
        번역 문장, 읽는 법, 뜻, 사용 상황을 포함한 문자열
    """
    return _translate_impl(text, target_language)


def translate_text(text, target_language):
    """
    문서 예시와 호환되는 일반 함수이다.
    """
    return _translate_impl(text, target_language)
