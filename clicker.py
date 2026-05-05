from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
import os

# Инициализация Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

@router.post("/click/{user_id}")
async def handle_click(user_id: str):
    try:
        # Чистим ID (оставляем только цифры)
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # Используем rpc или прямой update с инкрементом. 
        # Самый надежный способ для Supabase без лишних чтений:
        result = supabase.table("profiles") \
            .update({"points": supabase.rpc("increment", {"row_id": clean_id}).data}) \
            .eq("id", clean_id) \
            .execute()
        
        # Но если у тебя нет функции RPC 'increment', используем классический быстрый апдейт:
        # Сначала получаем текущее значение (один раз)
        res = supabase.table("profiles").select("points").eq("id", clean_id).single().execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        new_points = res.data["points"] + 1
        
        # Сохраняем (без проверки энергии!)
        supabase.table("profiles").update({"points": new_points}).eq("id", clean_id).execute()
        
        return {
            "status": "ok", 
            "points": new_points
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        # Возвращаем профиль, игнорируя колонку энергии в логике, 
        # даже если она осталась в таблице
        result = supabase.table("profiles").select("points").eq("id", clean_id).single().execute()
        
        if not result.data:
            return {"error": "Not found"}
            
        return result.data
    except Exception as e:
        return {"error": str(e)}
