import asyncio
import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions
from supabase import create_client, Client

# --- Настройки ---
# Эти данные подтянутся из настроек Render, которые мы проверяли на скрине image_02e97e.png
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SELF_URL = "https://rat-guard-api.onrender.com/"

# Инициализация клиента Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- Настройка CORS ---
# Разрешаем фронтенду (твоему сайту на GitHub) общаться с этим бэкендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    # Статус сервера и количество участников в «Крысином логове»
    return {"status": "Rat_Guard API is online", "members": 141}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    # Очищаем ID от лишних знаков и букв
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
    except ValueError:
        return {"error": "Invalid User ID"}
        
    print(f"DEBUG: Запрос профиля для ID: {clean_id}")
    
    # 1. Ищем пользователя в таблице profiles
    result = supabase.table("profiles").select("*").eq("id", clean_id).execute()
    
    # 2. Если пользователя нет в базе — регистрируем его (создаем новую запись)
    if not result.data:
        print(f"DEBUG: Новый пользователь! Создаю запись для {clean_id}")
        new_user = {
            "id": clean_id,
            "points": 0,
            "inventory": [],
            "total_opened": 0
        }
        supabase.table("profiles").insert(new_user).execute()
        return new_user
        
    # 3. Если пользователь есть — отдаем его реальные данные
    return result.data[0]

# --- Фоновые задачи ---

async def keep_alive():
    """Стучимся к себе каждые 10 минут, чтобы Render не выключал сервер"""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(SELF_URL)
                print("Self-ping: Success")
            except Exception as e:
                print(f"Self-ping: Failed ({e})")
            await asyncio.sleep(600)

async def start_bot():
    """Запуск телеграм-бота внутри FastAPI"""
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            print("Бот запущен...")
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            print("Конфликт процессов бота. Ждем 5 сек...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            await asyncio.sleep(10)

@app.on_event("startup")
async def on_startup():
    # Запускаем бота и пинг в фоне, чтобы они не мешали работе API
    asyncio.create_task(start_bot())
    asyncio.create_task(keep_alive())
