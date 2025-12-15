from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class RaceResult(db.Model):
    """Результаты конкретной гонки"""
    __tablename__ = 'race_results'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    event = db.Column(db.String(200), nullable=False, index=True)
    driver_name = db.Column(db.String(100), nullable=False)
    driver_number = db.Column(db.String(10))
    team = db.Column(db.String(100))
    position = db.Column(db.Integer)
    time = db.Column(db.String(50))
    points = db.Column(db.Integer, default=0)
    fastest_lap = db.Column(db.Boolean, default=False)
    laps_behind = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Finished')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Составной уникальный ключ
    __table_args__ = (
        db.UniqueConstraint('year', 'event', 'driver_name', name='unique_race_result'),
    )
    
    def to_dict(self):
        return {
            'Позиция': self.position if self.position else 'нет информации',
            'Имя': self.driver_name,
            'Номер': self.driver_number,
            'Команда': self.team,
            'Время': self.time,
            'Очки': self.points
        }

class TrackStats(db.Model):
    """Статистика трасс"""
    __tablename__ = 'track_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    event = db.Column(db.String(200), nullable=False, index=True)
    track_name = db.Column(db.String(200))
    country = db.Column(db.String(100))
    location = db.Column(db.String(200))
    circuit_length = db.Column(db.String(50))
    turns_count = db.Column(db.Integer)
    coordinates_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('year', 'event', name='unique_track_stats'),
    )
    
    @property
    def coordinates(self):
        if self.coordinates_json:
            return json.loads(self.coordinates_json)
        return []
    
    @coordinates.setter
    def coordinates(self, value):
        self.coordinates_json = json.dumps(value if value else [])
    
    def to_dict(self):
        return {
            'track_info': {
                'name': self.track_name,
                'country': self.country,
                'location': self.location,
                'event_name': self.event
            },
            'circuit_length': self.circuit_length,
            'turns_count': str(self.turns_count) if self.turns_count else 'Нет данных',
            'coordinates': self.coordinates,
            'year': self.year
        }

class PositionData(db.Model):
    """Данные для графика позиций"""
    __tablename__ = 'position_data'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    event = db.Column(db.String(200), nullable=False, index=True)
    driver_code = db.Column(db.String(10), nullable=False)
    positions_json = db.Column(db.Text)  # JSON список позиций
    laps_json = db.Column(db.Text)       # JSON список кругов
    team = db.Column(db.String(100))
    color = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('year', 'event', 'driver_code', name='unique_position_data'),
    )
    
    @property
    def positions(self):
        if self.positions_json:
            return json.loads(self.positions_json)
        return []
    
    @positions.setter
    def positions(self, value):
        self.positions_json = json.dumps(value if value else [])
    
    @property
    def laps(self):
        if self.laps_json:
            return json.loads(self.laps_json)
        return []
    
    @laps.setter
    def laps(self, value):
        self.laps_json = json.dumps(value if value else [])

class CacheStatus(db.Model):
    """Статус кэширования"""
    __tablename__ = 'cache_status'
    
    id = db.Column(db.Integer, primary_key=True)
    data_type = db.Column(db.String(50), nullable=False)  # 'race_results', 'track_stats', 'positions'
    year = db.Column(db.Integer, nullable=False)
    event = db.Column(db.String(200), nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_valid = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('data_type', 'year', 'event', name='unique_cache_status'),
    )