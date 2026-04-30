import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# Настройка приложения
app = FastAPI()

# РАЗРЕШАЕМ ПОДКЛЮЧЕНИЯ (CORS) — чтобы твой сайт на GitHub мог забирать данные
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase (используем переменные из настроек Render)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
async def root():
    return {"status": "Rat_Guard API is running"}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    try:
        # 1. Очищаем ID от лишних символов Telegram (%26authuser и т.д.)
        clean_id = user_id.split('&')[0].split('%')[0]
        user_id_int = int(clean_id)
        
        # 2. Запрос в твою таблицу 'profiles' по колонке 'id'
        response = supabase.table("profiles").select("*").eq("id", user_id_int).execute()
        
        # 3. Если пользователя нет в базе — создаем его автоматически
        if not response.data:
            new_user = {
                "id": user_id_int, 
                "points": 0, 
                "inventory": [],
                "twitch_username": "",
                "total_opened": 0
            }
            supabase.table("profiles").insert(new_user).execute()
            return new_user
            
        # 4. Возвращаем данные игрока, если он найден
        return response.data[0]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid User ID format")
    except Exception as e:
        print(f"Ошибка сервера: {e}")
        raise HTTPException(status_code=500, detail=str(e))
