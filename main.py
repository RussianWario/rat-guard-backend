import os
import random
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from fastapi.middleware.cors import CORSMiddleware

# Получаем ссылку на базу из настроек Render
# Она должна выглядеть как postgresql://postgres:password@db.link.supabase.co:5432/postgres
DATABASE_URL = os.getenv("DATABASE_URL")

# Настройка подключения
engine = create_engine(DATABASE_URL)
app = FastAPI()

# Разрешаем запросы от твоего будущего Mini App (Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Rat_Guard API Online", "message": "Крысиное логово приветствует тебя!"}

@app.get("/get_profile/{tg_id}")
def get_profile(tg_id: int):
    with engine.connect() as conn:
        query = text("SELECT points, inventory FROM profiles WHERE id = :id")
        result = conn.execute(query, {"id": tg_id}).fetchone()
        
        if not result:
            # Если юзера нет в базе, регистрируем его
            insert_query = text("INSERT INTO profiles (id, points, inventory) VALUES (:id, 0, '[]'::jsonb)")
            conn.execute(insert_query, {"id": tg_id})
            conn.commit()
            return {"id": tg_id, "points": 0, "inventory": []}
        
        return {
            "id": tg_id, 
            "points": result[0], 
            "inventory": result[1] if result[1] else []
        }

@app.post("/open_case/{tg_id}")
def open_case(tg_id: int):
    cost = 100  # Цена одного кейса
    
    with engine.connect() as conn:
        # Проверяем наличие юзера и его баланс
        user = conn.execute(text("SELECT points, inventory FROM profiles WHERE id = :id"), {"id": tg_id}).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден. Сначала открой профиль.")
        
        if user[0] < cost:
            raise HTTPException(status_code=400, detail="Маловато баллов! Нужно хотя бы 100.")

        # Список призов (можно менять как хочешь)
        prizes = [
            "Роль 'Элитная Крыса'", 
            "1000 VP (Слот)", 
            "Сигна на стриме", 
            "Иммунитет к муту", 
            "Утешительный сухарик"
        ]
        win = random.choice(prizes)

        # Обновляем данные в базе
        new_points = user[0] - cost
        # Добавляем новый предмет в список инвентаря
        current_inv = list(user[1]) if user[1] else []
        current_inv.append(win)
        
        update_query = text("UPDATE profiles SET points = :p, inventory = :i WHERE id = :id")
        conn.execute(update_query, {
            "p": new_points, 
            "i": str(current_inv).replace("'", '"'), # Форматируем под JSON
            "id": tg_id
        })
        conn.commit()
        
        return {"win": win, "new_balance": new_points}
