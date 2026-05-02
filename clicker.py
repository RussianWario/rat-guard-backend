from fastapi import APIRouter
from supabase import create_client, Client
import os

# Инициализация Supabase для этого модуля
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Создаем роутер, который мы потом подключим к основному приложению
router = APIRouter()

@router.post("/click/{user_id}")
async def handle_click(user_id: str):
    try:
        # Очищаем ID на случай, если придут лишние символы
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # 1. Получаем текущие очки пользователя
        result = supabase.table("profiles").select("points").eq("id", clean_id).execute()
        
        if not result.data:
            return {"error": "User not found"}
        
        # 2. Увеличиваем на 1
        new_points = result.data[0].get("points", 0) + 1
        
        # 3. Сохраняем результат обратно в базу
        supabase.table("profiles").update({"points": new_points}).eq("id", clean_id).execute()
        
        return {"status": "ok", "points": new_points}
    except Exception as e:
        return {"error": str(e)}
