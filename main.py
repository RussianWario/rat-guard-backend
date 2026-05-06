import asyncio
import os
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions
from aiogram.types import WebAppInfo

# ИМПОРТ КЛИЕНТА ИЗ ОТДЕЛЬНОГО МОДУЛЯ (Защита от цикличного импорта)
from database import supabase

# Импорт роутеров и логики лидерборда
from clicker import router as clicker_router
from upgrades_router import router as upgrades_router  # Наш модуль улучшений
from quests_router import router as quests_router      # Подключаем систему квестов
from leaderboard_logic import get_leaderboard_data 

# --- Конфигурация ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEB_APP_URL = "https://russianwario.github.io/rat-guard-web/?v=2.3" 

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- CORS Middlewares ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение изолированных роутеров в FastAPI
app.include_router(clicker_router)
app.include_router(upgrades_router)  # Регистрируем роутер улучшений
app.include_router(quests_router)    # Регистрируем роутер квестов

# --- ЛОГИКА ТЕЛЕГРАМ-БОТА ---
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
        "— Выполняй игровые квесты внутри Логова.\n"
        "— Врывайся в топ-10 лучших крыс.\n\n"
        "Жми кнопку <b>«Склад 🧀»</b> слева от ввода, чтобы начать! 🐀🚀"
    )
    await message.answer(instruction, parse_mode="HTML")

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

# --- ЭНДПОИНТЫ API ---

@app.get("/leaderboard")
async def get_leaderboard():
    """
    Использует логику из модуля leaderboard_logic для формирования топа
    """
    try:
        data = get_leaderboard_data(supabase)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = Query("Крыса")):
    try:
        # Извлекаем чистый ID пользователя Telegram
        clean_id = int("".join(filter(str.isdigit, user_id)))
        avatar_url = await get_tg_avatar(clean_id)
        
        # Запрашиваем профиль по верной колонке 'user_id'
        result = supabase.table("profiles").select("*").eq("user_id", clean_id).execute()
        
        # Если пользователя еще нет в базе — регистрируем с дефолтными параметрами
        if not result.data:
            new_user = {
                "user_id": clean_id, 
                "username": username,
                "avatar_url": avatar_url,
                "points": 0,
                "total_clicks": 0,       # Добавлено для корректного трекинга квестов
                "multitap_level": 1,
                "level": 1,
                "stars": 0
            }
            insert_result = supabase.table("profiles").upsert(new_user).execute()
            return insert_result.data[0]
        
        user_data = result.data[0]
        
        # Защита фронтенда: гарантируем, что критические поля не прилетят как None
        if user_data.get("multitap_level") is None: user_data["multitap_level"] = 1
        if user_data.get("level") is None: user_data["level"] = 1
        if user_data.get("stars") is None: user_data["stars"] = 0
        if user_data.get("total_clicks") is None: user_data["total_clicks"] = 0
        
        # Динамическое обновление юзернейма или аватарки, если они изменились в TG
        updates = {}
        if username != "Крыса" and user_data.get("username") != username:
            updates["username"] = username
        if avatar_url and user_data.get("avatar_url") != avatar_url:
            updates["avatar_url"] = avatar_url

        if updates:
            supabase.table("profiles").update(updates).eq("user_id", clean_id).execute()
            user_data.update(updates)

        return user_data
    except Exception as e:
        return {"error": str(e)}

# --- Фоновый запуск бота ---
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
