from datetime import datetime, timezone

def sync_energy(user_data):
    """
    Рассчитывает регенерацию энергии. 
    Используется перед каждым кликом или открытием профиля.
    """
    current_energy = user_data.get('energy', 0)
    max_energy = user_data.get('max_energy', 1000)
    
    # Обработка времени последнего рефилла
    last_refill_str = user_data.get('last_refill')
    if isinstance(last_refill_str, str):
        last_refill = datetime.fromisoformat(last_refill_str.replace('Z', '+00:00'))
    else:
        last_refill = last_refill_str
        
    now = datetime.now(timezone.utc)
    
    # Баланс: +2 единицы энергии в секунду
    seconds_passed = (now - last_refill).total_seconds()
    regenerated = int(seconds_passed * 2) 
    
    new_energy = min(max_energy, current_energy + regenerated)
    return new_energy, now

def get_upgrade_price(level, base_cost=100):
    """Считает цену следующего уровня (каждый уровень в 2 раза дороже)."""
    return base_cost * (2 ** (level - 1))

def get_leaderboard_query(supabase):
    """Формирует запрос для получения топ-10 игроков."""
    return supabase.table("profiles") \
        .select("twitch_username, points") \
        .order("points", desc=True) \
        .limit(10) \
        .execute()
