# upgrades_router.py — Изолированный роутер для прокачки пассивных зданий и клика
from fastapi import APIRouter, HTTPException
import math
from database import supabase 

router = APIRouter(prefix="/upgrade", tags=["Upgrades"])

# Конфигурация стоимости, множителей и ПАССИВНОГО ДОХОДА за каждый уровень
UPGRADE_CONFIG = {
    "multitap": {
        "base_cost": 100,
        "multiplier": 2.0,
        "db_column": "multitap_level",
        "pps_per_level": 0       # Мультитап увеличивает клик, а не пассивный доход
    },
    "rat_helper": {
        "base_cost": 500,
        "multiplier": 2.2,
        "db_column": "rat_helper_level",
        "pps_per_level": 2       # Каждая дрессированная крыса дает +2 сыра в секунду
    },
    "factory": {
        "base_cost": 2500,
        "multiplier": 2.5,
        "db_column": "factory_level",
        "pps_per_level": 15      # Каждая мануфактура дает +15 сыра в секунду
    },
    "syndicate": {
        "base_cost": 15000,
        "multiplier": 3.0,
        "db_column": "syndicate_level",
        "pps_per_level": 80      # Каждый синдикат дает +80 сыра в секунду
    }
}

def calculate_upgrade_cost(upgrade_type: str, current_level: int) -> int:
    cfg = UPGRADE_CONFIG[upgrade_type]
    lvl = current_level if current_level >= 1 else 1
    power = 0 if (upgrade_type != "multitap" and current_level == 0) else lvl
    return int(cfg["base_cost"] * math.pow(cfg["multiplier"], power))

def calculate_total_pps(user_data: dict, updated_type: str, new_type_level: int) -> int:
    """
    Высчитывает суммарный пассивный доход (PPS) на основе текущих уровней из базы
    и с учетом только что купленного апгрейда.
    """
    total_pps = 0
    for utype, cfg in UPGRADE_CONFIG.items():
        if utype == "multitap":
            continue
        
        # Если это апгрейд, который мы сейчас покупаем — берем его новый уровень
        if utype == updated_type:
            level = new_type_level
        else:
            level = user_data.get(cfg["db_column"]) or 0
            
        total_pps += level * cfg["pps_per_level"]
        
    return total_pps

@router.post("/{upgrade_type}/{user_id}")
async def buy_upgrade(upgrade_type: str, user_id: int):
    if upgrade_type not in UPGRADE_CONFIG:
        return {"status": "error", "message": "Неизвестный тип улучшения"}

    cfg = UPGRADE_CONFIG[upgrade_type]
    db_col = cfg["db_column"]

    # 1. Получаем текущие данные игрока по верному полю "user_id"
    # Дополнительно запрашиваем уровни всех остальных построек для пересчета pps
    res = supabase.table("profiles").select(
        "points", "level", "multitap_level", "rat_helper_level", "factory_level", "syndicate_level"
    ).eq("user_id", user_id).execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Крыса не найдена в логове")
    
    user_data = res.data[0]
    
    current_points = user_data.get("points") or 0
    current_level = user_data.get(db_col) or 0
    global_level = user_data.get("level") or 1
    
    # 2. Считаем стоимость апгрейда
    cost = calculate_upgrade_cost(upgrade_type, current_level)
    
    # 3. Проверяем баланс на бэке (защита от накрутки фейк-пакетами)
    if current_points < cost:
        return {"status": "error", "message": "Недостаточно сыра 🧀"}
    
    new_points = current_points - cost
    new_level = current_level + 1
    
    # Динамически пересчитываем pps на основе новых уровней бизнеса
    new_pps = calculate_total_pps(user_data, upgrade_type, new_level)
    
    # Считаем, нужно ли повысить уровень логова за покупку апгрейда
    if new_level % 5 == 0:
        global_level += 1
    
    # 4. Сохраняем изменения обратно в профиль по user_id
    update_data = {
        "points": new_points,
        db_col: new_level,
        "level": global_level,
        "pps": new_pps  # Передаем обновленное значение пассивного дохода в базу
    }
    
    update_res = supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
    
    if not update_res.data:
        raise HTTPException(status_code=500, detail="Ошибка при записи в логово")
        
    return {
        "status": "ok",
        "points": new_points,
        "new_level": new_level,
        "global_level": global_level,
        "pps": new_pps
    }
