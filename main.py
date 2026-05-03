import asyncio
import os
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.utils import exceptions
from supabase import create_client, Client

# Импорт твоих модулей
from clicker import router as clicker_router
from game_logic import sync_energy
from leaderboard_logic import get_leaderboard_data

# --- Конфигурация ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SELF_URL = "https://rat-guard-api.onrender.com/"

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clicker_router)

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Rat_Guard API is online", "time": datetime.now().isoformat()}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = Query("Крыса")):
    try:
        # Очистка ID
        try:
            clean_id = int(user_id)
        except ValueError:
            clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # Запрос в базу
        result = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        # РЕГИСТРАЦИЯ: если юзера нет
        if not result.data:
            print(f"DEBUG: Регистрация нового пользователя ID: {clean_id}")
            new_user = {
                "id": clean_id, 
                "username": username if username else f"Крыса #{str(clean_id)[-4:]}",
                "points": 0, 
                "energy": 1000, 
                "max_energy": 1000,
                "multitap_level": 1,
                "last_refill": datetime.now(timezone.utc).isoformat()
            }
            # Используем upsert для надежности
            insert_result = supabase.table("profiles").upsert(new_user).execute()
            if insert_result.data:
                return insert_result.data[0]
            raise Exception("Base insert failed")
        
        # СИНХРОНИЗАЦИЯ ЭНЕРГИИ
        user_data = result.data[0]
        new_energy, last_time = sync_energy(user_data)
        
        if new_energy != user_data.get('energy'):
            supabase.table("profiles").update({
                "energy": new_energy,
                "last_refill": last_time.isoformat()
            }).eq("id", clean_id).execute()
            user_data['energy'] = new_energy

        return user_data

    except Exception as e:
        print(f"ERROR в get_profile: {e}")
        return {"error": str(e), "details": "Check Supabase columns"}

@app.get("/leaderboard")
async def get_leaderboard():
    try:
        data = get_leaderboard_data(supabase)
        if isinstance(data, list):
            count_result = supabase.table("profiles").select("id", count="exact").execute()
            total = count_result.count if count_result.count else len(data)
            return {"users": data, "total_count": total}
        return data
    except Exception as e:
        print(f"ERROR в leaderboard: {e}")
        return {"users": [], "total_count": 0}

# --- Фоновые задачи ---
async def keep_alive():
    await asyncio.sleep(15)
    async with httpx.AsyncClient() as client:
        while True:
            try: await client.get(SELF_URL)
            except: pass
            await asyncio.sleep(600)

async def start_bot():
    """Запуск бота без блокировки API"""
    await asyncio.sleep(10)
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            print("Бот запущен локально! Ожидание 30 сек...")
            await asyncio.sleep(30)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            await asyncio.sleep(15)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
    asyncio.create_task(keep_alive())
