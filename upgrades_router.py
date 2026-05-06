# upgrades_router.py — Изолированный роутер для прокачки
from fastapi import APIRouter, HTTPException
import math

# ИМПОРТ КЛИЕНТА ИЗ ОТДЕЛЬНОГО МОДУЛЯ (Защита от цикличного импорта)
from database import supabase 

router = APIRouter(prefix="/upgrade", tags=["Upgrades"])

MULTITAP_BASE_COST = 100
MULTITAP_COST_MULTIPLIER = 2

def calculate_cost(current_level: int) -> int:
    if current_level < 1:
        current_level = 1
    return int(MULTITAP_BASE_COST * math.pow(MULTITAP_COST_MULTIPLIER, current_level - 1))

@router.post("/multitap/{user_id}")
async def buy_multitap(user_id: int):
    # 1. Получаем текущие данные игрока из таблицы profiles по полю "id"
    res = supabase.table("profiles").select("points", "multitap_level", "level").eq("id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Крыса не найдена в логове")
    
    user_data = res.data[0]
    
    # Защита на случай, если в базе лежат null значения
    current_points = user_data.get("points") or 0
    current_multitap = user_data.get("multitap_level") or 1
    user_level = user_data.get("level") or 1
    
    # 2. Считаем стоимость апгрейда
    cost = calculate_cost(current_multitap)
    
    # 3. Проверяем баланс на бэке (защита от накрутки)
    if current_points < cost:
        return {"status": "error", "message": "Недостаточно сыра 🧀"}
    
    new_points = current_points - cost
    new_multitap = current_multitap + 1
    
    # 4. Сохраняем изменения обратно в таблицу profiles, используя фильтр по "id"
    update_res = supabase.table("profiles").update({
        "points": new_points,
        "multitap_level": new_multitap
    }).eq("id", user_id).execute()
    
    if not update_res.data:
        raise HTTPException(status_code=500, detail="Ошибка при записи в логово")
        
    return {
        "status": "ok",
        "points": new_points,
        "multitap_level": new_multitap,
        "level": user_level
    }
