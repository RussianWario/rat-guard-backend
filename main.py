import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions

# Настройки из Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Инициализация FastAPI
app = FastAPI()

# Настройка CORS (Полный доступ для Mini App и GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация Бота
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# --- МАРШРУТЫ API ---

@app.get("/")
async def root():
    """Проверка для Render и актуальный статус сообщества"""
    return {
        "status": "Rat_Guard API is running", 
        "community": "Крысиное логово",
        "members_count": 141  # Обновлено согласно последним данным
    }

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    # Очищаем ID (на случай, если фронт прислал 'id123' вместо '123')
    clean_id = "".join(filter(str.isdigit, user_id))
    
    if not clean_id:
        raise HTTPException(status_code=400, detail="Invalid User ID format")
    
    try:
        user_id_int = int(clean_id)
        # Ищем профиль в Supabase
        response = supabase.table("profiles").select("*").eq("id", user_id_int).execute()
        
        if not response.data:
            # Авто-регистрация нового пользователя
            new_user = {"id": user_id_int, "points": 0, "inventory": []}
            supabase.table("profiles").insert(new_user).execute()
            return new_user
            
        return response.data[0]
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    # Ссылка на твой фронтенд
    web_app = types.WebAppInfo(url="https://russianwario.github.io/rat-guard-backend/") 
    keyboard.add(types.InlineKeyboardButton(text="Открыть склад 🧀", web_app=web_app))
    
    await message.reply(
        f"Привет, {message.from_user.first_name}! 🐀\n"
        "Добро пожаловать в Крысиное логово. Нажми кнопку, чтобы проверить свои запасы сыра:",
        reply_markup=keyboard
    )

# --- БЕЗОПАСНЫЙ ЗАПУСК ---

async def start_bot():
    """Запуск бота с защитой от конфликтов polling"""
    try:
        # Удаляем вебхук перед запуском polling, чтобы не было конфликтов
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling()
    except exceptions.TerminatedByOtherGetUpdates:
        print("Polling уже запущен в другом процессе, пропускаем...")
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")

@app.on_event("startup")
async def startup_event():
    # Запускаем бота в фоне, чтобы он не блокировал FastAPI
    asyncio.create_task(start_bot())
