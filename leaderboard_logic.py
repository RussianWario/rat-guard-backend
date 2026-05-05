def get_leaderboard_data(supabase):
    """
    Получает топ-10 игроков и форматирует их имена.
    """
    try:
        # Запрос к базе: берем id, основной username и очки
        # Сортируем по убыванию points
        result = supabase.table("profiles") \
            .select("id, username, points") \
            .order("points", desc=True) \
            .limit(10) \
            .execute()
        
        formatted_list = []
        for row in result.data:
            # Сначала пробуем взять обычный username (он виден на скриншоте image_1f1717.png)
            display_name = row.get("username")
            
            # Если имени нет, используем последние 4 цифры ID
            if not display_name:
                user_id_str = str(row.get("id"))
                display_name = f"Крыса #{user_id_str[-4:]}"
                
            formatted_list.append({
                "username": display_name,
                "points": row.get("points", 0)
            })
            
        return formatted_list
    except Exception as e:
        print(f"Ошибка в leaderboard_logic: {e}")
        return []
