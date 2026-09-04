import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

from fetch_vacancies import search_vacancies, passes_filters, format_salary
from database import filter_new_vacancies
from bot import build_vacancy_message, build_vacancy_keyboard

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def main():
    bot = Bot(token=BOT_TOKEN)

    vacancies, _ = search_vacancies()
    filtered = [v for v in vacancies if passes_filters(v)]
    new_ones = filter_new_vacancies(filtered, format_salary)

    print(f"Новых вакансий: {len(new_ones)}")

    for v in new_ones[:3]:  # только первые 3 — чтобы не засыпать чат сразу
        await bot.send_message(
            chat_id=CHAT_ID,
            text=build_vacancy_message(v),
            reply_markup=build_vacancy_keyboard(v["_db_id"]),
        )

    await bot.close()


if __name__ == "__main__":
    asyncio.run(main())