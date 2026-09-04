import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("AI_API_KEY")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

COVER_LETTER_TEMPLATE = """Здравствуйте! Меня зовут Венера Михайлова. Я — project manager с 3-летним опытом управления кросс-функциональными проектами. Веду полный цикл проектов: от инициации до сдачи результата, работаю с бюджетами, сроками и командами.

Почему я подхожу для этой позиции:

- Реализовала проектный портфель из 40 мероприятий, выполнив 200% от планового показателя.
- Самостоятельно разработала и запустила проект совместно с СИБУР ПолиЛаб (от формирования концепции и согласования с партнером до реализации и запуска).
- Масштабировала проектные инициативы до федерального уровня: проекты были реализованы в 89 регионах России.
- Выстраивала взаимодействие с партнерами уровня СИБУР, Сбер, МТС, Wildberries, Аэрофлот и Московский метрополитен.
- Формирую ТЗ и PRD, User Stories и acceptance criteria для кросс-функциональных команд; приоритизирую backlog по RICE / ICE / MoSCoW.
- Координирую работу команд разработки, дизайна и медиа, контролирую сроки, бюджет, риски и итоговую реализацию.
- Работаю в Jira, Confluence и Trello; использую SQL, Excel / Google Sheets; имею базовую техническую экспертизу в Python, MySQL и Linux / Bash.
- Английский и испанский — C1.

Ваша вакансия заинтересовала меня возможностью применить этот опыт в IT-среде и работать над задачами, где важны самостоятельность, системность и доведение продукта или проекта до результата. Буду рада обсудить детали на собеседовании."""


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
