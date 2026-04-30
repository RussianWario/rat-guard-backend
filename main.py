import os
import random
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from fastapi.middleware.cors import CORSMiddleware

DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка: SQLAlchemy требует, чтобы ссылка начиналась именно с postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Rat_Guard API Online"}

@app.get("/get_profile/{tg_id}")
def get_profile(tg_id: int):
    try:
        with engine.connect() as conn:
            query = text("SELECT points, inventory FROM profiles WHERE id = :id")
            result = conn.execute(query, {"id": tg_id}).fetchone()
            
            if not result:
                insert_query = text("INSERT INTO profiles (id, points, inventory) VALUES (:id, 0, '[]'::jsonb)")
                conn.execute(insert_query, {"id": tg_id})
                conn.commit()
                return {"id": tg_id, "points": 0, "inventory": []}
            
            return {"id": tg_id, "points": result[0], "inventory": result[1] or []}
    except Exception as e:
        # Это покажет нам реальную причину ошибки в браузере
        return {"error": str(e)}
