import fastf1 as f1
import pandas as pd

def get_latest_race():
    """Находит самую последнюю гонку, по которой есть реальные результаты"""
    for year in range(2025, 2017, -1):  # от 2025 до 2018
        try:
            schedule = f1.get_event_schedule(year)
            # Проходим по гонкам с конца сезона
            for i in range(len(schedule)-1, -1, -1):
                event = schedule.iloc[i]
                if event['EventName'] == 'Test':
                    continue
                try:
                    session = f1.get_session(year, event['EventName'], 'R')
                    session.load(laps=False, telemetry=False, weather=False, messages=False)
                    # Проверяем, есть ли результаты
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
    # Если ничего не нашли — возвращаем что-то по умолчанию
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