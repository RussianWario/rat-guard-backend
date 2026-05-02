import asyncio
import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.utils import exceptions
from supabase import create_client, Client

# Импортируем роутер кликера и логику
from clicker import router as clicker_router
from game_logic import sync_energy
from leaderboard_logic import get_leaderboard_data  # НОВЫЙ ИМПОРТ

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
async def get_profile(user_id: str):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        result = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        if not result.data:
            new_user = {
                "id": clean_id, 
                "points": 0, 
                "energy": 1000, 
                "max_energy": 1000,
                "multitap_level": 1
            }
            supabase.table("profiles").insert(new_user).execute()
            return new_user
        
        user_data = result.data[0]
        new_energy, last_time = sync_energy(user_data)
        
        if new_energy != user_data['energy']:
            supabase.table("profiles").update({
                "energy": new_energy,
                "last_refill": last_time.isoformat()
            }).eq("id", clean_id).execute()
            user_data['energy'] = new_energy

        return user_data
    except Exception as e:
        return {"error": str(e)}

# ОБНОВЛЕННЫЙ ЭНДПОИНТ ЛИДЕРБОРДА
@app.get("/leaderboard")
async def get_leaderboard():
    # Теперь вся логика обработки имен живет в отдельном файле
    data = get_leaderboard_data(supabase)
    return data

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
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            await asyncio.sleep(5)
        except Exception:
            await asyncio.sleep(10)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
    asyncio.create_task(keep_alive())
