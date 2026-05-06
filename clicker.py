# clicker.py — Роутер обработки тапов и профилей
from fastapi import APIRouter, HTTPException
# ИМПОРТ КЛИЕНТА ИЗ ОТДЕЛЬНОГО МОДУЛЯ (Защита от цикличного импорта)
from database import supabase 

router = APIRouter()

@router.get("/get_profile/{user_id}")
async def get_profile(user_id: str, username: str = "rat_user"):
    """Эндпоинт для загрузки профиля при старте игры"""
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # Проверяем, есть ли пользователь в базе
        res = supabase.table("profiles").select("*").eq("id", clean_id).execute()
        
        if not res.data:
            # Если пользователя нет — создаем его (авторегистрация)
            new_user = {
                "id": clean_id,
                "username": username,
                "points": 0,
                "multitap_level": 1,
                "level": 1,
                "stars": 0,
                "passive_income": 0
            }
            insert_res = supabase.table("profiles").insert(new_user).execute()
            if insert_res.data:
                return insert_res.data[0]
            raise HTTPException(status_code=500, detail="Не удалось создать профиль")
            
        return res.data[0]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/click/{user_id}")
async def handle_click(user_id: str):
    """Эндпоинт для обработки тапов"""
    try:
        clean_id = int("".join(filter(str.isdigit, user_id)))
        
        # 1. Получаем текущие данные (безопасно через execute без .single())
        res = supabase.table("profiles").select("points, multitap_level, level, stars").eq("id", clean_id).execute()
        
        if not res.data:
            return {"status": "error", "message": "Пользователь не найден", "points": 0}
            
        user_data = res.data[0]
            
        # 2. Считаем новые очки с жесткой защитой от None/null в базе
        current_points = user_data.get("points") or 0
        multitap = user_data.get("multitap_level") or 1
        
        # Если в базе вдруг записан 0 или null, принудительно ставим силу клика = 1
        click_power = int(multitap) if multitap and multitap > 0 else 1
        new_points = current_points + click_power
        
        # 3. Сохраняем новые очки в Supabase
        supabase.table("profiles").update({"points": new_points}).eq("id", clean_id).execute()
        
        # Возвращаем полный набор данных, чтобы фронт сразу обновлял и уровни
        return {
            "status": "ok", 
            "points": new_points,
            "level": user_data.get("level", 1) or 1,
            "stars": user_data.get("stars", 0) or 0
        }
        
    except Exception as e:
        # Возвращаем дефолтную структуру, чтобы фронтенд-скрипт не ломался из-за undefined
        return {"status": "error", "message": str(e), "points": 0}
