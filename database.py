import os
import mysql.connector
from dotenv import load_dotenv
from fetch_vacancies import extract_snippet

load_dotenv()


def get_connection():
    """Открывает соединение с MySQL, используя данные из .env"""
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
    )


def filter_new_vacancies(vacancies: list[dict], format_salary_fn) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    new_ones = []

    for v in vacancies:
        try:
            hh_id = v["vacancyId"]

            cursor.execute("SELECT id FROM vacancies WHERE hh_id = %s", (hh_id,))
            if cursor.fetchone():
                continue  # уже видели раньше

            title = v.get("name", "Без названия")
    
            snippet_text = extract_snippet(v)
            is_accredited = v.get("company", {}).get("accreditedITEmployer", False)
            company_name = v.get("company", {}).get("name", "Компания не указана")
            url = v.get("links", {}).get("desktop", "")

            cursor.execute("""
                INSERT INTO vacancies (hh_id, title, company, salary, experience, published_at, responses_count, url, snippet, accredited_it)

                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                hh_id,
                title,
                company_name,
                format_salary_fn(v.get("compensation")),
                v.get("workExperience"),
                v.get("publicationTime", {}).get("$", "")[:10],
                v.get("responsesCount"),
                url,
                snippet_text,
                is_accredited,
            ))
            new_vacancy_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO applications (vacancy_id, status) VALUES (%s, 'new')",
                (new_vacancy_id,),
            )

            v["_db_id"] = new_vacancy_id
            new_ones.append(v)

        except Exception as e:
            print(f"Пропускаю вакансию из-за ошибки: {e}")
            continue  # одна плохая запись не должна останавливать весь пакет

    conn.commit()
    cursor.close()
    conn.close()
    return new_ones

def update_status(vacancy_db_id: int, status: str):
    """Меняет статус в applications для вакансии с данным внутренним id (не hh_id!)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE applications SET status = %s WHERE vacancy_id = %s",
        (status, vacancy_db_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_recent_applications(limit: int = 15) -> list[dict]:
    """Возвращает последние вакансии вместе с их текущим статусом."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT v.title, v.url, a.status, a.updated_at
        FROM applications a
        JOIN vacancies v ON v.id = a.vacancy_id
        ORDER BY a.updated_at DESC
        LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
    
def get_vacancy(vacancy_db_id: int) -> dict | None:
    """Достаёт сохранённые данные вакансии по внутреннему id — нужно для генерации письма."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vacancies WHERE id = %s", (vacancy_db_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def save_cover_letter(vacancy_db_id: int, letter: str, status: str = "letter_ready"):
    """Сохраняет текст сгенерированного письма и обновляет статус одновременно."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE applications SET status = %s, cover_letter = %s WHERE vacancy_id = %s",
        (status, letter, vacancy_db_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # Простая проверка: если это выполнится без ошибок — .env настроен верно
    # и Python реально может достучаться до MySQL
    conn = get_connection()
    print("Соединение с базой установлено успешно.")
    conn.close()