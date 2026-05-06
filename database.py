# database.py — Инициализация базы данных (защита от цикличного импорта)
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Инициализируем клиент здесь один раз
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
