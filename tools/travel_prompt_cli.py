import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.travel_recommend_tool import generate_travel_recommendation


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def parse_travel_prompt(user_prompt):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "사용자의 한국어 여행 요청을 아래 JSON 형식으로만 변환하세요. "
                    "모르는 값은 자연스러운 기본값으로 채우세요.\n"
                    "{"
                    '"destination": "도시명", '
                    '"duration": "2박 3일", '
                    '"people_count": 2, '
                    '"total_budget": 100, '
                    '"selected_themes": ["맛집"], '
                    '"companion_type": "친구"'
                    "}"
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def main():
    print("여행 요청을 자연어로 입력하세요.")
    print("예: 방콕으로 친구랑 2박 3일, 예산 120만 원, 맛집이랑 야경 위주로 추천해줘")
    print()

    user_prompt = input("> ").strip()
    if not user_prompt:
        print("입력된 요청이 없습니다.")
        return

    try:
        conditions = parse_travel_prompt(user_prompt)
        print("\n[추출된 여행 조건]")
        print(json.dumps(conditions, ensure_ascii=False, indent=2))
        print("\n[추천 결과]\n")

        result = generate_travel_recommendation(
            destination=conditions.get("destination", ""),
            duration=conditions.get("duration", "2박 3일"),
            people_count=int(conditions.get("people_count", 1)),
            total_budget=int(conditions.get("total_budget", 100)),
            selected_themes=conditions.get("selected_themes", []),
            companion_type=conditions.get("companion_type", "자유 여행"),
        )
        print(result)
    except Exception as error:
        print(f"테스트 중 오류가 발생했습니다: {error}")


if __name__ == "__main__":
    main()
