from flask import Flask, render_template, request, jsonify
import fastf1 as f1
import pandas as pd
import os
from utils import get_latest_race, get_team_color, format_time

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
        session.load()
    except Exception as e:
        table_html = f'<p>Не удалось загрузить данные для {event} {year}. Попробуйте другую гонку.</p>'
    else:
        results = session.results[['Position', 'FullName', 'DriverNumber', 'TeamName', 'Time']]
        results = results.rename(columns={
            'Position': 'Позиция',
            'FullName': 'Имя',
            'DriverNumber': 'Номер',
            'TeamName': 'Команда',
            'Time': 'Время'
        })
        # Преобразуем Позицию в целые числа
        results['Позиция'] = results['Позиция'].apply(lambda x: int(x) if pd.notna(x) else 'нет информации')
        # Форматируем время
        results['Время'] = results['Время'].apply(format_time)

        table_html = results.to_html(index=False, classes='f1-table')

    # Получаем список гонок для текущего года
    try:
        schedule = f1.get_event_schedule(year)
        events = schedule[schedule['EventName'] != 'Test']['EventName'].tolist()
    except:
        events = [event]

    return render_template('index.html', years=YEARS, current_year=year, current_event=event, events=events, table_html=table_html)

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
        session.load()

        results = session.results[['Position', 'FullName', 'DriverNumber', 'TeamName', 'Time']]
        results = results.rename(columns={
            'Position': 'Позиция',
            'FullName': 'Имя',
            'DriverNumber': 'Номер',
            'TeamName': 'Команда',
            'Time': 'Время'
        })
        # Преобразуем Позицию в целые числа
        results['Позиция'] = results['Позиция'].apply(lambda x: int(x) if pd.notna(x) else 'нет информации')
        # Форматируем время
        results['Время'] = results['Время'].apply(format_time)

        table_html = results.to_html(index=False, classes='f1-table')

    except Exception as e:
        table_html = f'<p>Ошибка: {e}</p>'

    return table_html

@app.route('/replay', methods=['POST'])
def replay():
    year = int(request.form['year'])
    event = request.form['event']

    try:
        session = f1.get_session(year, event, 'R')
        session.load(laps=False, telemetry=False, weather=False, messages=False)

        # Получаем список пилотов
        drivers = session.results[['DriverNumber', 'FullName', 'TeamName', 'Position']].dropna()
        drivers = drivers.rename(columns={'FullName': 'Имя', 'TeamName': 'Команда', 'DriverNumber': 'Номер'})

        # Пример: распределяем пилотов по кругу
        import math
        driver_list = []
        n = len(drivers)
        for i, (idx, row) in enumerate(drivers.iterrows()):
            angle = (i / n) * 2 * math.pi  # угол на круге
            team = row['Команда']
            color = get_team_color(team)
            # Берём фамилию — если есть пробел, берём последнее слово
            full_name = row['Имя']
            surname = full_name.split()[-1] if ' ' in full_name else full_name
            name = surname[:3]
            driver_list.append({
                'name': name,
                'color': color,
                'angle': angle
            })

    except Exception as e:
        driver_list = []

    return jsonify(driver_list)

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

            # Заменяем NaN на None (который станет null в JSON)
            positions = [int(x) if pd.notna(x) else None for x in positions]
            
            from utils import get_team_color
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

if __name__ == '__main__':
    app.run(debug=True)