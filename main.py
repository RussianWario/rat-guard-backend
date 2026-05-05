import asyncio
import os
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions
from aiogram.types import WebAppInfo
from supabase import create_client, Client

# Импорт роутера (энергия больше не нужна)
from clicker import router as clicker_router

# --- Конфигурация ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# Твоя ссылка на фронтенд
WEB_APP_URL = "https://russianwario.github.io/rat-guard-web/?v=2.3" 

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- ЛОГИКА БОТА ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    try:
        await message.delete() 
    except:
        pass

    user_name = message.from_user.first_name or "Гвардеец"
    
    instruction = (
        f"🧀 <b>Привет, {user_name}! Добро пожаловать в Rat Guard Hub!</b>\n\n"
        "Rat Guard — это Mini App игра для зрителей канала <b>kirisaa</b>.\n\n"
        "— Добывай сыр тапами по экрану (БЕЗ ЛИМИТОВ!).\n"
        "— Врывайся в топ-100 лучших крыс.\n\n"
        "Жми кнопку <b>«Склад 🧀»</b> слева от ввода, чтобы начать! 🐀🚀"
    )

    await message.answer(instruction, parse_mode="HTML")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clicker_router)

# --- Логика аватарок ---
async def get_tg_avatar(user_id: int):
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][0].file_id
            file = await bot.get_file(file_id)
            return f"https://api.telegram.org/file/bot{API_TOKEN}/{file.file_path}"
    except:
        return ""
    return ""

# --- Эндпоинты API ---

@app.get("/leaderboard")
async def get_leaderboard():
    try:
        result = supabase.table("profiles").select("*").order("points", desc=True).limit(100).execute()
        return result.data
    except Exception as e:
        return {"error": str(e)}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = Query("Крыса")):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        avatar_url = await get_tg_avatar(clean_id)
        result = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        # Если пользователя нет — создаем без полей энергии
        if not result.data:
            new_user = {
                "id": clean_id, 
                "username": username,
                "avatar_url": avatar_url,
                "points": 0,
                "multitap_level": 1
            }
            insert_result = supabase.table("profiles").upsert(new_user).execute()
            return insert_result.data[0]
        
        user_data = result.data[0]
        
        # Обновление аватарки и ника если изменились
        updates = {}
        if username != "Крыса" and user_data.get("username") != username:
            updates["username"] = username
        if avatar_url and user_data.get("avatar_url") != avatar_url:
            updates["avatar_url"] = avatar_url

        if updates:
            supabase.table("profiles").update(updates).eq("id", clean_id).execute()
            user_data.update(updates)

        return user_data
    except Exception as e:
        return {"error": str(e)}

# --- Запуск бота ---
async def start_bot():
    await asyncio.sleep(5)
    try:
        await bot.set_chat_menu_button(
            menu_button=types.MenuButtonWebApp(
                text="Склад 🧀",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
    except Exception as e:
        print(f"Ошибка кнопки: {e}")

    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            await asyncio.sleep(30)
        except Exception:
            await asyncio.sleep(15)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
