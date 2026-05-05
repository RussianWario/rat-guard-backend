from datetime import datetime, timezone

def get_click_power(user_data):
    """
    Возвращает силу клика на основе уровня Multitap.
    Даже без энергии прокачка силы клика остается важной частью геймплея.
    """
    return user_data.get('multitap_level', 1)

def get_upgrade_price(level):
    """
    Формула цены улучшения. 
    Можно оставить прежнюю (level * 500) или немного усложнить для баланса.
    """
    return level * 500

def get_leaderboard_query(supabase):
    """
    Топ игроков для 'Крысиного логова'.
    Выбираем ID, никнейм и очки, сортируя по убыванию.
    """
    return supabase.table("profiles") \
        .select("id, twitch_username, points") \
        .order("points", desc=True) \
        .limit(10) \
        .execute()
