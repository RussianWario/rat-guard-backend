import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# Настройка приложения
app = FastAPI()

# РАЗРЕШАЕМ ПОДКЛЮЧЕНИЯ (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
async def root():
    return {"status": "Rat_Guard API is running"}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    try:
        # Очищаем ID от лишних символов Telegram (%26authuser и т.д.)
        clean_id = user_id.split('&')[0].split('%')[0]
        user_id_int = int(clean_id)
        
        # Запрос в базу данных
        response = supabase.table("users").select("*").eq("user_id", user_id_int).execute()
        
        if not response.data:
            # Если юзера нет, создаем дефолтного
            new_user = {"user_id": user_id_int, "points": 0, "inventory": []}
            supabase.table("users").insert(new_user).execute()
            return new_user
            
        return response.data[0]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid User ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
