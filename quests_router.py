# quests_router.py — Логика системы уровней, опыта и квестов
from fastapi import APIRouter, HTTPException
from database import supabase

router = APIRouter(prefix="/quests", tags=["Quests"])

@router.get("/{user_id}")
async def get_user_quests(user_id: int):
    """
    Получает список квестов, которые доступны игроку по уровню,
    с пометкой о выполнении.
    """
    try:
        # 1. Получаем уровень игрока
        user_res = supabase.table("profiles").select("level").eq("user_id", user_id).single().execute()
        user_level = user_res.data.get("level") or 1

        # 2. Загружаем квесты, которые подходят под уровень (required_level <= user_level)
        quests_res = supabase.table("quests").select("*").lte("required_level", user_level).execute()
        
        # 3. Загружаем выполненные квесты
        completed_res = supabase.table("user_quests").select("quest_id").eq("user_id", user_id).execute()
        completed_ids = [item["quest_id"] for item in completed_res.data] if completed_res.data else []
        
        quests_list = []
        for q in quests_res.data:
            q_copy = q.copy()
            q_copy["is_completed"] = q["id"] in completed_ids
            quests_list.append(q_copy)
            
        return quests_list
    except Exception as e:
        print(f"Ошибка получения квестов: {e}")
        raise HTTPException(status_code=500, detail="Не удалось загрузить задачи Логова")

@router.post("/claim/{user_id}/{quest_id}")
async def claim_quest_reward(user_id: int, quest_id: int):
    """
    Проверяет выполнение квеста, начисляет XP и Сыр.
    Если XP хватает для Level Up — повышает уровень и дает Звезду.
    """
    try:
        # 1. Проверка на повторное получение
        check = supabase.table("user_quests").select("*").eq("user_id", user_id).eq("quest_id", quest_id).execute()
        if check.data:
            return {"status": "error", "message": "Награда уже в норке! 🐀"}
            
        # 2. Получаем данные квеста и профиля
        quest_res = supabase.table("quests").select("*").eq("id", quest_id).execute()
        user_res = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if not quest_res.data or not user_res.data:
            raise HTTPException(status_code=404, detail="Данные не найдены")
            
        quest = quest_res.data[0]
        user = user_res.data[0]
        
        # 3. ПРОВЕРКА УСЛОВИЙ (динамическая по quest_type)
        q_type = quest["quest_type"]
        req_val = quest["required_value"]
        current_val = user.get(q_type) or 0
        
        if current_val < req_val:
            return {"status": "error", "message": f"Условие не выполнено! Нужно {req_val}, у тебя {current_val}"}

        # 4. РАСЧЕТ ПРОГРЕССА (Опыт и Уровень)
        new_xp = (user.get("xp") or 0) + quest["reward_xp"]
        new_points = (user.get("points") or 0) + quest["reward_points"]
        current_lvl = user.get("level") or 1
        xp_target = user.get("xp_to_next_level") or 100
        stars = user.get("stars") or 0
        
        leveled_up = False
        
        # Цикл на случай, если опыта столько, что игрок перепрыгнул через несколько уровней
        while new_xp >= xp_target:
            new_xp -= xp_target
            current_lvl += 1
            stars += 1  # ЗВЕЗДА ТОЛЬКО ЗА НОВЫЙ УРОВЕНЬ
            xp_target = int(xp_target * 1.5) # Пропорциональное усложнение на 50%
            leveled_up = True

        # 5. СОХРАНЕНИЕ
        supabase.table("profiles").update({
            "points": new_points,
            "xp": new_xp,
            "xp_to_next_level": xp_target,
            "level": current_lvl,
            "stars": stars
        }).eq("user_id", user_id).execute()
        
        supabase.table("user_quests").insert({
            "user_id": user_id,
            "quest_id": quest_id
        }).execute()
        
        return {
            "status": "ok",
            "message": "Уровень повышен!" if leveled_up else "Награда получена!",
            "leveled_up": leveled_up,
            "new_level": current_lvl,
            "new_xp": new_xp,
            "xp_target": xp_target,
            "stars": stars,
            "points": new_points
        }
        
    except Exception as e:
        print(f"Ошибка claim_quest: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обработки награды")
