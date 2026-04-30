import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

app = FastAPI()

# Разрешаем фронтенду подключаться к бэкенду
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase через переменные окружения Render
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
async def root():
    return {"status": "Rat_Guard API is running"}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    try:
        # Очистка ID от лишних параметров Telegram
        clean_id = user_id.split('&')[0].split('%')[0]
        user_id_int = int(clean_id)
        
        # Запрос в таблицу 'profiles' (как в твоем SQL)
        response = supabase.table("profiles").select("*").eq("id", user_id_int).execute()
        
        if not response.data:
            # Создание нового профиля, если его нет
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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
