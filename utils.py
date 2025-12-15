import fastf1 as f1
import pandas as pd

def get_latest_race():
    """Находит самую последнюю гонку, по которой есть реальные результаты"""
    for year in range(2025, 2017, -1):
        try:
            schedule = f1.get_event_schedule(year)
            for i in range(len(schedule)-1, -1, -1):
                event = schedule.iloc[i]
                if event['EventName'] == 'Test':
                    continue
                try:
                    session = f1.get_session(year, event['EventName'], 'R')
                    session.load(laps=False, telemetry=False, weather=False, messages=False)
                    if not session.results.empty:
                        return year, event['EventName']
                    else:
                        print(f"Нет результатов для {event['EventName']} {year}")
                except Exception as e:
                    print(f"Не удалось загрузить {event['EventName']} {year}: {e}")
                    continue
        except Exception as e:
            print(f"Не удалось получить расписание за {year}: {e}")
            continue
    return 2024, 'Austrian'

def get_team_color(team):
    colors = {
        'Mercedes': '#27F4D2',
        'Red Bull': '#3671C6', 
        'Red Bull Racing': '#3671C6',
        'Ferrari': '#E80020',
        'McLaren': '#FF8000',
        'Alpine': '#FF87BC',
        'Williams': '#64C4FF',
        'Aston Martin': '#229971',
        'AlphaTauri': '#6692FF', 
        'Racing Bulls': '#6692FF',
        'Haas': '#B6BABD',
        'Alfa Romeo': '#52E252',
        'Kick Sauber': '#52E252'
    }
    return colors.get(team, '#CCCCCC')

def format_time(t):
    if pd.isna(t):
        return 'нет информации'
    s = str(t)
    if 'days' in s:
        s = s.split(' ')[-1]
    if s.endswith('000'):
        s = s[:-3]
    return s

def calculate_points(position, fastest_lap=False, sprint=False):
    """Рассчитывает очки по позиции в гонке"""
    points_system = {
        1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
        6: 8, 7: 6, 8: 4, 9: 2, 10: 1
    }
    
    # Проверяем, что позиция - число
    if pd.isna(position) or not isinstance(position, (int, float)):
        return 0
    
    pos = int(position)
    
    # Базовые очки за позицию
    points = points_system.get(pos, 0)
    
    # Дополнительное очко за быстрый круг (только если в топ-10)
    if fastest_lap and 1 <= pos <= 10:
        points += 1
    
    return points

def get_fastest_lap_driver(session):
    """Определяет пилота с самым быстрым кругом"""
    try:
        if session.laps is not None and not session.laps.empty:
            # Находим самый быстрый круг
            fastest_lap = session.laps.pick_fastest()
            if fastest_lap is not None:
                return fastest_lap['Driver']
    except:
        pass
    return None

def get_fastest_lap_info(session):
    """Получает информацию о самом быстром круге"""
    try:
        if hasattr(session, 'laps') and session.laps is not None and not session.laps.empty:
            # Используем встроенный метод FastF1
            fastest_lap = session.laps.pick_fastest()
            if fastest_lap is not None:
                return {
                    'driver': fastest_lap['Driver'],
                    'driver_number': fastest_lap['DriverNumber'],
                    'team': fastest_lap['Team'],
                    'lap_time': fastest_lap['LapTime']
                }
    except Exception as e:
        print(f"Ошибка при определении быстрого круга: {e}")
    
    return None

def calculate_points_for_session(session):
    """Рассчитывает очки для всех пилотов в сессии"""
    if session.results is None or session.results.empty:
        return {}
    
    fastest_info = get_fastest_lap_info(session)
    fastest_driver_number = fastest_info['driver_number'] if fastest_info else None
    
    points_dict = {}
    
    for idx, row in session.results.iterrows():
        position = row['Position']
        driver_number = row['DriverNumber']
        
        # Проверяем, есть ли у пилота быстрый круг
        has_fastest = (fastest_driver_number == driver_number)
        
        # Рассчитываем очки
        points = calculate_points(position, has_fastest)
        
        points_dict[driver_number] = {
            'points': points,
            'has_fastest_lap': has_fastest,
            'position': position
        }
    
    return points_dict