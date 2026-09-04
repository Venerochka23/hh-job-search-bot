# hh-job-search-bot
Бот в телеграм для автоматизации поиска вакансий на hh.ru: находит вакансии по заданным фильтрам, отправляет вакансии в чат ("Откликнуться"/"Пропустить"), ИИ генерирует сопроводительное письмо по заранее переданному шаблону для тех вакансий, на которые вы решаете откликнуться. 

Стек: 
- Python 3.12
- `python-telegram-bot` (async, JobQueue для планировщика)
- MySQL (`mysql-connector-python`)
- Google Gemini API (Interactions API)
- `requests` 
- Управление через systemd
- VPS, Ubuntu (любая локация, кроме РФ)

Архитектура: 
| Файл | Назначение |
|---|---|
| `fetch_vacancies.py` | Поиск и парсинг вакансий с hh.ru, фильтрация по критериям |
| `database.py` | Работа с MySQL: дедупликация, хранение вакансий и статусов откликов |
| `ai_letter.py` | Генерация сопроводительного письма через Gemini API |
| `bot.py` | Telegram-бот: меню, обработка кнопок, планировщик рассылки |

Технические решения: 
- **Обход закрытия публичного API**: с апреля 2026 hh.ru закрыл неавторизованный доступ к `GET /vacancies`. Решение — запрос к обычной странице поиска (`hh.ru/search/vacancy`) с разбором данных, встроенных в HTML-ответ.
- **Отклик реализован полуавтоматически** — бот готовит текст письма и присылает его в Telegram, но не отправляет отклик от имени пользователя автоматически (так как это может привести к блокировке аккаунта). 
- **Устойчивость к неполным данным**: обработка вакансий обёрнута в try/except по каждой записи отдельно.

.env_example:
TELEGRAM_BOT_TOKEN=Токен вашего бота
AI_API_KEY=ваш личный ключ для Gemini API
MYSQL_HOST=localhost
MYSQL_USER=имя_пользователя_базы_данных
MYSQL_PASSWORD=пароль_для_базы_данных
MYSQL_DB=имя_базы_данных
TELEGRAM_CHAT_ID=ID_вашего_чата

Установка и запуск: 
```bash
git clone <repo_url>
cd hh_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполнить реальными значениями
python3 database.py   # проверка соединения с БД (таблицы создаются вручную, см. schema.sql)
python3 bot.py
```

<img width="744" height="870" alt="Снимок экрана — 2026-09-04 в 14 42 22" src="https://github.com/user-attachments/assets/bcafb42d-dfa4-476a-ae22-73b4add6093f" />
<img width="744" height="870" alt="Снимок экрана — 2026-09-04 в 14 41 39" src="https://github.com/user-attachments/assets/e3482ce6-ddae-4ea8-87c3-7aff35d6fe9e" />

