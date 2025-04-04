import os
import json
import asyncio
from aiohttp import ClientTimeout
from datetime import datetime
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import FSInputFile
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import gspread
from oauth2client.service_account import ServiceAccountCredentials

API_TOKEN = '7819266341:AAGR7hA37YWnTv6Ptc8sh9HSgFdgxGJNGe8'

# Подключение к Google Таблице
def get_google_sheet(sheet_name="users"):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

# Проверка доступа
def is_user_authorized(username: str) -> bool:
    sheet = get_google_sheet()
    authorized_users = sheet.col_values(1)  # первая колонка (A)
    return username in authorized_users

# Хэндлер команды /start
async def send_welcome(message: types.Message):
    username = f"@{message.from_user.username}"

    await message.answer(f"👋 Привет, {username}! Сейчас проверим доступ...")

    if is_user_authorized(username):
        await message.answer(
            f"✅ Доступ разрешён!\n\n"
            f"🎉 Добро пожаловать, {username}!\n\n"
            "Вы успешно прошли авторизацию. Теперь мы можем начать обучение!\n\n"
            "👇 Сначала — короткое приветственное видео."
        )

        await asyncio.sleep(1.0)

        # 👇 Отправка видео как video
        try:
            print("➡️ Отправляем видео как video")
            video = FSInputFile("welcome.mp4")
            await message.answer_video(
                video,
                caption="🎥 Добро пожаловать в обучение!",
                width=720,
                height=1280,
                supports_streaming=False
            )
        except Exception as e:
            print(f"❌ Ошибка при отправке: {e}")
            await message.answer(f"⚠️ Ошибка при отправке видео: {e}")

        await asyncio.sleep(1.0)

        # 👇 Теперь кнопка "Открыть обучение"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🧠 Начать обучение",
                web_app=WebAppInfo(url="https://bucolic-dasik-c35220.netlify.app/")
            )]
        ])
        await message.answer("📘 Нажми кнопку ниже, чтобы начать обучение:", reply_markup=keyboard)

    else:
        help_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="show_help")]
        ])

        await message.answer(
            "⛔️ Увы, у вас нет доступа. Возможно, вы ещё не добавлены в список участников.\n\n"
            "👇 Нажмите «Помощь», чтобы узнать, что делать дальше.",
            reply_markup=help_keyboard
        )

# Обработчик нажатия на кнопку
async def start_training(callback: types.CallbackQuery):
    await callback.message.answer("📘 Отлично! Обучение началось. Готовься узнавать новое 💡")
    await callback.answer()  # Закрыть "часики" на кнопке

# Кнопка хелп
async def show_help(callback: types.CallbackQuery):
    print("🔔 Обработчик show_help сработал!")
    await callback.message.answer(
        "ℹ️ *Справка:*\n\n"
        "Если вы получили сообщение об отказе в доступе:\n\n"
        "1. Обратитесь к [администратору Денису Ахмерову](https://t.me/Kidisildur1).\n"
        "2. После добавления — снова напишите /start.\n\n"
        "Если проблема сохраняется — сообщите. Мы поможем 😊",
        parse_mode="Markdown"
    )
    await callback.answer()

async def process_webapp_data(message: types.Message):
    print("📩 Попытка обработать сообщение")

    if message.web_app_data:
        print("✅ Получены данные из WebApp:", message.web_app_data.data)

        data = json.loads(message.web_app_data.data)
        equipment = data.get("equipment")
        score = data.get("score")
        passed = data.get("passed")

        username = f"@{message.from_user.username}"
        full_name = message.from_user.full_name
        status = "Пройдено" if passed else "Не пройдено"
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        sheet = get_google_sheet("results")
        sheet.append_row([username, full_name, equipment, score, status, date_str])

        await message.answer(
            f"📘 Обучение завершено!\n"
            f"🛠 Оборудование: {equipment}\n"
            f"💯 Баллы: {score}\n"
            f"{'✅ Тест пройден' if passed else '❌ Тест не пройден'}"
        )
    else:
        print("⚠️ message.web_app_data отсутствует")
        await message.answer("⚠️ Данные от WebApp не получены.")

async def debug_all(message: types.Message):
    print("⚠️ DEBUG: Пришло сообщение:", message)

# Эхо для всех остальных сообщений
async def echo(message: types.Message):
    print("🪵 DEBUG MESSAGE:", message)
    await message.answer(f"Вы написали: {message.text}")

async def check_table(message: types.Message):
    try:
        sheet = get_google_sheet("results")
        values = sheet.get_all_values()
        await message.answer(f"📄 Таблица 'results' найдена!\nСтрок: {len(values)}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при подключении к таблице:\n{e}")

# Регистрация хэндлеров
def register_handlers(dp: Dispatcher):
    dp.message.register(send_welcome, Command(commands=["start"]))
    dp.callback_query.register(start_training, lambda c: c.data == "start_training")
    dp.callback_query.register(show_help, lambda c: c.data == "show_help")
    dp.message.register(process_webapp_data, lambda msg: msg.web_app_data)
    dp.message.register(check_table, Command(commands=["check_table"]))
    # dp.message.register(debug_all)
    dp.message.register(echo)

# Запуск бота
async def main():
    session = AiohttpSession(timeout=60)  # 👈 просто число
    bot = Bot(token=API_TOKEN, session=session)
    dp = Dispatcher()
    register_handlers(dp)
    print("✅ Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())