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
        
        
        # Получаем длину трассы
        circuit_length = get_circuit_length(session)
        
        # Получаем количество поворотов
        turns_count = estimate_turns_count(session)
        
        # Получаем координаты трассы
        coordinates = get_track_coordinates(session)
        
        # Собираем всю статистику
        stats = {
            'track_info': track_info,
            'circuit_length': circuit_length,
            'turns_count': turns_count,
            'coordinates': coordinates,  
            'year': year
        }
        
        return convert_to_serializable(stats)
        
    except Exception as e:
        print(f"Ошибка в get_track_stats: {e}")
        import traceback
        traceback.print_exc()

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
            'Saudi Arabian Grand Prix': '6.174 км',
            'Azerbaijan Grand Prix': '6.003 км',
            'Miami Grand Prix': '5.412 км',
            'Spanish Grand Prix': '4.657 км',
            'Canadian Grand Prix': '4.361 км',
            'Austrian Grand Prix': '4.318 км',
            'Hungarian Grand Prix': '4.381 км',
            'Belgian Grand Prix': '7.004 км',
            'Dutch Grand Prix': '4.259 км',
            'Singapore Grand Prix': '4.928 км',
            'Japanese Grand Prix': '5.807 км',
            'Qatar Grand Prix': '5.419 км',
            'Las Vegas Grand Prix': '6.201 км',
            'Chinese Grand Prix': '5.451 км',
            'Emilia Romagna Grand Prix': '4.909 км',
            'Portuguese Grand Prix': '4.653 км'
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
            'Australian Grand Prix': 14,  # После реконфигурации 2022 года
            'Bahrain Grand Prix': 15,
            'Saudi Arabian Grand Prix': 27,
            'Azerbaijan Grand Prix': 20,
            'Miami Grand Prix': 19,
            'Spanish Grand Prix': 16,
            'Canadian Grand Prix': 14,
            'Austrian Grand Prix': 10,
            'Hungarian Grand Prix': 14,
            'Belgian Grand Prix': 19,
            'Dutch Grand Prix': 14,
            'Singapore Grand Prix': 19,
            'Japanese Grand Prix': 18,
            'Qatar Grand Prix': 16,
            'Las Vegas Grand Prix': 17,
            'Chinese Grand Prix': 16,
            'Emilia Romagna Grand Prix': 19,
            'Portuguese Grand Prix': 15
        }
        
        circuit_name = session.event['EventName'] if hasattr(session.event, 'EventName') else ''
        for key, value in known_turns.items():
            if key in circuit_name or circuit_name in key:
                return value
        
        return "Нет данных"
        
    except:
        return "Нет данных"


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