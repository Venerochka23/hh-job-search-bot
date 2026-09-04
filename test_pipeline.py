from fetch_vacancies import search_vacancies, format_salary
from database import filter_new_vacancies

if __name__ == "__main__":
    vacancies, _ = search_vacancies()
    print(f"Найдено всего (из hh.ru, до проверки на дубли): {len(vacancies)}")

    new_ones = filter_new_vacancies(vacancies, format_salary)
    print(f"Новых (не встречались раньше): {len(new_ones)}")
    print("---")

    for v in new_ones:
        print(v["name"], "|", v["links"]["desktop"])