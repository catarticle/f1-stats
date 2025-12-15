from flask import Flask, render_template, request, jsonify
import fastf1 as f1
import pandas as pd
import os
from utils import (get_latest_race, get_team_color, format_time, 
                   get_fastest_lap_driver, calculate_points, 
                   get_formatted_time_for_driver)
from track_utils import get_track_stats

app = Flask(__name__)

if not os.path.exists('cache'):
    os.makedirs('cache')

f1.Cache.enable_cache('cache')

YEARS = list(range(2018, 2026))

@app.route('/')
def index():
    year, event = get_latest_race()

    try:
        session = f1.get_session(year, event, 'R')
        session.load(laps=True)
    except Exception as e:
        table_html = f'<p>Не удалось загрузить данные для {event} {year}. Попробуйте другую гонку.</p>'
    else:
        results = session.results[['Position', 'FullName', 'DriverNumber', 'TeamName', 'Time']]
        
        # Определяем пилота с быстрым кругом
        fastest_driver = get_fastest_lap_driver(session)
        
        # Добавляем колонку с очками
        points_list = []
        
        for idx, row in results.iterrows():
            position = row['Position']
            driver_abbr = None
            
            try:
                driver_number = row['DriverNumber']
                driver_info = session.results[session.results['DriverNumber'] == driver_number]
                if not driver_info.empty:
                    driver_abbr = driver_info.iloc[0]['Abbreviation']
            except:
                pass
            
            has_fastest_lap = False
            if driver_abbr and fastest_driver and driver_abbr == fastest_driver:
                has_fastest_lap = True
            
            points = calculate_points(position, has_fastest_lap)
            points_list.append(points)
        
        results['Points'] = points_list
        
        results = results.rename(columns={
            'Position': 'Позиция',
            'FullName': 'Имя',
            'DriverNumber': 'Номер',
            'TeamName': 'Команда',
            'Time': 'Время',
            'Points': 'Очки'
        })
        
        results['Позиция'] = results['Позиция'].apply(
            lambda x: int(x) if pd.notna(x) else 'нет информации'
        )
        
        # Используем новую функцию для форматирования времени
        formatted_times = []
        for idx, row in results.iterrows():
            position = row['Позиция']
            time_value = row['Время']
            driver_number = row['Номер']
            
            # Используем новую функцию для форматирования времени
            formatted_time = get_formatted_time_for_driver(session, position, time_value, driver_number)
            formatted_times.append(formatted_time)
        
        results['Время'] = formatted_times
        
        table_html = results[['Позиция', 'Имя', 'Номер', 'Команда', 'Время', 'Очки']].to_html(
            index=False, 
            classes='f1-table'
        )

    try:
        schedule = f1.get_event_schedule(year)
        events = schedule[schedule['EventName'] != 'Test']['EventName'].tolist()
    except:
        events = [event]

    return render_template('index.html', 
                         years=YEARS, 
                         current_year=year, 
                         current_event=event, 
                         events=events, 
                         table_html=table_html)

@app.route('/events', methods=['GET'])
def get_events():
    year = int(request.args.get('year', 2024))
    try:
        schedule = f1.get_event_schedule(year)
        events = schedule[schedule['EventName'] != 'Test']['EventName'].tolist()
    except:
        events = []
    return jsonify(events)

@app.route('/results', methods=['POST'])
def results():
    year = int(request.form['year'])
    event = request.form['event']

    try:
        session = f1.get_session(year, event, 'R')
        session.load(laps=True)  # Загружаем круги для определения быстрого круга

        results = session.results[['Position', 'FullName', 'DriverNumber', 'TeamName', 'Time']]
        
        # Определяем пилота с быстрым кругом
        fastest_driver = get_fastest_lap_driver(session)
        
        # Добавляем колонку с очками
        points_list = []
        
        for idx, row in results.iterrows():
            position = row['Position']
            driver_abbr = None
            
            # Получаем аббревиатуру пилота для проверки быстрого круга
            try:
                # Ищем аббревиатуру в результатах
                driver_number = row['DriverNumber']
                driver_info = session.results[session.results['DriverNumber'] == driver_number]
                if not driver_info.empty:
                    driver_abbr = driver_info.iloc[0]['Abbreviation']
            except:
                pass
            
            # Проверяем, есть ли у этого пилота быстрый круг
            has_fastest_lap = False
            if driver_abbr and fastest_driver and driver_abbr == fastest_driver:
                has_fastest_lap = True
            
            # Рассчитываем очки
            points = calculate_points(position, has_fastest_lap)
            points_list.append(points)
        
        results['Points'] = points_list
        
        # Переименовываем колонки
        results = results.rename(columns={
            'Position': 'Позиция',
            'FullName': 'Имя',
            'DriverNumber': 'Номер',
            'TeamName': 'Команда',
            'Time': 'Время',
            'Points': 'Очки'
        })
        
        # Форматируем позицию
        results['Позиция'] = results['Позиция'].apply(
            lambda x: int(x) if pd.notna(x) else 'нет информации'
        )
        
        # Используем новую функцию для форматирования времени
        formatted_times = []
        for idx, row in results.iterrows():
            position = row['Позиция']
            time_value = row['Время']
            driver_number = row['Номер']
            
            # Используем новую функцию для форматирования времени
            formatted_time = get_formatted_time_for_driver(session, position, time_value, driver_number)
            formatted_times.append(formatted_time)
        
        results['Время'] = formatted_times
        
        # Упорядочиваем колонки
        table_html = results[['Позиция', 'Имя', 'Номер', 'Команда', 'Время', 'Очки']].to_html(
            index=False, 
            classes='f1-table'
        )

    except Exception as e:
        table_html = f'<p>Ошибка: {e}</p>'

    return table_html

@app.route('/positions', methods=['POST'])
def positions():
    year = int(request.form['year'])
    event = request.form['event']

    try:
        session = f1.get_session(year, event, 'R')
        session.load(telemetry=False, weather=False, messages=False)

        data = []
        for drv in session.drivers:
            drv_laps = session.laps.pick_drivers(drv)

            if drv_laps.empty:
                continue

            abb = drv_laps['Driver'].iloc[0]
            positions = drv_laps['Position'].tolist()
            laps = drv_laps['LapNumber'].tolist()

            positions = [int(x) if pd.notna(x) else None for x in positions]
            
            team = session.results[session.results['DriverNumber'] == drv]['TeamName'].iloc[0]
            color = get_team_color(team)

            data.append({
                'name': abb,
                'positions': positions,
                'laps': laps,
                'color': color,
                'team': team  
            })

        from collections import defaultdict
        team_drivers = defaultdict(list)

        for driver in data:
            team_drivers[driver['team']].append(driver)

        for team, drivers in team_drivers.items():
            for i, driver in enumerate(drivers):
                driver['dash'] = 'solid' if i == 0 else 'dash'

    except Exception as e:
        print(f"Ошибка в /positions: {e}")
        data = []

    return jsonify(data)
 
@app.route('/track_stats', methods=['POST'])
def track_stats():
    """Возвращает статистику трассы"""
    year = int(request.form['year'])
    event = request.form['event']
    
    try:
        stats_data = get_track_stats(year, event)
        return jsonify(stats_data)
    except Exception as e:
        print(f"Ошибка в track_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})  

if __name__ == '__main__':
    app.run(debug=True)