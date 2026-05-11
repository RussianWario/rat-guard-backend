# quests_router.py — Исправленная версия
from fastapi import APIRouter, HTTPException
from database import supabase

# Убедись, что префикс совпадает с вызовами во фронтенде
router = APIRouter(prefix="/quests", tags=["Quests"])

@router.get("/{user_id}")
async def get_user_quests(user_id: str):
    try:
        # Чистим ID (как в clicker.py)
        clean_id = int("".join(filter(str.isdigit, user_id)))

        # 1. Получаем профиль (используем "id", а не "user_id")
        user_res = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        if not user_res.data:
            return []
        
        user_data = user_res.data[0]
        user_level = user_data.get("level") or 1

        # 2. Загружаем доступные квесты
        quests_res = supabase.table("quests").select("*").lte("required_level", user_level).execute()
        
        # 3. Загружаем выполненные квесты (фильтр по "user_id" в связующей таблице)
        completed_res = supabase.table("user_quests").select("quest_id").eq("user_id", clean_id).execute()
        completed_ids = [item["quest_id"] for item in completed_res.data] if completed_res.data else []
        
        result = []
        for q in quests_res.data:
            # Считаем текущий прогресс на основе типа квеста
            # Если тип 'total_clicks', берем значение из колонки total_clicks в профиле
            current_val = user_data.get(q["quest_type"]) or 0
            
            is_completed = q["id"] in completed_ids
            can_claim = not is_completed and current_val >= q["required_value"]

            result.append({
                "id": q["id"],
                "title": q["title"],
                "description": q["description"],
                "target": q["required_value"],
                "current_progress": current_val,
                "can_claim": can_claim,
                "is_completed": is_completed,
                "reward_points": q.get("reward_points", 0),
                "reward_xp": q.get("reward_xp", 0)
            })
            
        return result
    except Exception as e:
        print(f"Ошибка получения квестов: {e}")
        return [] # Возвращаем пустой список вместо 500 ошибки, чтобы фронт не вис

@router.post("/claim/{quest_id}/{user_id}") # ПОРЯДОК ИСПРАВЛЕН ПОД ТВОЙ JS
async def claim_quest_reward(quest_id: int, user_id: str):
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # 1. Проверка: не забирали ли уже?
        check = supabase.table("user_quests").select("*").eq("user_id", clean_id).eq("quest_id", quest_id).execute()
        if check.data:
            return {"status": "error", "message": "Награда уже получена!"}
            
        # 2. Получаем данные
        quest_res = supabase.table("quests").select("*").eq("id", quest_id).execute()
        user_res = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        if not quest_res.data or not user_res.data:
            return {"status": "error", "message": "Данные не найдены"}
            
        quest = quest_res.data[0]
        user = user_res.data[0]
        
        # 3. Проверка прогресса
        q_type = quest["quest_type"]
        req_val = quest["required_value"]
        current_val = user.get(q_type) or 0
        
        if current_val < req_val:
            return {"status": "error", "message": "Условие еще не выполнено"}

        # 4. Логика наград и XP
        new_xp = (user.get("xp") or 0) + quest["reward_xp"]
        new_points = (user.get("points") or 0) + quest["reward_points"]
        current_lvl = user.get("level") or 1
        xp_target = user.get("xp_to_next_level") or 100
        stars = user.get("stars") or 0
        
        leveled_up = False
        while new_xp >= xp_target:
            new_xp -= xp_target
            current_lvl += 1
            stars += 1
            xp_target = int(xp_target * 1.5)
            leveled_up = True

        # 5. Сохраняем всё в БД (используем колонку "id" для профиля)
        supabase.table("profiles").update({
            "points": new_points,
            "xp": new_xp,
            "xp_to_next_level": xp_target,
            "level": current_lvl,
            "stars": stars
        }).eq("id", clean_id).execute()
        
        supabase.table("user_quests").insert({
            "user_id": clean_id,
            "quest_id": quest_id
        }).execute()
        
        return {
            "status": "ok",
            "message": "Успешно!",
            "leveled_up": leveled_up,
            "new_level": current_lvl,
            "points": new_points
        }
        
    except Exception as e:
        print(f"Ошибка claim_quest: {e}")
        return {"status": "error", "message": "Системная ошибка"}
