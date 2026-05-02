from datetime import datetime, timezone

def sync_energy(user_data):
    """
    Рассчитывает регенерацию энергии на основе времени.
    """
    current_energy = user_data.get('energy', 1000)
    max_energy = user_data.get('max_energy', 1000)
    
    # Извлекаем время последнего обновления
    last_refill_str = user_data.get('last_refill')
    if isinstance(last_refill_str, str):
        # Убираем Z и приводим к формату с таймзоной
        last_refill = datetime.fromisoformat(last_refill_str.replace('Z', '+00:00'))
    else:
        last_refill = last_refill_str or datetime.now(timezone.utc)
        
    now = datetime.now(timezone.utc)
    
    # Регенерация: 2 единицы в секунду
    seconds_passed = (now - last_refill).total_seconds()
    regenerated = int(seconds_passed * 2) 
    
    new_energy = min(max_energy, current_energy + regenerated)
    return new_energy, now

def get_click_power(user_data):
    """Возвращает силу клика на основе уровня Multitap."""
    return user_data.get('multitap_level', 1)

def get_upgrade_price(level):
    """Простая формула цены: уровень * 500 очков."""
    return level * 500

def get_leaderboard_query(supabase):
    """
    Топ игроков. Если twitch_username пустой, 
    фронтенд может выводить 'Анонимная Крыса' или Telegram ID.
    """
    return supabase.table("profiles") \
        .select("id, twitch_username, points") \
        .order("points", desc=True) \
        .limit(10) \
        .execute()
