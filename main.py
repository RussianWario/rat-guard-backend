import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

app = FastAPI()

# Полный доступ для фронтенда (GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase через переменные окружения
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
async def root():
    return {"status": "Rat_Guard API is running"}

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    try:
        # Улучшенная очистка ID от мусора Telegram
        import re
        clean_id = re.sub(r'\D', '', user_id) 
        if not clean_id:
            raise ValueError("Некорректный ID")
        
        user_id_int = int(clean_id)
        
        # Запрос к таблице profiles
        response = supabase.table("profiles").select("*").eq("id", user_id_int).execute()
        
        if not response.data:
            # Автоматическая регистрация нового участника
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
