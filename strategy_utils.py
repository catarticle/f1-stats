import fastf1 as f1
import pandas as pd
import json
from datetime import datetime
from database import TyreStrategy, CacheStatus, db, PitstopData

def save_tyre_strategy_to_db(year, event, strategy_data):
    """Сохраняет данные стратегии по шинам"""
    try:
        print(f"Сохраняем стратегию {event} {year} в PostgreSQL...")
        
        # Удаляем старые данные
        TyreStrategy.query.filter_by(year=year, event=event).delete()
        
        # Сохраняем новые данные
        for driver_data in strategy_data:
            tyre_strategy = TyreStrategy(
                year=year,
                event=event,
                driver_code=driver_data['driver'],
                stints=driver_data['stints']
            )
            db.session.add(tyre_strategy)
        
        # Обновляем статус кэша
        from app import update_cache_status
        update_cache_status('tyre_strategy', year, event, True)
        
        db.session.commit()
        print(f"Стратегия {event} {year} сохранена в PostgreSQL")
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка сохранения стратегии: {e}")
        from app import update_cache_status
        update_cache_status('tyre_strategy', year, event, False)

def get_tyre_strategy_from_db(year, event):
    """Получает данные стратегии из БД"""
    strategy_data = TyreStrategy.query.filter_by(year=year, event=event).all()
    
    if not strategy_data:
        return None
    
    # Преобразуем в нужный формат
    data = []
    for entry in strategy_data:
        data.append({
            'driver': entry.driver_code,
            'stints': entry.stints
        })
    
    return data

def extract_tyre_strategy(session):
    """Извлекает данные стратегии по шинам из сессии FastF1"""
    try:
        print(f"DEBUG: Извлечение стратегии из FastF1")
        
        if session.laps is None or session.laps.empty:
            print("DEBUG: Нет данных кругов")
            return []
        
        laps = session.laps
        print(f"DEBUG: Всего кругов: {len(laps)}")
        print(f"DEBUG: Уникальные гонщики: {laps['Driver'].unique()}")
        
        # Проверяем наличие нужных колонок
        if 'Compound' not in laps.columns or 'Stint' not in laps.columns:
            print("DEBUG: Нет колонок Compound или Stint")
            return []
        
        # Получаем уникальных гонщиков
        drivers = laps['Driver'].unique()
        print(f"DEBUG: Найдено гонщиков: {len(drivers)}")
        
        # Собираем данные стратегии для каждого гонщика
        strategy_data = []
        
        for driver in drivers:
            # Получаем круги гонщика
            driver_laps = laps[laps['Driver'] == driver].copy()
            
            if driver_laps.empty:
                continue
            
            # Сортируем по номеру круга
            driver_laps = driver_laps.sort_values('LapNumber')
            
            # Группируем по стендам и составу
            stints = []
            current_stint = None
            current_compound = None
            stint_start_lap = 0
            stint_length = 0
            
            for idx, lap in driver_laps.iterrows():
                lap_num = lap['LapNumber']
                compound = lap['Compound'] if pd.notna(lap['Compound']) else 'UNKNOWN'
                stint = lap['Stint'] if pd.notna(lap['Stint']) else 1
                
                # Если это первый круг или сменился стенд/состав
                if current_stint is None or stint != current_stint or compound != current_compound:
                    # Сохраняем предыдущий стенд если он есть
                    if current_stint is not None and stint_length > 0:
                        stints.append({
                            'compound': current_compound,
                            'stint_length': stint_length,
                            'start_lap': stint_start_lap,
                            'end_lap': stint_start_lap + stint_length - 1
                        })
                    
                    # Начинаем новый стенд
                    current_stint = stint
                    current_compound = compound
                    stint_start_lap = lap_num
                    stint_length = 1
                else:
                    # Продолжаем текущий стенд
                    stint_length += 1
            
            # Добавляем последний стенд
            if current_stint is not None and stint_length > 0:
                stints.append({
                    'compound': current_compound,
                    'stint_length': stint_length,
                    'start_lap': stint_start_lap,
                    'end_lap': stint_start_lap + stint_length - 1
                })
            
            # Получаем аббревиатуру гонщмка из сессии
            try:
                # Ищем номер гонщика
                driver_number = driver_laps['DriverNumber'].iloc[0] if 'DriverNumber' in driver_laps.columns else None
                if driver_number:
                    driver_info = session.get_driver(driver_number)
                    driver_abbr = driver_info["Abbreviation"]
                else:
                    driver_abbr = driver
            except:
                driver_abbr = driver
            
            if stints:
                total_laps = sum(stint['stint_length'] for stint in stints)
                print(f"DEBUG: Гонщик {driver_abbr}: {len(stints)} стендов, {total_laps} кругов")
                
                strategy_data.append({
                    'driver': driver_abbr,
                    'stints': stints,
                    'total_laps': total_laps
                })
        
        print(f"DEBUG: Собрано стратегий: {len(strategy_data)}")
        
        # Отладочный вывод первых 3 стратегий
        for i, data in enumerate(strategy_data[:3]):
            print(f"DEBUG: Стратегия {i+1} - {data['driver']}:")
            for stint in data['stints']:
                print(f"  - {stint['compound']}: круги {stint['start_lap']}-{stint['end_lap']} ({stint['stint_length']}L)")
        
        return strategy_data
        
    except Exception as e:
        print(f"Ошибка извлечения стратегии: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_pitstop_data(session):
    """Извлекает данные пит-стопов из сессии FastF1"""
    try:
        print(f"Извлечение пит-стопов для {session.event['EventName']}")
        
        if session.laps is None or session.laps.empty:
            print("Нет данных кругов")
            return []
        
        laps = session.laps
        pitstop_data = []
        
        print(f"Всего кругов в сессии: {len(laps)}")
        print(f"Уникальные гонщики: {laps['Driver'].unique()}")
        
        # Способ 1: Ищем круги с PitOutTime (выезд из пит-лейна)
        print("\nПоиск пит-стопов по PitOutTime...")
        if 'PitOutTime' in laps.columns:
            pit_out_laps = laps[laps['PitOutTime'].notna()].copy()
            print(f"Найдено кругов с PitOutTime: {len(pit_out_laps)}")
            
            if not pit_out_laps.empty:
                # Покажем несколько примеров
                print("Примеры кругов с PitOutTime:")
                for idx, lap in pit_out_laps.head(5).iterrows():
                    print(f"  Гонщик: {lap['Driver']}, Круг: {lap['LapNumber']}, PitOutTime: {lap['PitOutTime']}")
        
        # Способ 2: Ищем круги с PitInTime (въезд в пит-лейн)
        print("\nПоиск пит-стопов по PitInTime...")
        if 'PitInTime' in laps.columns:
            pit_in_laps = laps[laps['PitInTime'].notna()].copy()
            print(f"Найдено кругов с PitInTime: {len(pit_in_laps)}")
            
            if not pit_in_laps.empty:
                print("Примеры кругов с PitInTime:")
                for idx, lap in pit_in_laps.head(5).iterrows():
                    print(f"  Гонщик: {lap['Driver']}, Круг: {lap['LapNumber']}, PitInTime: {lap['PitInTime']}")
        
        # Основной способ: находим пит-стопы по смене стендов (Stint)
        print("\nПоиск пит-стопов по смене стендов (Stint)...")
        
        if 'Stint' in laps.columns:
            # Для каждого гонщика
            for driver in sorted(laps['Driver'].unique()):
                driver_laps = laps[laps['Driver'] == driver].copy()
                driver_laps = driver_laps.sort_values('LapNumber')
                
                print(f"\nГонщик {driver}:")
                print(f"  Всего кругов: {len(driver_laps)}")
                print(f"  Стенды: {sorted(driver_laps['Stint'].dropna().unique())}")
                
                # Создаем список стендов
                stints = []
                for _, lap in driver_laps.iterrows():
                    stint_num = int(lap['Stint']) if pd.notna(lap['Stint']) else 1
                    lap_num = int(lap['LapNumber']) if pd.notna(lap['LapNumber']) else 0
                    stints.append((lap_num, stint_num))
                
                # Находим смены стендов (пит-стопы)
                pitstops_for_driver = []
                prev_stint = None
                pitstop_lap = None
                
                for lap_num, stint_num in stints:
                    if prev_stint is not None and stint_num != prev_stint:
                        # Нашли смену стенда на этом круге
                        pitstop_lap = lap_num
                        
                        # Ищем реальное время пит-стопа
                        pitstop_time_seconds = 2.5  # значение по умолчанию
                        
                        # Пробуем найти реальное время
                        pit_lap_data = driver_laps[driver_laps['LapNumber'] == lap_num]
                        if not pit_lap_data.empty:
                            pit_lap = pit_lap_data.iloc[0]
                            
                            # Если есть PitInTime и PitOutTime на предыдущем/следующем круге
                            if pd.notna(pit_lap.get('PitOutTime')):
                                # Это круг выезда из пит-лейна
                                # Ищем круг въезда
                                in_lap_num = lap_num - 1
                                in_lap_data = driver_laps[driver_laps['LapNumber'] == in_lap_num]
                                
                                if not in_lap_data.empty:
                                    in_lap = in_lap_data.iloc[0]
                                    if pd.notna(in_lap.get('PitInTime')) and pd.notna(pit_lap.get('PitOutTime')):
                                        try:
                                            pitstop_time = pit_lap['PitOutTime'] - in_lap['PitInTime']
                                            pitstop_time_seconds = pitstop_time.total_seconds()
                                            print(f"  Найден пит-стоп: круг {in_lap_num}->{lap_num}, время: {pitstop_time_seconds:.2f}с")
                                        except:
                                            pass
                        
                        pitstops_for_driver.append({
                            'lap': pitstop_lap,
                            'from_stint': prev_stint,
                            'to_stint': stint_num,
                            'time': pitstop_time_seconds
                        })
                        
                        print(f"  Пит-стоп: круг {pitstop_lap}, стенд {prev_stint}->{stint_num}")
                    
                    prev_stint = stint_num
                
                # Сохраняем данные для этого гонщика
                for pitstop in pitstops_for_driver:
                    # Находим данные для этого круга
                    lap_data = driver_laps[driver_laps['LapNumber'] == pitstop['lap']]
                    if not lap_data.empty:
                        lap_row = lap_data.iloc[0]
                        
                        pitstop_data.append({
                            'driver': str(driver),
                            'team': str(lap_row['Team']) if 'Team' in lap_row and pd.notna(lap_row['Team']) else 'Unknown',
                            'lap': int(pitstop['lap']),
                            'pitstop_time': pitstop['time'],
                            'compound': str(lap_row['Compound']) if pd.notna(lap_row['Compound']) else 'UNKNOWN',
                            'stint': int(pitstop['to_stint'])
                        })
        
        print(f"\nИтого найдено пит-стопов: {len(pitstop_data)}")
        
        if pitstop_data:
            print("\nСписок найденных пит-стопов:")
            for stop in pitstop_data:
                print(f"  {stop['driver']} ({stop['team']}): круг {stop['lap']}, {stop['pitstop_time']:.2f}с, стенд {stop['stint']}")
        
        # Сортируем по кругу
        pitstop_data.sort(key=lambda x: x['lap'])
        
        return pitstop_data
        
    except Exception as e:
        print(f"Ошибка извлечения пит-стопов: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_pitstop_data_to_db(year, event, pitstop_data):
    """Сохраняет данные пит-стопов в таблицу PitstopData"""
    try:
        print(f"Сохраняем пит-стопы {event} {year} в PostgreSQL...")
        
        # Удаляем старые данные
        PitstopData.query.filter_by(year=year, event=event).delete()
        
        # Сохраняем новые данные
        for pitstop in pitstop_data:
            pitstop_entry = PitstopData(
                year=year,
                event=event,
                driver_code=pitstop['driver'],
                team=pitstop['team'],
                lap=pitstop['lap'],
                pitstop_time=pitstop['pitstop_time'],
                compound=pitstop['compound'],
                stint=pitstop['stint']
            )
            db.session.add(pitstop_entry)
        
        # Обновляем статус кэша
        from app import update_cache_status
        update_cache_status('pitstop_data', year, event, True)
        
        db.session.commit()
        print(f"Пит-стопы {event} {year} сохранены в PostgreSQL")
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка сохранения пит-стопов: {e}")
        from app import update_cache_status
        update_cache_status('pitstop_data', year, event, False)

def get_pitstop_data_from_db(year, event):
    """Получает данные пит-стопов из БД"""
    pitstop_entries = PitstopData.query.filter_by(year=year, event=event).all()
    
    if not pitstop_entries:
        return None
    
    # Преобразуем в нужный формат
    data = []
    for entry in pitstop_entries:
        data.append({
            'driver': entry.driver_code,
            'team': entry.team,
            'lap': entry.lap,
            'pitstop_time': entry.pitstop_time,
            'compound': entry.compound,
            'stint': entry.stint
        })
    
    return data
