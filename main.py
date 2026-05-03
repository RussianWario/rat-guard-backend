import asyncio
import os
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.utils import exceptions
from supabase import create_client, Client

# Импортируем роутер кликера и логику
from clicker import router as clicker_router
from game_logic import sync_energy
from leaderboard_logic import get_leaderboard_data

# --- Конфигурация ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SELF_URL = "https://rat-guard-api.onrender.com/"

# Инициализация Supabase с обработкой ошибок
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"CRITICAL ERROR: Failed to connect to Supabase: {e}")

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- CORS (Разрешаем запросы от Telegram) ---
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
    return {"status": "Rat_Guard API is online", "timestamp": datetime.now().isoformat()}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = Query("Крыса")):
    try:
        # 1. Очистка и проверка ID
        try:
            clean_id = int(user_id)
        except ValueError:
            clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # 2. Поиск пользователя в базе
        result = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        # 3. РЕГИСТРАЦИЯ (если юзера нет)
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
            # Делаем upsert вместо insert для надежности
            insert_result = supabase.table("profiles").upsert(new_user).execute()
            if insert_result.data:
                return insert_result.data[0]
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # 4. СИНХРОНИЗАЦИЯ (если юзер найден)
        user_data = result.data[0]
        new_energy, last_time = sync_energy(user_data)
        
        # Обновляем энергию в базе, если она изменилась
        if new_energy != user_data.get('energy'):
            supabase.table("profiles").update({
                "energy": new_energy,
                "last_refill": last_time.isoformat()
            }).eq("id", clean_id).execute()
            user_data['energy'] = new_energy

        return user_data

    except Exception as e:
        print(f"ERROR в get_profile: {e}")
        return {"error": str(e), "id": user_id}

@app.get("/leaderboard")
async def get_leaderboard():
    try:
        data = get_leaderboard_data(supabase)
        if isinstance(data, list):
            count_result = supabase.table("profiles").select("id", count="exact").execute()
            total = count_result.count if count_result.count else len(data)
            return {"users": data, "total_count": total}
        return data if data else {"users": [], "total_count": 0}
    except Exception as e:
        print(f"ERROR в leaderboard: {e}")
        return {"users": [], "total_count": 0}

# --- Фоновые задачи ---
async def keep_alive():
    """Самопрозвон сервера для предотвращения сна"""
    await asyncio.sleep(30) # Даем серверу запуститься
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(SELF_URL)
                print("Keep-alive: ping success")
            except:
                pass
            await asyncio.sleep(600) # 10 минут

async def start_bot():
    """Запуск Telegram бота"""
    # Ждем немного, чтобы FastAPI успел подняться
    await asyncio.sleep(5)
    print("Starting Telegram Bot Polling...")
    while True:
        try:
            # Сбрасываем все зависшие обновления перед стартом
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            print("WARNING: Бот запущен где-то еще. Ожидание 30 секунд...")
            await asyncio.sleep(30)
        except Exception as e:
            print(f"ERROR бота: {e}")
            await asyncio.sleep(20)

@app.on_event("startup")
async def on_startup():
    # Запускаем бота и пингер фоновыми задачами
    asyncio.create_task(start_bot())
    asyncio.create_task(keep_alive())
