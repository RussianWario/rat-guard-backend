# upgrades_router.py — Роутер для прокачки пассивных зданий и клика
from fastapi import APIRouter, HTTPException
import math
from database import supabase 

router = APIRouter(prefix="/upgrade", tags=["Upgrades"])

# Конфигурация: добавлены требования к уровню (min_level)
UPGRADE_CONFIG = {
    "multitap": {
        "base_cost": 100,
        "multiplier": 2.0,
        "db_column": "multitap_level",
        "pps_per_level": 0,
        "min_level": 1        # Доступно сразу
    },
    "rat_helper": {
        "base_cost": 500,
        "multiplier": 2.2,
        "db_column": "rat_helper_level",
        "pps_per_level": 2,
        "min_level": 2        # Откроется на 2 уровне
    },
    "factory": {
        "base_cost": 2500,
        "multiplier": 2.5,
        "db_column": "factory_level",
        "pps_per_level": 15,
        "min_level": 5        # Откроется на 5 уровне
    },
    "syndicate": {
        "base_cost": 15000,
        "multiplier": 3.0,
        "db_column": "syndicate_level",
        "pps_per_level": 80,
        "min_level": 10       # Откроется на 10 уровне
    }
}

def calculate_upgrade_cost(upgrade_type: str, current_level: int) -> int:
    cfg = UPGRADE_CONFIG[upgrade_type]
    lvl = current_level if current_level >= 1 else 1
    power = 0 if (upgrade_type != "multitap" and current_level == 0) else lvl
    return int(cfg["base_cost"] * math.pow(cfg["multiplier"], power))

def calculate_total_pps(user_data: dict, updated_type: str, new_type_level: int) -> int:
    """Высчитывает суммарный пассивный доход (PPS)"""
    total_pps = 0
    for utype, cfg in UPGRADE_CONFIG.items():
        if utype == "multitap":
            continue
        level = new_type_level if utype == updated_type else (user_data.get(cfg["db_column"]) or 0)
        total_pps += level * cfg["pps_per_level"]
    return total_pps

@router.get("/available/{user_id}")
async def get_available_upgrades(user_id: int):
    """Возвращает список только тех улучшений, которые открыты по уровню"""
    res = supabase.table("profiles").select("level").eq("user_id", user_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Крыса не найдена")
    
    current_user_level = res.data.get("level") or 1
    # Отфильтровываем то, что игроку еще рано видеть
    available = {k: v for k, v in UPGRADE_CONFIG.items() if v["min_level"] <= current_user_level}
    return available

@router.post("/{upgrade_type}/{user_id}")
async def buy_upgrade(upgrade_type: str, user_id: int):
    if upgrade_type not in UPGRADE_CONFIG:
        return {"status": "error", "message": "Неизвестный тип улучшения"}

    cfg = UPGRADE_CONFIG[upgrade_type]
    
    # 1. Получаем данные игрока
    res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Крыса не найдена")
    
    user_data = res.data[0]
    user_level = user_data.get("level") or 1
    
    # ПРОВЕРКА: открыто ли улучшение для этого уровня логова
    if user_level < cfg["min_level"]:
        return {
            "status": "error", 
            "message": f"Нужен {cfg['min_level']} уровень логова! Керри квесты 🧀"
        }

    db_col = cfg["db_column"]
    current_points = user_data.get("points") or 0
    current_upgrade_level = user_data.get(db_col) or 0
    
    # 2. Считаем стоимость
    cost = calculate_upgrade_cost(upgrade_type, current_upgrade_level)
    
    # 3. Проверка баланса
    if current_points < cost:
        return {"status": "error", "message": "Недостаточно сыра 🧀"}
    
    new_points = current_points - cost
    new_upgrade_level = current_upgrade_level + 1
    new_pps = calculate_total_pps(user_data, upgrade_type, new_upgrade_level)
    
    # 4. Сохраняем (уровень логова НЕ меняем, он только за квесты)
    update_data = {
        "points": new_points,
        db_col: new_upgrade_level,
        "pps": new_pps
    }
    
    update_res = supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
    
    if not update_res.data:
        raise HTTPException(status_code=500, detail="Ошибка при записи в логово")
        
    return {
        "status": "ok",
        "points": new_points,
        "new_level": new_upgrade_level,
        "pps": new_pps
    }
