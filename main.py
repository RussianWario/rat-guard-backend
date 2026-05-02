import os
import re
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

app = FastAPI()

# 1. Настройка CORS — чтобы фронтенд на GitHub Pages видел данные
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Подключение к Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 3. Настройка Бота (Токен берется из переменных окружения Render)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@app.on_event("startup")
async def on_startup():
    # Запуск бота в фоновом режиме вместе с сервером
    asyncio.create_task(dp.start_polling())

# 4. Логика команды /start — кнопка появится здесь
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    markup = InlineKeyboardMarkup()
    # Ссылка на твой фронтенд
    web_app = WebAppInfo(url="https://russianwario.github.io/rat-guard-web/")
    markup.add(InlineKeyboardButton(text="Открыть склад 🧀", web_app=web_app))
    
    await message.answer(
        f"Привет, {message.from_user.first_name}! 🐀\n"
        "Нажми на кнопку ниже, чтобы зайти в склад:", 
        reply_markup=markup
    )

# 5. Эндпоинты для получения данных профиля
@app.get("/")
async def root():
    return {"status": "Rat_Guard API is running"}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    try:
        # Очистка ID от лишних символов
        clean_id = re.sub(r'\D', '', user_id) 
        if not clean_id:
            raise ValueError("Некорректный ID")
        
        user_id_int = int(clean_id)
        
        # Запрос в Supabase
        response = supabase.table("profiles").select("*").eq("id", user_id_int).execute()
        
        if not response.data:
            # Если юзера нет, создаем его (регистрация)
            new_user = {
                "id": user_id_int, 
                "points": 0, 
                "inventory": [],
                "twitch_username": "",
                "total_opened": 0
            }
            supabase.table("profiles").insert(new_user).execute()
            return new_user
            
        return response.data[0]
    except Exception as e:
        print(f"Ошибка бэкенда: {e}")
        raise HTTPException(status_code=500, detail=str(e))
