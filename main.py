import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import asyncio

# Настройки из Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Инициализация FastAPI
app = FastAPI()

# Настройка CORS, чтобы GitHub Pages мог достучаться до Render
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
    """Проверка для Render, чтобы сервер не выключался"""
    return {"status": "Rat_Guard API is running", "members_count": 141}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    # Очищаем ID от лишних символов, если они пришли с фронтенда
    clean_id = "".join(filter(str.isdigit, user_id))
    
    try:
        user_id_int = int(clean_id)
        # Ищем профиль в таблице profiles
        response = supabase.table("profiles").select("*").eq("id", user_id_int).execute()
        
        if not response.data:
            # Если юзера нет, создаем его (авто-регистрация)
            new_user = {"id": user_id_int, "points": 0, "inventory": []}
            supabase.table("profiles").insert(new_user).execute()
            return new_user
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    # Убедись, что ссылка ведет на твой фронтенд на GitHub Pages
    web_app = types.WebAppInfo(url="https://russianwario.github.io/rat-guard-backend/") 
    keyboard.add(types.InlineKeyboardButton(text="Открыть склад 🧀", web_app=web_app))
    
    await message.reply(
        f"Привет, {message.from_user.first_name}! 🐀\n"
        "Нажми на кнопку ниже, чтобы зайти в склад:",
        reply_markup=keyboard
    )

# Запуск бота в фоновом режиме при старте FastAPI
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(dp.start_polling())
