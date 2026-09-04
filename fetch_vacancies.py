import requests
import json
import html
import re
from datetime import datetime, timezone, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

STATE_PATTERN = re.compile(
    r'<template[^>]*id="HH-Lux-InitialState"[^>]*>(.*?)</template>',
    re.S,
)

JOB_TITLES_QUERY = (
    '("project manager" OR "product manager" OR '
    '"руководитель проектов" OR "менеджер проектов" OR "менеджер продукта")'
)

EXCLUDED_KEYWORDS = "строительство строительный фасад ВОЛС СКС нефтегаз энергетик слаботочн конвейер химия пищевой промышленность"

EXPERIENCE_LEVELS = ["noExperience", "between1And3", "between3And6"]
EXPERIENCE_LABELS = {
    "noExperience": "без опыта",
    "between1And3": "1–3 года",
    "between3And6": "3–6 лет",
    "moreThan6": "более 6 лет",
}

MAX_RESPONSES = 250
MIN_SALARY = 100_000
MOSCOW_TZ = timezone(timedelta(hours=3))


def fetch_search_page(params: dict) -> dict:
    response = requests.get(
        "https://hh.ru/search/vacancy",
        headers=HEADERS,
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    match = STATE_PATTERN.search(response.text)
    if not match:
        raise RuntimeError(
            "Блок HH-Lux-InitialState не найден — возможно, hh.ru показал капчу"
        )
    return json.loads(html.unescape(match.group(1)))


def search_vacancies() -> tuple[list[dict], list[dict]]:
    """Собирает вакансии из двух запросов: Москва (офис/гибрид) и удалёнка по всей стране."""
    base_params = {
        "text": JOB_TITLES_QUERY,
        "search_field": "name",
        "experience": EXPERIENCE_LEVELS,
        "salary": MIN_SALARY,
        "enable_snippets": True,
        "currency": "RUR",
        "search_period": 1,
        "order_by": "publication_time",
        "excluded_text": EXCLUDED_KEYWORDS,
    }

    search_moscow = {**base_params, "area": 1}
    search_remote = {**base_params, "schedule": "remote"}

    all_vacancies = {}
    criteria_samples = []

    for params in (search_moscow, search_remote):
        data = fetch_search_page(params)
        result = data["vacancySearchResult"]
        criteria_samples.append(result.get("criteria"))
        for v in result["vacancies"]:
            all_vacancies[v["vacancyId"]] = v

    return list(all_vacancies.values()), criteria_samples


def format_salary(comp: dict | None) -> str:
    if not comp:
        return "не указана"
    frm = comp.get("from")
    to = comp.get("to")
    currency = comp.get("currencyCode", "")
    if frm and to:
        return f"{frm}–{to} {currency}"
    if frm:
        return f"от {frm} {currency}"
    if to:
        return f"до {to} {currency}"
    return "не указана"


def is_recently_published(v: dict, hours: int = 24) -> bool:
    """Публикация должна быть не старше указанного количества часов по московскому времени."""
    pub = v.get("publicationTime", {}).get("$")
    if not pub:
        return False

    try:
        pub_dt = datetime.fromisoformat(pub)
    except ValueError:
        return False

    now = datetime.now(MOSCOW_TZ)
    return now - pub_dt <= timedelta(hours=hours)


def passes_filters(v: dict) -> bool:
    comp = v.get("compensation")
    if comp:
        salary_value = comp.get("from") or comp.get("to")
        if salary_value is not None and salary_value < MIN_SALARY:
            return False

    responses = v.get("responsesCount")
    if responses is not None and responses > MAX_RESPONSES:
        return False

    if not is_recently_published(v, hours=24):
        return False

    return True

    
def extract_snippet(v: dict) -> str:
    """Забирает краткое описание вакансии (требования + обязанности), очищает от HTML-тегов."""
    snippet = v.get("snippet", {}) or {}
    requirement = snippet.get("requirement") or ""
    responsibility = snippet.get("responsibility") or ""

    combined = f"{responsibility} {requirement}".strip()
    return re.sub(r"<[^>]+>", "", combined)  # hh.ru подсвечивает совпадения тегами, убираем их

if __name__ == "__main__":
    vacancies, _ = search_vacancies()

    filtered = [v for v in vacancies if passes_filters(v)]

    print(f"Всего найдено (до фильтра): {len(vacancies)}")
    dates_seen = sorted({v.get("publicationTime", {}).get("$", "")[:10] for v in vacancies}, reverse=True)
    print("Даты публикаций среди найденного (без фильтра):", dates_seen)
    print(f"Прошло фильтр (зарплата/отклики/за последние 24 часа): {len(filtered)}")
    print("---")

    for v in filtered:
        comp = v.get("compensation")
        exp_label = EXPERIENCE_LABELS.get(v.get("workExperience"), "не указан")
        pub_date = v.get("publicationTime", {}).get("$", "")[:10]

        print(f"{v['name']}")
        print(f"Компания: {v['company']['name']}")
        print(f"Зарплата: {format_salary(comp)}")
        print(f"Опыт: {exp_label}")
        print(f"Опубликовано: {pub_date}")
        print(f"Откликов: {v.get('responsesCount')}")
        print(v["links"]["desktop"])
        print("---")
