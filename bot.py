import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

from datetime import datetime
from fetch_vacancies import format_salary, EXPERIENCE_LABELS, search_vacancies, passes_filters, MOSCOW_TZ
from database import update_status, get_recent_applications, filter_new_vacancies, get_vacancy, save_cover_letter
from ai_letter import generate_cover_letter

EXPERIENCE_PRIORITY = {
    "between1And3": 0,
    "between3And6": 1,
    "noExperience": 2,
} 

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Одноразовая команда — только чтобы узнать свой chat_id."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Твой chat_id: {chat_id}\n\nДобавь строку в .env:\nTELEGRAM_CHAT_ID={chat_id}"
    )


def build_vacancy_message(v: dict) -> str:
    comp = v.get("compensation")
    exp_label = EXPERIENCE_LABELS.get(v.get("workExperience"), "не указан")
    pub_date = v.get("publicationTime", {}).get("$", "")[:10]
    title = v.get("name", "Без названия")
    company_name = v.get("company", {}).get("name", "Компания не указана")
    url = v.get("links", {}).get("desktop", "")
    accredited_tag = "\n🏢 Аккредитованная IT-компания" if v.get("company", {}).get("accreditedITEmployer") else ""

    return (
        f"{title}\n"
        f"Компания: {company_name}\n"
        f"Зарплата: {format_salary(comp)}\n"
        f"Опыт: {exp_label}\n"
        f"Опубликовано: {pub_date}\n"
        f"Откликов: {v.get('responsesCount')}\n"
        f"Аккредитация: {accredited_tag}\n" 
        f"{url}"
    )

def build_vacancy_keyboard(vacancy_db_id: int) -> InlineKeyboardMarkup:
    buttons = [[
        InlineKeyboardButton("Откликнуться", callback_data=f"apply:{vacancy_db_id}"),
        InlineKeyboardButton("Пропустить", callback_data=f"skip:{vacancy_db_id}"),
    ]]
    return InlineKeyboardMarkup(buttons)

STATUS_LABELS = {
    "new": "Новая",
    "skipped": "Пропущено",
    "pending_letter": "Ожидает письма",
    "responded": "Отклик отправлен",
    "waiting": "Ожидаем ответ",
    "rejected": "Отказ",
    "invited": "Приглашение",
    "letter_ready": "Письмо готово, жду отклика на сайте",
}


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    apps = get_recent_applications(limit=15)
    if not apps:
        await update.message.reply_text("Пока нет ни одной записи в базе.")
        return

    lines = []
    for a in apps:
        label = STATUS_LABELS.get(a["status"], a["status"])
        lines.append(f"{label} — {a['title']}\n{a['url']}")

    await update.message.reply_text("\n\n".join(lines))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Доступные команды:\n"
        "/start — приветствие\n"
        "/status — последние вакансии и их статусы\n"
        "/help — это сообщение"
    )
    await update.message.reply_text(text)
DAY_START_HOUR = 8   # раньше этого часа (по Москве) не беспокоим
DAY_END_HOUR = 22    # после этого часа тоже не беспокоим


async def send_new_vacancies_job(context: ContextTypes.DEFAULT_TYPE):
    current_hour = datetime.now(MOSCOW_TZ).hour
    if current_hour < DAY_START_HOUR or current_hour >= DAY_END_HOUR:
        return  # ночь — тихо ничего не делаем

    vacancies, _ = search_vacancies()
    filtered = [v for v in vacancies if passes_filters(v)]
    new_ones = filter_new_vacancies(filtered, format_salary)
    new_ones.sort(key=lambda v: EXPERIENCE_PRIORITY.get(v.get("workExperience"), 99))
    for v in new_ones:
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=build_vacancy_message(v),
            reply_markup=build_vacancy_keyboard(v["_db_id"]),
        )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # обязательно — иначе кнопка "крутится" в телефоне у пользователя

    action, db_id_str = query.data.split(":")
    db_id = int(db_id_str)

    if action == "skip":
        update_status(db_id, "skipped")
        await query.edit_message_reply_markup(reply_markup=None)  # убирает кнопки из уже отправленного сообщения
        await query.message.reply_text("Пропущено.")

    elif action == "apply":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Генерирую письмо, секунду...")

        vacancy_row = get_vacancy(db_id)
        if not vacancy_row:
            await query.message.reply_text("Не нашла эту вакансию в базе, что-то пошло не так.")
            return

        vacancy_for_prompt = {
            "name": vacancy_row["title"],
            "company": {"name": vacancy_row["company"]},
            "description": vacancy_row.get("snippet", ""),
        }
        letter = generate_cover_letter(vacancy_for_prompt)

        save_cover_letter(db_id, letter)

        await query.message.reply_text(letter)
        await query.message.reply_text(f"Вставь это на странице отклика:\n{vacancy_row['url']}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.job_queue.run_repeating(send_new_vacancies_job, interval=5400, first=15)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_button))
    print("Бот запущен, слушает сообщения...")
    app.run_polling()


if __name__ == "__main__":
    main()
