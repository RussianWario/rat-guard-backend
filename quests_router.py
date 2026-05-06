# quests_router.py — Логика системы квестов кликера
from fastapi import APIRouter, HTTPException
from database import supabase

router = APIRouter(prefix="/quests", tags=["Quests"])

@router.get("/{user_id}")
async def get_user_quests(user_id: int):
    """
    Получить список всех квестов из базы данных 
    с пометкой 'is_completed' индивидуально для конкретного user_id
    """
    try:
        # 1. Загружаем все доступные квесты из таблицы quests
        quests_res = supabase.table("quests").select("*").execute()
        
        # 2. Загружаем ID квестов, которые эта крыса уже выполнила
        completed_res = supabase.table("user_quests").select("quest_id").eq("user_id", user_id).execute()
        
        completed_ids = [item["quest_id"] for item in completed_res.data] if completed_res.data else []
        
        # 3. Формируем список квестов, подмешивая флаг выполнения
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
    Проверяет, выполнил ли юзер условия квеста, 
    и если да — начисляет сыр (points) и звёзды (stars)
    """
    try:
        # 1. Проверяем, не забирал ли он уже награду за этот квест
        check = supabase.table("user_quests").select("*").eq("user_id", user_id).eq("quest_id", quest_id).execute()
        if check.data:
            return {"status": "error", "message": "Награда за эту задачу уже в твоей норке! Rat_Guard бдит 🐀"}
            
        # 2. Вытягиваем данные квеста и профиля игрока по колонке user_id
        quest_res = supabase.table("quests").select("*").eq("id", quest_id).execute()
        user_res = supabase.table("profiles").select("points", "level", "stars", "multitap_level", "total_clicks").eq("user_id", user_id).execute()
        
        if not quest_res.data or not user_res.data:
            raise HTTPException(status_code=404, detail="Квест или профиль игрока не найден в базе")
            
        quest = quest_res.data[0]
        user_data = user_res.data[0]
        
        # Вытаскиваем текущие статы игрока (с защитой от None)
        user_level = user_data.get("level") or 1
        user_points = user_data.get("points") or 0
        user_stars = user_data.get("stars") or 0
        user_multitap = user_data.get("multitap_level") or 1
        user_total_clicks = user_data.get("total_clicks") or 0
        
        req_value = quest["required_value"]
        quest_type = quest["quest_type"]

        # 3. ПРОВЕРКА ВЫПОЛНЕНИЯ УСЛОВИЙ
        if quest_type == "level":
            if user_level < req_value:
                return {"status": "error", "message": f"Твое Логово ещё слабовато! Требуется {req_value} уровень. (У тебя {user_level})"}
                
        elif quest_type == "total_clicks":
            if user_total_clicks < req_value:
                return {"status": "error", "message": f"Маловато сыра натапано за всё время! Нужно: {req_value:,}. (У тебя: {user_total_clicks})"}
                
        elif quest_type == "multitap_level":
            if user_multitap < req_value:
                return {"status": "error", "message": f"Слабые лапки! Прокачай Мультитап до {req_value} уровня. (У тебя {user_multitap})"}
        else:
            return {"status": "error", "message": "Неизвестный тип квеста"}

        # 4. НАЧИСЛЕНИЕ НАГРАДЫ И ФИКСАЦИЯ
        new_points = user_points + quest["reward_points"]
        new_stars = user_stars + quest["reward_stars"]
        
        # Обновляем профиль в Supabase по user_id
        supabase.table("profiles").update({
            "points": new_points,
            "stars": new_stars
        }).eq("user_id", user_id).execute()
        
        # Записываем лог, чтобы нельзя было заабузить повторно
        supabase.table("user_quests").insert({
            "user_id": user_id,
            "quest_id": quest_id
        }).execute()
        
        return {
            "status": "ok",
            "message": f"Успешно! Получено {quest['reward_points']} 🧀 и {quest['reward_stars']} ⭐",
            "points": new_points,
            "stars": new_stars,
            "level": user_level
        }
        
    except Exception as e:
        print(f"Ошибка при обработке квеста: {e}")
        raise HTTPException(status_code=500, detail="Ошибка Логова при обработке награды")
