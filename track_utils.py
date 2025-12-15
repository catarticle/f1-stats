import fastf1 as f1
import pandas as pd
import numpy as np
import json
from datetime import datetime
from collections import Counter

def get_track_stats(year, event):
    """Получает статистику трассы"""
    try:
        print(f"Загрузка статистики трассы для {event} {year}...")
        
        # Загружаем данные текущей гонки
        try:
            session = f1.get_session(year, event, 'R')
            session.load(telemetry=True, laps=True, weather=False)
        except:
            try:
                session = f1.get_session(year, event, 'Q')
                session.load(telemetry=True, laps=True, weather=False)
            except:
                session = f1.get_session(year, event, 'FP3')
                session.load(telemetry=True, laps=True, weather=False)
        
        # Получаем информацию о трассе из расписания
        schedule = f1.get_event_schedule(year)
        event_info = schedule[schedule['EventName'] == event]
        
        if not event_info.empty:
            event_info = event_info.iloc[0]
            track_info = {
                'name': str(event_info.get('OfficialEventName', event)),
                'country': str(event_info.get('Country', 'Unknown')),
                'location': str(event_info.get('Location', 'Unknown')),
                'event_name': str(event)
            }
        else:
            track_info = {
                'name': str(event),
                'country': 'Unknown',
                'location': 'Unknown',
                'event_name': str(event)
            }
        
        # Получаем рекорд круга (самый быстрый круг этой гонки)
        lap_record = get_lap_record(session)
        
        # Получаем самого успешного пилота
        successful_pilot = get_successful_pilot(session, event)
        
        # Получаем длину трассы
        circuit_length = get_circuit_length(session)
        
        # Получаем количество поворотов
        turns_count = estimate_turns_count(session)
        
        # ВАЖНО: Получаем координаты трассы
        coordinates = get_track_coordinates(session)
        
        # Собираем всю статистику
        stats = {
            'track_info': track_info,
            'lap_record': lap_record,
            'successful_pilot': successful_pilot,
            'circuit_length': circuit_length,
            'turns_count': turns_count,
            'coordinates': coordinates,  # ← ДОБАВЛЕНО!
            'year': year
        }
        
        return convert_to_serializable(stats)
        
    except Exception as e:
        print(f"Ошибка в get_track_stats: {e}")
        import traceback
        traceback.print_exc()
        return get_fallback_stats(event)

def get_track_coordinates(session):
    """Получает координаты трассы из сессии"""
    try:
        if session.laps is None or session.laps.empty:
            print("Нет данных кругов для получения координат")
            return []
        
        # Берем самый быстрый круг
        fastest_lap = session.laps.pick_fastest()
        if fastest_lap is None:
            print("Не удалось найти самый быстрый круг")
            return []
        
        # Получаем телеметрию
        telemetry = fastest_lap.get_telemetry()
        if telemetry is None or len(telemetry) < 10:
            print("Недостаточно телеметрии")
            return []
        
        # Получаем координаты X и Y
        x = telemetry['X'].values
        y = telemetry['Y'].values
        
        # Нормализуем координаты для SVG (500x500)
        x_min, x_max = float(x.min()), float(x.max())
        y_min, y_max = float(y.min()), float(y.max())
        
        # Добавляем отступы
        x_range = x_max - x_min
        y_range = y_max - y_min
        margin = 0.1  # 10% отступ
        
        x_min -= x_range * margin
        x_max += x_range * margin
        y_min -= y_range * margin
        y_max += y_range * margin
        
        # Создаем массив координат
        coordinates = []
        step = max(1, len(x) // 300)  # Берем 300 точек для плавности
        
        for i in range(0, len(x), step):
            x_norm = 50 + 400 * (float(x[i]) - x_min) / (x_max - x_min)
            y_norm = 50 + 400 * (float(y[i]) - y_min) / (y_max - y_min)
            coordinates.append({
                'x': float(x_norm),
                'y': float(y_norm)
            })
        
        print(f"Получено {len(coordinates)} точек координат трассы")
        return coordinates
        
    except Exception as e:
        print(f"Ошибка получения координат трассы: {e}")
        return []

def get_lap_record(session):
    """Получает рекорд круга из сессии"""
    try:
        if session.laps is None or session.laps.empty:
            return {
                'time': 'Нет данных',
                'driver': 'Нет данных',
                'driver_fullname': 'Нет данных',
                'team': 'Нет данных',
                'year': 'Нет данных'
            }
        
        # Находим самый быстрый круг
        fastest_lap = session.laps.pick_fastest()
        if fastest_lap is None:
            return {
                'time': 'Нет данных',
                'driver': 'Нет данных',
                'driver_fullname': 'Нет данных',
                'team': 'Нет данных',
                'year': 'Нет данных'
            }
        
        # Получаем информацию о пилоте
        driver_abbr = fastest_lap['Driver']
        lap_time = fastest_lap['LapTime']
        
        # Ищем полное имя и команду в результатах
        driver_fullname = driver_abbr
        driver_team = 'Unknown'
        
        if hasattr(session, 'results') and session.results is not None:
            driver_info = session.results[session.results['Abbreviation'] == driver_abbr]
            if not driver_info.empty:
                driver_fullname = driver_info.iloc[0]['FullName']
                driver_team = driver_info.iloc[0]['TeamName']
        
        # Форматируем время
        if pd.notna(lap_time):
            if hasattr(lap_time, 'total_seconds'):
                total_seconds = lap_time.total_seconds()
                minutes = int(total_seconds // 60)
                seconds = total_seconds % 60
                formatted_time = f"{minutes}:{seconds:06.3f}"
            else:
                # Убираем микросекунды если они есть
                time_str = str(lap_time)
                if len(time_str) > 8:
                    formatted_time = time_str[-12:-4]
                else:
                    formatted_time = time_str
        else:
            formatted_time = 'Нет данных'
        
        return {
            'time': formatted_time,
            'driver': str(driver_abbr),
            'driver_fullname': str(driver_fullname),
            'team': str(driver_team),
            'year': str(session.event['EventDate'].year) if hasattr(session.event, 'EventDate') else 'Нет данных'
        }
        
    except Exception as e:
        print(f"Ошибка получения рекорда круга: {e}")
        return {
            'time': 'Нет данных',
            'driver': 'Нет данных',
            'driver_fullname': 'Нет данных',
            'team': 'Нет данных',
            'year': 'Нет данных'
        }


def get_successful_pilot(session, event_name):
    """Получает самого успешного пилота на трассе на основе исторических данных"""
    try:
        print(f"Анализ исторических данных для трассы: {event_name}")
        
        # Получаем исторические данные (последние 20 лет)
        current_year = datetime.now().year
        start_year = max(1950, current_year - 20)  # Берем максимум 20 лет истории
        
        winners = []
        
        # Анализируем результаты прошлых гонок на этой трассе
        for year in range(start_year, current_year + 1):
            try:
                # Получаем расписание за год
                schedule = f1.get_event_schedule(year)
                if schedule is None or schedule.empty:
                    continue
                
                # Ищем эту трассу в расписании
                event_matches = schedule[schedule['EventName'].str.contains(event_name.split('Grand Prix')[0], case=False, na=False)]
                if event_matches.empty:
                    # Пробуем найти по ключевым словам
                    event_keywords = event_name.replace('Grand Prix', '').strip()
                    event_matches = schedule[schedule['EventName'].str.contains(event_keywords, case=False, na=False)]
                
                if not event_matches.empty:
                    for _, event_row in event_matches.iterrows():
                        try:
                            # Пробуем загрузить гонку
                            race_session = f1.get_session(year, event_row['EventName'], 'R')
                            race_session.load(results=True, laps=False, telemetry=False)
                            
                            if race_session.results is not None and not race_session.results.empty:
                                # Находим победителя (позиция 1)
                                winner = race_session.results[race_session.results['Position'] == 1]
                                if not winner.empty:
                                    winner_info = winner.iloc[0]
                                    winners.append({
                                        'year': year,
                                        'driver': winner_info['FullName'],
                                        'driver_abbr': winner_info.get('Abbreviation', ''),
                                        'team': winner_info['TeamName']
                                    })
                                    print(f"  {year}: {winner_info['FullName']} ({winner_info['TeamName']})")
                        except Exception as e:
                            # Пропускаем гонки, которые не загружаются
                            continue
                            
            except Exception as e:
                print(f"Ошибка при анализе года {year}: {e}")
                continue
        
        if winners:
            # Анализируем, кто побеждал чаще всего
            driver_wins = Counter()
            driver_details = {}
            
            for win in winners:
                driver_name = win['driver']
                driver_wins[driver_name] += 1
                
                if driver_name not in driver_details:
                    driver_details[driver_name] = {
                        'driver': driver_name,
                        'driver_abbr': win['driver_abbr'],
                        'team': win['team'],
                        'wins': 0,
                        'years': []
                    }
                
                driver_details[driver_name]['wins'] = driver_wins[driver_name]
                driver_details[driver_name]['years'].append(str(win['year']))
            
            # Находим самого успешного пилота
            most_wins_driver = driver_wins.most_common(1)[0][0]
            most_wins_details = driver_details[most_wins_driver]
            
            # Форматируем годы побед
            years_list = most_wins_details['years']
            if len(years_list) > 3:
                years_str = f"{years_list[0]}-{years_list[-1]}"
            else:
                years_str = ', '.join(years_list)
            
            return {
                'driver': most_wins_driver,
                'driver_abbr': most_wins_details['driver_abbr'],
                'team': most_wins_details['team'],
                'wins': most_wins_details['wins'],
                'years': years_str
            }
        else:
            # Если исторических данных нет, используем текущего победителя
            return get_current_winner(session, event_name)
            
    except Exception as e:
        print(f"Ошибка анализа исторических данных: {e}")
        return get_current_winner(session, event_name)

def get_current_winner(session, event_name):
    """Получает победителя текущей гонки"""
    try:
        if hasattr(session, 'results') and session.results is not None:
            winner = session.results[session.results['Position'] == 1]
            if not winner.empty:
                winner_info = winner.iloc[0]
                year = session.event['EventDate'].year if hasattr(session.event, 'EventDate') else datetime.now().year
                
                return {
                    'driver': winner_info['FullName'],
                    'driver_abbr': winner_info.get('Abbreviation', ''),
                    'team': winner_info['TeamName'],
                    'wins': 1,
                    'years': str(year)
                }
    except Exception as e:
        print(f"Ошибка получения текущего победителя: {e}")
    
    # Заглушка как последний вариант
    return 'Нет данных'

def get_circuit_length(session):
    """Получает длину трассы"""
    try:
        if session.laps is None or session.laps.empty:
            return "Нет данных"
        
        # Пробуем получить из данных круга
        if 'LapLength' in session.laps.columns:
            first_lap = session.laps.iloc[0]
            if pd.notna(first_lap['LapLength']):
                length_km = float(first_lap['LapLength']) / 1000
                return f"{length_km:.3f} км"
        
        # Известные длины трасс
        known_lengths = {
            'Abu Dhabi Grand Prix': '5.281 км',
            'Monaco Grand Prix': '3.337 км',
            'Italian Grand Prix': '5.793 км',
            'British Grand Prix': '5.891 км',
            'Brazilian Grand Prix': '4.309 км',
            'Mexican Grand Prix': '4.304 км',
            'United States Grand Prix': '5.513 км',
            'Australian Grand Prix': '5.278 км',
            'Bahrain Grand Prix': '5.412 км',
            'Saudi Arabian Grand Prix': '6.174 км'
        }
        
        circuit_name = session.event['EventName'] if hasattr(session.event, 'EventName') else ''
        for key, value in known_lengths.items():
            if key in circuit_name or circuit_name in key:
                return value
        
        return "Нет данных"
        
    except:
        return "Нет данных"

def estimate_turns_count(session):
    """Оценивает количество поворотов"""
    try:
        if session.laps is None or session.laps.empty:
            return "Нет данных"
        
        # Известное количество поворотов для популярных трасс
        known_turns = {
            'Abu Dhabi Grand Prix': 16,
            'Monaco Grand Prix': 19,
            'Italian Grand Prix': 11,
            'British Grand Prix': 18,
            'Brazilian Grand Prix': 15,
            'Mexican Grand Prix': 17,
            'United States Grand Prix': 20,
            'Australian Grand Prix': 16,
            'Bahrain Grand Prix': 15,
            'Saudi Arabian Grand Prix': 27
        }
        
        circuit_name = session.event['EventName'] if hasattr(session.event, 'EventName') else ''
        for key, value in known_turns.items():
            if key in circuit_name or circuit_name in key:
                return value
        
        return "Нет данных"
        
    except:
        return "Нет данных"

def get_fallback_stats(event_name):
    """Заглушка при ошибке"""
    return {
        'track_info': {
            'name': event_name,
            'country': 'Нет данных',
            'location': 'Нет данных',
            'event_name': event_name
        },
        'lap_record': {
            'time': 'Нет данных',
            'driver': 'Нет данных',
            'driver_fullname': 'Нет данных',
            'team': 'Нет данных',
            'year': 'Нет данных'
        },
        'successful_pilot': {
            'driver': 'Нет данных',
            'driver_abbr': 'N/A',
            'team': 'N/A',
            'wins': 0,
            'years': 'N/A'
        },
        'circuit_length': 'Нет данных',
        'turns_count': 'Нет данных',
        'coordinates': [],  # ← ДОБАВЛЕНО пустой массив координат
        'year': 'Нет данных'
    }

def convert_to_serializable(obj):
    """Конвертирует numpy типы в стандартные Python"""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj