from datetime import datetime
from .database import db

class WorkoutSession(db.Model):
    __tablename__ = 'workout_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    exercise_key = db.Column(db.String(50), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    reps = db.Column(db.Integer, default=0)
    calories = db.Column(db.Float, default=0.0)
    duration_seconds = db.Column(db.Integer, default=0)
    
    # New fields for advanced tracking
    form_score = db.Column(db.Float, nullable=True)  # Average form score (0-100)
    set_number = db.Column(db.Integer, default=1)
    weight_used = db.Column(db.Float, nullable=True)  # For weighted exercises
    notes = db.Column(db.Text, nullable=True)
    
    # Video metadata (if recording)
    video_url = db.Column(db.String(500), nullable=True)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'exercise': self.exercise_key,
            'exercise_name': self.exercise_name,
            'reps': self.reps,
            'calories': round(self.calories, 2),
            'duration': self.duration_seconds,
            'form_score': self.form_score,
            'set_number': self.set_number,
            'weight_used': self.weight_used,
            'timestamp': self.timestamp.isoformat(),
            'date': self.timestamp.strftime('%Y-%m-%d')
        }
    
    def to_summary(self):
        return {
            'reps': self.reps,
            'calories': self.calories,
            'exercise': self.exercise_name,
            'date': self.timestamp.strftime('%Y-%m-%d %H:%M')
        }

class ExerciseStat(db.Model):
    """Track user's performance per exercise over time"""
    __tablename__ = 'exercise_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    exercise_key = db.Column(db.String(50), nullable=False)
    
    total_reps = db.Column(db.Integer, default=0)
    total_sessions = db.Column(db.Integer, default=0)
    total_calories = db.Column(db.Float, default=0.0)
    max_reps_in_session = db.Column(db.Integer, default=0)
    average_form_score = db.Column(db.Float, default=0.0)
    
    last_performed = db.Column(db.DateTime, nullable=True)
    personal_best = db.Column(db.Integer, default=0)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'exercise_key', name='unique_user_exercise'),
    )