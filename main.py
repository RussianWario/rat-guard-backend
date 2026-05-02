import asyncio
import os
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, Query
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
    return {"status": "Rat_Guard API is online"}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = Query("Крыса")):
    try:
        # Очистка ID
        try:
            clean_id = int(user_id)
        except ValueError:
            clean_id = int("".join(filter(str.isdigit, user_id)))
        
        result = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        if not result.data:
            # РЕГИСТРАЦИЯ: Если пользователя нет, создаем запись с именем
            print(f"DEBUG: Регистрация нового пользователя ID: {clean_id}, Имя: {username}")
            
            new_user = {
                "id": clean_id, 
                "username": username, # Сохраняем имя из Telegram
                "points": 0, 
                "energy": 1000, 
                "max_energy": 1000,
                "multitap_level": 1,
                "last_refill": datetime.now(timezone.utc).isoformat()
            }
            insert_result = supabase.table("profiles").insert(new_user).execute()
            return insert_result.data[0]
        
        # СИНХРОНИЗАЦИЯ: Если пользователь есть, обновляем его энергию
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
        return {"error": str(e)}

@app.get("/leaderboard")
async def get_leaderboard():
    try:
        # Получаем данные из логики лидерборда
        # Ожидается, что get_leaderboard_data вернет {'users': [...], 'total_count': X}
        data = get_leaderboard_data(supabase)
        
        # Если в базе пусто или логика вернула не то, считаем вручную
        if not data or 'total_count' not in data:
            count_result = supabase.table("profiles").select("id", count="exact").execute()
            total = count_result.count if count_result.count else 0
            
            # Если логика вернула только список юзеров
            users_list = data if isinstance(data, list) else []
            return {"users": users_list, "total_count": total}
            
        return data
    except Exception as e:
        print(f"ERROR в leaderboard: {e}")
        return {"users": [], "total_count": 0}

# --- Фоновые задачи ---
async def keep_alive():
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(SELF_URL)
            except:
                pass
            await asyncio.sleep(600)

async def start_bot():
    await asyncio.sleep(10)
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            print("Конфликт обновлений, ожидание...")
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            await asyncio.sleep(15)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
    asyncio.create_task(keep_alive())
