from flask import Flask, render_template, request, jsonify
import fastf1 as f1
import pandas as pd
import os
from datetime import datetime, timedelta
from database import db, RaceResult, TrackStats, PositionData, CacheStatus
from utils import (get_latest_race, get_team_color, format_time, 
                   get_fastest_lap_driver, calculate_points, 
                   get_formatted_time_for_driver)
from track_utils import get_track_stats
from strategy_utils import save_tyre_strategy_to_db, get_tyre_strategy_from_db, extract_tyre_strategy, get_pitstop_data, get_pitstop_data_from_db, save_pitstop_data_to_db

app = Flask(__name__)

# НАСТРОЙКИ POSTGRESQL 
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:maIam2343PRO@localhost:5432/f1_dashboard'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db.init_app(app)

# Создаем таблицы при первом запуске
with app.app_context():
    db.create_all()
    print("База данных PostgreSQL подключена и таблицы созданы")

# Функции работы с кэшем 

def should_use_cache(data_type, year, event, expire_days=1):
    """Проверяет, можно ли использовать кэшированные данные из БД"""
    cache_status = CacheStatus.query.filter_by(
        data_type=data_type,
        year=year,
        event=event,
        is_valid=True
    ).first()
    
    if not cache_status:
        return False
    
    # Проверяем срок годности кэша
    time_diff = datetime.utcnow() - cache_status.last_updated
    return time_diff < timedelta(days=expire_days)

def update_cache_status(data_type, year, event, is_valid=True):
    """Обновляет статус кэша в таблице CacheStatus"""
    cache_status = CacheStatus.query.filter_by(
        data_type=data_type,
        year=year,
        event=event
    ).first()
    
    if cache_status:
        cache_status.last_updated = datetime.utcnow()
        cache_status.is_valid = is_valid
    else:
        cache_status = CacheStatus(
            data_type=data_type,
            year=year,
            event=event,
            is_valid=is_valid
        )
        db.session.add(cache_status)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка обновления статуса кэша: {e}")

def save_race_results_to_db(year, event, session):
    """Сохраняет результаты гонки в таблицу RaceResult"""
    try:
        print(f"Сохраняем результаты {event} {year} в PostgreSQL...")
        
        # Удаляем старые результаты этой гонки
        RaceResult.query.filter_by(year=year, event=event).delete()
        
        # Определяем пилота с быстрым кругом
        fastest_driver = get_fastest_lap_driver(session)
        
        # Сохраняем каждого гонщика
        for idx, row in session.results.iterrows():
            position = row['Position'] if pd.notna(row['Position']) else None
            driver_name = row['FullName'] if 'FullName' in row and pd.notna(row['FullName']) else 'Unknown'
            driver_number = row['DriverNumber'] if 'DriverNumber' in row and pd.notna(row['DriverNumber']) else ''
            team = row['TeamName'] if 'TeamName' in row and pd.notna(row['TeamName']) else 'Unknown'
            time_value = row['Time'] if 'Time' in row else None
            
            # Получаем аббревиатуру пилота для проверки быстрого круга
            driver_abbr = None
            if 'Abbreviation' in row and pd.notna(row['Abbreviation']):
                driver_abbr = row['Abbreviation']
            
            # Проверяем, есть ли у этого пилота быстрый круг
            has_fastest_lap = False
            if driver_abbr and fastest_driver and driver_abbr == fastest_driver:
                has_fastest_lap = True
            
            # Рассчитываем очки
            points = calculate_points(position, has_fastest_lap)
            
            # Форматируем время отставания
            formatted_time = get_formatted_time_for_driver(session, position, time_value, driver_number)
            
            # Сохраняем в БД
            race_result = RaceResult(
                year=year,
                event=event,
                driver_name=driver_name,
                driver_number=driver_number,
                team=team,
                position=position,
                time=formatted_time,
                points=points,
                fastest_lap=has_fastest_lap,
                status='Finished'
            )
            
            db.session.add(race_result)
        
        # Обновляем статус кэша
        update_cache_status('race_results', year, event, True)
        db.session.commit()
        print(f"Результаты {event} {year} сохранены в PostgreSQL")
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка сохранения результатов в БД: {e}")
        update_cache_status('race_results', year, event, False)

def get_race_results_from_db(year, event):
    """Получает результаты гонки из таблицы RaceResult и возвращает HTML"""
    results = RaceResult.query.filter_by(year=year, event=event)\
        .order_by(RaceResult.position).all()
    
    if not results:
        return None
    
    # Преобразуем в список словарей для таблицы
    results_data = [result.to_dict() for result in results]
    
    # Создаем HTML таблицу
    if results_data:
        df = pd.DataFrame(results_data)
        return df.to_html(index=False, classes='f1-table')
    
    return None

def save_track_stats_to_db(year, event, track_data):
    """Сохраняет статистику трассы в таблицу TrackStats"""
    try:
        print(f"Сохраняем статистику трассы {event} {year} в PostgreSQL...")
        
        # Удаляем старые данные
        TrackStats.query.filter_by(year=year, event=event).delete()
        
        # Сохраняем новые данные
        track_info = track_data.get('track_info', {})
        
        track_stats = TrackStats(
            year=year,
            event=event,
            track_name=track_info.get('name', event),
            country=track_info.get('country', 'Unknown'),
            location=track_info.get('location', 'Unknown'),
            circuit_length=track_data.get('circuit_length', 'Нет данных'),
            turns_count=track_data.get('turns_count', 'Нет данных'),
            coordinates=track_data.get('coordinates', [])
        )
        
        db.session.add(track_stats)
        update_cache_status('track_stats', year, event, True)
        db.session.commit()
        print(f"Статистика трассы {event} {year} сохранена в PostgreSQL")
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка сохранения статистики трассы: {e}")
        update_cache_status('track_stats', year, event, False)

def get_track_stats_from_db(year, event):
    """Получает статистику трассы из таблицы TrackStats"""
    track_stats = TrackStats.query.filter_by(year=year, event=event).first()
    
    if track_stats:
        return track_stats.to_dict()
    
    return None

def save_position_data_to_db(year, event, position_data):
    """Сохраняет данные для графика позиций"""
    try:
        print(f"Сохраняем данные графика {event} {year} в PostgreSQL...")
        
        # Удаляем старые данные
        PositionData.query.filter_by(year=year, event=event).delete()
        
        # Сохраняем новые данные
        for driver_data in position_data:
            position_entry = PositionData(
                year=year,
                event=event,
                driver_code=driver_data['name'],
                positions=driver_data['positions'],
                laps=driver_data['laps'],
                team=driver_data.get('team', ''),
                color=driver_data.get('color', '#CCCCCC')
            )
            db.session.add(position_entry)
        
        update_cache_status('position_data', year, event, True)
        db.session.commit()
        print(f"Данные графика {event} {year} сохранены в PostgreSQL")
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка сохранения данных графика: {e}")
        update_cache_status('position_data', year, event, False)

def get_position_data_from_db(year, event):
    """Получает данные для графика позиций из БД"""
    position_data = PositionData.query.filter_by(year=year, event=event).all()
    
    if not position_data:
        return None
    
    # Преобразуем в формат для Plotly
    data = []
    for entry in position_data:
        data.append({
            'name': entry.driver_code,
            'positions': entry.positions,
            'laps': entry.laps,
            'team': entry.team,
            'color': entry.color
        })
    
    return data


if not os.path.exists('cache'):
    os.makedirs('cache')
f1.Cache.enable_cache('cache')

YEARS = list(range(2018, 2026))

# Маршруты приложений

@app.route('/')
def index():
    year, event = get_latest_race()

    # Пробуем взять результаты из БД
    if should_use_cache('race_results', year, event):
        table_html = get_race_results_from_db(year, event)
        if table_html:
            print(f"Главная страница: используем кэшированные результаты из БД ({event} {year})")
        else:
            table_html = '<p>Нет кэшированных данных</p>'
    else:
        # Если нет в кэше или устарели, загружаем новые
        try:
            session = f1.get_session(year, event, 'R')
            session.load(laps=True)
            
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
            
            # Форматируем время
            formatted_times = []
            for idx, row in results.iterrows():
                position = row['Позиция']
                time_value = row['Время']
                driver_number = row['Номер']
                
                formatted_time = get_formatted_time_for_driver(session, position, time_value, driver_number)
                formatted_times.append(formatted_time)
            
            results['Время'] = formatted_times
            
            table_html = results[['Позиция', 'Имя', 'Номер', 'Команда', 'Время', 'Очки']].to_html(
                index=False, 
                classes='f1-table'
            )
            
            # Сохраняем в БД 
            save_race_results_to_db(year, event, session)
            
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            table_html = f'<p>Не удалось загрузить данные для {event} {year}.</p>'

    # Получаем список гонок для выпадающего меню
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

    # Пробуем взять из БД
    if should_use_cache('race_results', year, event):
        table_html = get_race_results_from_db(year, event)
        if table_html:
            print(f"/results: используем кэшированные данные из БД ({event} {year})")
            return table_html

    # Если нет в кэше или устарели, загружаем и кэшируем
    try:
        session = f1.get_session(year, event, 'R')
        session.load(laps=True)

        results_data = session.results[['Position', 'FullName', 'DriverNumber', 'TeamName', 'Time']]
        
        fastest_driver = get_fastest_lap_driver(session)
        
        points_list = []
        
        for idx, row in results_data.iterrows():
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
        
        results_data['Points'] = points_list
        
        results_data = results_data.rename(columns={
            'Position': 'Позиция',
            'FullName': 'Имя',
            'DriverNumber': 'Номер',
            'TeamName': 'Команда',
            'Time': 'Время',
            'Points': 'Очки'
        })
        
        results_data['Позиция'] = results_data['Позиция'].apply(
            lambda x: int(x) if pd.notna(x) else 'нет информации'
        )
        
        formatted_times = []
        for idx, row in results_data.iterrows():
            position = row['Позиция']
            time_value = row['Время']
            driver_number = row['Номер']
            
            formatted_time = get_formatted_time_for_driver(session, position, time_value, driver_number)
            formatted_times.append(formatted_time)
        
        results_data['Время'] = formatted_times
        
        table_html = results_data[['Позиция', 'Имя', 'Номер', 'Команда', 'Время', 'Очки']].to_html(
            index=False, 
            classes='f1-table'
        )
        
        # Сохраняем в БД
        save_race_results_to_db(year, event, session)
        
    except Exception as e:
        table_html = f'<p>Ошибка: {e}</p>'

    return table_html

@app.route('/positions', methods=['POST'])
def positions():
    year = int(request.form['year'])
    event = request.form['event']

    # Пробуем взять из БД
    if should_use_cache('position_data', year, event):
        position_data = get_position_data_from_db(year, event)
        if position_data:
            print(f"/positions: используем кэшированные данные из БД ({event} {year})")
            return jsonify(position_data)

    # Если нет в кэше, загружаем и кэшируем
    try:
        session = f1.get_session(year, event, 'R')
        session.load(telemetry=False, weather=False, messages=False)

        data = []
        for drv in session.drivers:
            drv_laps = session.laps.pick_drivers(drv)

            if drv_laps.empty:
                continue

            abb = drv_laps['Driver'].iloc[0]
            positions_list = drv_laps['Position'].tolist()
            laps_list = drv_laps['LapNumber'].tolist()

            positions_list = [int(x) if pd.notna(x) else None for x in positions_list]
            
            team = session.results[session.results['DriverNumber'] == drv]['TeamName'].iloc[0]
            color = get_team_color(team)

            data.append({
                'name': abb,
                'positions': positions_list,
                'laps': laps_list,
                'color': color,
                'team': team  
            })

        # Группируем по командам для разных типов линий
        from collections import defaultdict
        team_drivers = defaultdict(list)

        for driver in data:
            team_drivers[driver['team']].append(driver)

        for team, drivers in team_drivers.items():
            for i, driver in enumerate(drivers):
                driver['dash'] = 'solid' if i == 0 else 'dash'

        # Сохраняем в БД
        save_position_data_to_db(year, event, data)

    except Exception as e:
        print(f"Ошибка в /positions: {e}")
        data = []

    return jsonify(data)
 
@app.route('/track_stats', methods=['POST'])
def track_stats():
    """Возвращает статистику трассы из кэша или загружает новую"""
    year = int(request.form['year'])
    event = request.form['event']
    
    # Пробуем взять из БД
    if should_use_cache('track_stats', year, event):
        stats_data = get_track_stats_from_db(year, event)
        if stats_data:
            print(f"/track_stats: используем кэшированные данные из БД ({event} {year})")
            return jsonify(stats_data)
    
    # Если нет в кэше, загружаем и кэшируем
    try:
        stats_data = get_track_stats(year, event)
        
        if stats_data and 'error' not in stats_data:
            # Сохраняем в БД
            save_track_stats_to_db(year, event, stats_data)
        
        return jsonify(stats_data)
    except Exception as e:
        print(f"Ошибка в track_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    """Очищает кэш конкретной гонки из БД"""
    try:
        year = int(request.form['year'])
        event = request.form['event']
        
        # Удаляем данные из всех таблиц
        RaceResult.query.filter_by(year=year, event=event).delete()
        TrackStats.query.filter_by(year=year, event=event).delete()
        PositionData.query.filter_by(year=year, event=event).delete()
        CacheStatus.query.filter_by(year=year, event=event).delete()
        
        db.session.commit()
        
        return jsonify({'message': f'Кэш для {event} {year} очищен из PostgreSQL'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/cache_stats', methods=['GET'])
def cache_stats():
    """Показывает статистику кэша"""
    try:
        race_count = RaceResult.query.count()
        track_count = TrackStats.query.count()
        position_count = PositionData.query.count()
        
        return jsonify({
            'race_results_count': race_count,
            'track_stats_count': track_count,
            'position_data_count': position_count,
            'total_cached_items': race_count + track_count + position_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tyre_strategy', methods=['POST'])
def tyre_strategy():
    """Возвращает данные стратегии по шинам"""
    year = int(request.form['year'])
    event = request.form['event']
    
    # Пробуем взять из БД
    if should_use_cache('tyre_strategy', year, event):
        strategy_data = get_tyre_strategy_from_db(year, event)
        if strategy_data:
            print(f"/tyre_strategy: используем кэшированные данные из БД ({event} {year})")
            return jsonify(strategy_data)
    
    # Если нет в кэше, загружаем и кэшируем
    try:
        session = f1.get_session(year, event, 'R')
        session.load(laps=True)
        
        strategy_data = extract_tyre_strategy(session)
        
        # Сохраняем в БД
        if strategy_data:
            save_tyre_strategy_to_db(year, event, strategy_data)
        
        return jsonify(strategy_data)
        
    except Exception as e:
        print(f"Ошибка в /tyre_strategy: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

@app.route('/pitstop_analysis', methods=['POST'])
def pitstop_analysis():
    """Возвращает данные анализа пит-стопов"""
    year = int(request.form['year'])
    event = request.form['event']
    
    # Пробуем взять из БД
    if should_use_cache('pitstop_data', year, event):
        pitstop_data = get_pitstop_data_from_db(year, event)
        if pitstop_data:
            print(f"/pitstop_analysis: используем кэшированные данные из БД ({event} {year})")
            # Анализируем данные из БД
            return analyze_pitstop_data(pitstop_data)
    
    # Если нет в кэше, загружаем и кэшируем
    try:
        session = f1.get_session(year, event, 'R')
        session.load(laps=True)
        
        # Получаем данные пит-стопов
        pitstop_data = get_pitstop_data(session)
        
        # Сохраняем в БД
        if pitstop_data:
            save_pitstop_data_to_db(year, event, pitstop_data)
        
        # Анализируем и возвращаем
        return analyze_pitstop_data(pitstop_data)
        
    except Exception as e:
        print(f"Ошибка в /pitstop_analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'teams': {}, 'drivers': {}, 'total_pitstops': 0})

def analyze_pitstop_data(pitstop_data):
    """Анализирует данные пит-стопов"""
    team_analysis = {}
    driver_analysis = {}
    
    for pitstop in pitstop_data:
        team = pitstop['team']
        driver = pitstop['driver']
        
        # Анализ по командам
        if team not in team_analysis:
            team_analysis[team] = {
                'total_stops': 0,
                'total_time': 0,
                'avg_time': 0,
                'stops': []
            }
        
        team_analysis[team]['total_stops'] += 1
        team_analysis[team]['total_time'] += pitstop['pitstop_time']
        team_analysis[team]['stops'].append({
            'driver': driver,
            'time': pitstop['pitstop_time'],
            'lap': pitstop['lap']
        })
        
        # Анализ по гонщикам
        if driver not in driver_analysis:
            driver_analysis[driver] = {
                'team': team,
                'total_stops': 0,
                'stops': []
            }
        
        driver_analysis[driver]['total_stops'] += 1
        driver_analysis[driver]['stops'].append({
            'time': pitstop['pitstop_time'],
            'lap': pitstop['lap'],
            'compound': pitstop['compound']
        })
    
    # Рассчитываем среднее время для команд
    for team in team_analysis:
        if team_analysis[team]['total_stops'] > 0:
            team_analysis[team]['avg_time'] = (
                team_analysis[team]['total_time'] / team_analysis[team]['total_stops']
            )
    
    return jsonify({
        'teams': team_analysis,
        'drivers': driver_analysis,
        'total_pitstops': len(pitstop_data)
    })
    
    
if __name__ == '__main__':
    app.run(debug=True)