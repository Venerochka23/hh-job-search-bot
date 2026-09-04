import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("AI_API_KEY")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

COVER_LETTER_TEMPLATE = """Ваш шаблон, на который будет опираться ИИ при генерации писем."""


def build_prompt(vacancy: dict) -> str:
    description = (vacancy.get("description") or "").strip()
    description_block = (
        f"\nЧто известно о требованиях/обязанностях по этой вакансии:\n{description}\n"
        if description else ""
    )

    return f"""Ты помогаешь адаптировать сопроводительное письмо под конкретную вакансию.

Вот исходное письмо-шаблон пользователя (стиль и факты сохранять как есть, ничего не выдумывать):

{COVER_LETTER_TEMPLATE}

Вакансия, под которую нужно адаптировать письмо:
Должность: {vacancy['name']}
Компания: {vacancy['company']['name']}
{description_block}
Задача: адаптируй письмо под требования этой конкретной вакансии — если в описании выше есть что-то, что перекликается с опытом из шаблона, сделай на этом акцент. Сохрани все факты и достижения из шаблона без изменений, навыки можно добавить, если они перекликаются с навыками, которые уже есть или их можно очень быстро освоить/получить. Ответь только текстом письма — без пояснений, без markdown, без кавычек вокруг текста."""

def extract_text(response_json: dict) -> str:
    """Новый формат ответа Interactions API — текст лежит в steps, а не в candidates."""
    parts = []
    for step in response_json.get("steps", []):
        if step.get("type") == "model_output":
            for item in step.get("content", []):
                if item.get("type") == "text":
                    parts.append(item["text"])
    return "".join(parts).strip()


def generate_cover_letter(vacancy: dict) -> str:
    prompt = build_prompt(vacancy)

    response = requests.post(
        GEMINI_URL,
        headers={
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json",
            "Api-Revision": "2026-05-20",
        },
        json={"model": "gemini-3.5-flash", "input": prompt},
        timeout=30,
    )
    response.raise_for_status()
    return extract_text(response.json())


if __name__ == "__main__":
    test_vacancy = {
        "name": "Project Manager (IT)",
        "company": {"name": "Тестовая Компания"},
    }
    letter = generate_cover_letter(test_vacancy)
    print(letter)
