from fastapi import APIRouter
from supabase import create_client, Client
import os

# Подключаем настройки
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Создаем "роутер" — это как мини-филиал нашего основного приложения
router = APIRouter()

@router.post("/click/{user_id}")
async def handle_click(user_id: str):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        result = supabase.table("profiles").select("points").eq("id", clean_id).execute()
        
        if not result.data:
            return {"error": "User not found"}
        
        new_points = result.data[0].get("points", 0) + 1
        supabase.table("profiles").update({"points": new_points}).eq("id", clean_id).execute()
        
        return {"status": "ok", "points": new_points}
    except Exception as e:
        return {"error": str(e)}
