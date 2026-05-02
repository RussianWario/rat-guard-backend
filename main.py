import asyncio
import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions

# Настройки
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Укажи здесь URL своего приложения на Render
SELF_URL = "https://rat-guard-api.onrender.com/"

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Настройка CORS для работы с GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Rat_Guard API is online", "members": 141}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    # Убираем лишние символы из ID, если они прилетят
    clean_id = "".join(filter(str.isdigit, user_id))
    print(f"Запрос профиля для ID: {clean_id}")
    
    # ТУТ ТВОЯ ЛОГИКА С SUPABASE (оставь как была или используй заглушку для теста)
    # Для теста пока возвращаем статику:
    return {
        "points": 500,
        "inventory": ["Сыр", "Старая шестеренка", "Ржавый ключ"]
    }

async def keep_alive():
    """Фоновая задача: стучимся к себе, чтобы Render не спал"""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(SELF_URL)
                print("Self-ping: Success")
            except Exception as e:
                print(f"Self-ping: Failed ({e})")
            await asyncio.sleep(600) # 10 минут

async def start_bot():
    """Запуск бота с защитой от конфликтов"""
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            print("Бот запущен...")
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            print("Конфликт процессов. Ждем 5 сек...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            await asyncio.sleep(10)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
    asyncio.create_task(keep_alive())
