from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

@router.post("/click/{user_id}")
async def handle_click(user_id: str):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # 1. Получаем текущие данные (только очки и мультитап)
        res = supabase.table("profiles").select("points, multitap_level").eq("id", clean_id).single().execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        # 2. Считаем новые очки с учетом уровня мультитапа
        click_power = res.data.get("multitap_level", 1)
        new_points = res.data["points"] + click_power
        
        # 3. Сохраняем (энергия больше не учитывается)
        supabase.table("profiles").update({"points": new_points}).eq("id", clean_id).execute()
        
        return {
            "status": "ok", 
            "points": new_points
        }
        
    except Exception as e:
        return {"error": str(e)}
