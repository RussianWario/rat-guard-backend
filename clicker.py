# clicker.py — Роутер обработки тапов и профилей
from fastapi import APIRouter, HTTPException
from database import supabase 

router = APIRouter()

@router.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = "rat_user"):
    """Загрузка профиля при старте игры с учетом всех уровней прокачки"""
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # Запрашиваем все поля, которые важны для фронтенда
        res = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        if not res.data:
            # Авторегистрация с полями для всех улучшений
            new_user = {
                "id": clean_id,
                "username": username,
                "points": 0,
                "total_clicks": 0,  # Важно для квестов
                "multitap_level": 1,
                "rat_helper_level": 0,
                "factory_level": 0,
                "syndicate_level": 0,
                "level": 1,
                "stars": 0,
                "passive_income": 0
            }
            insert_res = supabase.table("profiles").insert(new_user).execute()
            if insert_res.data:
                return insert_res.data[0]
            raise HTTPException(status_code=500, detail="Ошибка создания профиля")
            
        return res.data[0]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/click/{user_id}")
async def handle_click(user_id: str):
    """Обработка клика: обновляем баланс и счетчик квестов"""
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # Получаем данные клика и квестов
        res = supabase.table("profiles").select("points, multitap_level, total_clicks, level, stars").eq("id", clean_id).execute()
        
        if not res.data:
            return {"status": "error", "message": "User not found"}
            
        user_data = res.data[0]
        
        # Логика силы клика
        multitap = user_data.get("multitap_level") or 1
        current_points = user_data.get("points") or 0
        current_total = user_data.get("total_clicks") or 0
        
        new_points = current_points + multitap
        new_total = current_total + 1 # Квесты обычно считают количество нажатий
        
        # Обновляем БД
        supabase.table("profiles").update({
            "points": new_points,
            "total_clicks": new_total
        }).eq("id", clean_id).execute()
        
        return {
            "status": "ok", 
            "points": new_points,
            "total_clicks": new_total,
            "level": user_data.get("level", 1),
            "stars": user_data.get("stars", 0)
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e), "points": 0}
