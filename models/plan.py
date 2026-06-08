from datetime import datetime
from .database import db

class WorkoutPlan(db.Model):
    __tablename__ = 'workout_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    plan_date = db.Column(db.Date, nullable=False, index=True)
    focus = db.Column(db.String(50), nullable=False)  # Full Body, Upper, Lower, Cardio, Rest
    
    # JSON field for exercises (MySQL 5.7+ with JSON support)
    exercises = db.Column(db.JSON, nullable=True)  # [{name, sets, reps, weight}]
    
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'plan_date', name='unique_user_plan_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.plan_date.isoformat(),
            'focus': self.focus,
            'exercises': self.exercises or [],
            'completed': self.completed,
            'notes': self.notes
        }

class NutritionLog(db.Model):
    """Track daily nutrition (bonus feature)"""
    __tablename__ = 'nutrition_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    log_date = db.Column(db.Date, nullable=False, index=True)
    meal_type = db.Column(db.String(50))  # Breakfast, Lunch, Dinner, Snack
    food_name = db.Column(db.String(200))
    calories = db.Column(db.Integer)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fats = db.Column(db.Float)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_user_date', 'user_id', 'log_date'),
    )