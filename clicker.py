from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client, Client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# Схема для приема пакета кликов с фронтенда
class ClickRequest(BaseModel):
    clicks: int = Field(default=1, ge=1, le=100)

# Настройка требований для уровней логова и наград в Звёздах ⭐
# Уровень 1 -> Уровень 2: стоит 5 000 сырков, даёт 5 Звёзд
LEVEL_REQUIREMENTS = {
    1: {"cost_cheese": 5000, "reward_stars": 5},
    2: {"cost_cheese": 25000, "reward_stars": 12},
    3: {"cost_cheese": 100000, "reward_stars": 30},
}

@router.post("/click/{user_id}")
async def handle_click(user_id: str, payload: ClickRequest):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        clicks_count = payload.clicks
        
        # 1. Получаем текущие данные, включая новые поля
        res = supabase.table("profiles").select("points, multitap_level, level, stars").eq("id", clean_id).single().execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        # 2. Считаем новые очки: сила клика * количество пришедших тапов
        click_power = res.data.get("multitap_level", 1)
        earned_points = click_power * clicks_count
        new_points = res.data["points"] + earned_points
        
        # 3. Сохраняем обновленный баланс сырков
        supabase.table("profiles").update({"points": new_points}).eq("id", clean_id).execute()
        
        # Возвращаем фронтенду полные актуальные данные
        return {
            "status": "ok", 
            "points": new_points,
            "level": res.data.get("level", 1),
            "stars": res.data.get("stars", 0)
        }
        
    except Exception as e:
        return {"error": str(e)}

# Новый эндпоинт: Повышение уровня Логова (Квесты)
@router.post("/level_up/{user_id}")
async def level_up(user_id: str):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # Получаем данные игрока
        res = supabase.table("profiles").select("points, level, stars").eq("id", clean_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        current_level = res.data.get("level", 1)
        current_points = res.data["points"]
        current_stars = res.data.get("stars", 0)
        
        # Если игрок дошел до конца заготовленного контента
        if current_level not in LEVEL_REQUIREMENTS:
            return {"status": "error", "message": "Вы достигли максимального доступного уровня логова!"}
            
        requirements = LEVEL_REQUIREMENTS[current_level]
        
        # Проверяем, хватает ли сырков для выполнения главного квеста уровня
        if current_points < requirements["cost_cheese"]:
            return {
                "status": "error", 
                "message": f"Недостаточно сырков! Требуется: {requirements['cost_cheese']}"
            }
            
        # Списываем локальную валюту, повышаем уровень этапа, начисляем глобальные Звёзды
        new_points = current_points - requirements["cost_cheese"]
        new_level = current_level + 1
        new_stars = current_stars + requirements["reward_stars"]
        
        supabase.table("profiles").update({
            "points": new_points,
            "level": new_level,
            "stars": new_stars
        }).eq("id", clean_id).execute()
        
        return {
            "status": "ok",
            "message": f"Поздравляем! Ваше логово перешло на уровень {new_level}!",
            "points": new_points,
            "level": new_level,
            "stars": new_stars
        }
        
    except Exception as e:
        return {"error": str(e)}
