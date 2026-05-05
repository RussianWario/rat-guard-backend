import asyncio
import os
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from supabase import create_client, Client

# Импорт твоих модулей
from clicker import router as clicker_router
from game_logic import sync_energy

# --- Конфигурация ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SELF_URL = "https://rat-guard-api.onrender.com/"
# Ссылка проверена и очищена от лишних символов
WEB_APP_URL = "https://russianwario.github.io/rat-guard-web/?v=1" 

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- ЛОГИКА БОТА ---

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Отправляет инструкцию и устанавливает кнопку Склад"""
    try:
        await message.delete() # Чистим чат от команды /start
    except:
        pass

    user_name = message.from_user.first_name or "Гвардеец"
    instruction = (
        f"🧀 **Привет, {user_name}! Добро пожаловать в Rat Guard Hub!**\n\n"
        "Rat Guard — это Mini App игра для зрителей канала **kirisaa**.\n\n"
        "— Добывай сыр тапами по экрану.\n"
        "— Улучшай мультатап и восстанавливай энергию.\n"
        "— Врывайся в топ-100 лучших крыс.\n\n"
        "Жми кнопку ниже, чтобы начать! 🐀🚀"
    )
    
    markup = ReplyKeyboardMarkup(
        resize_keyboard=True, 
        input_field_placeholder="Твой склад готов 👇"
    )
    # Кнопка привязана к твоему URL
    web_app_btn = KeyboardButton(
        text="Склад 🧀", 
        web_app=WebAppInfo(url=WEB_APP_URL)
    )
    markup.add(web_app_btn)

    await message.answer(instruction, reply_markup=markup, parse_mode="Markdown")

@dp.message_handler()
async def block_messages(message: types.Message):
    """Игнорирует обычный текст"""
    pass

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
    except Exception as e:
        print(f"Аватар не найден для {user_id}: {e}")
    return ""

# --- Эндпоинты API ---
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Rat_Guard API is online", "time": datetime.now().isoformat()}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = Query("Крыса")):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        avatar_url = await get_tg_avatar(clean_id)
        result = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        if not result.data:
            new_user = {
                "id": clean_id, 
                "username": username,
                "avatar_url": avatar_url,
                "points": 0, 
                "energy": 1000, 
                "max_energy": 1000,
                "multitap_level": 1,
                "last_refill": datetime.now(timezone.utc).isoformat()
            }
            insert_result = supabase.table("profiles").upsert(new_user).execute()
            return insert_result.data[0]
        
        user_data = result.data[0]
        # Обновляем профиль, если изменился ник или ава
        updates = {}
        if username != "Крыса" and user_data.get("username") != username:
            updates["username"] = username
        if avatar_url and user_data.get("avatar_url") != avatar_url:
            updates["avatar_url"] = avatar_url

        if updates:
            supabase.table("profiles").update(updates).eq("id", clean_id).execute()
            user_data.update(updates)

        new_energy, last_time = sync_energy(user_data)
        if new_energy != user_data.get('energy'):
            supabase.table("profiles").update({
                "energy": new_energy,
                "last_refill": last_time.isoformat()
            }).eq("id", clean_id).execute()
            user_data['energy'] = new_energy

        return user_data

    except Exception as e:
        return {"error": str(e)}

# --- Запуск ---
async def start_bot():
    await asyncio.sleep(5) # Даем API время прогреться
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling()
        except exceptions.TerminatedByOtherGetUpdates:
            await asyncio.sleep(30)
        except Exception as e:
            await asyncio.sleep(15)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
