from flask import Blueprint, request, jsonify, session, render_template
from flask_socketio import emit
from models.workout import WorkoutSession, ExerciseStat
from models.user import User
from models.database import db
from services.workout_service import WorkoutService
from services.pose_detection import PoseDetector, EXERCISE_CONFIGS
from utils.decorators import login_required, rate_limit
from datetime import datetime
import time

workout_bp = Blueprint('workout', __name__)

# Global state management (will be moved to Redis for production)
active_workouts = {}

class WorkoutSessionManager:
    """Manages active workout sessions per user"""
    
    def __init__(self):
        self.sessions = {}
    
    def get_or_create(self, user_id):
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'exercise': 'none',
                'reps': 0,
                'calories': 0.0,
                'start_time': None,
                'stage': None,
                'current_form_score': 0.0,
                'feedback': 'Select an exercise',
                'session_id': None
            }
        return self.sessions[user_id]
    
    def update(self, user_id, **kwargs):
        if user_id in self.sessions:
            self.sessions[user_id].update(kwargs)
    
    def reset(self, user_id):
        if user_id in self.sessions:
            self.sessions[user_id] = {
                'exercise': 'none',
                'reps': 0,
                'calories': 0.0,
                'start_time': None,
                'stage': None,
                'current_form_score': 0.0,
                'feedback': 'Select an exercise',
                'session_id': None
            }
    
    def save_session(self, user_id):
        """Save current workout to database"""
        session_data = self.sessions.get(user_id)
        if not session_data or session_data['reps'] == 0:
            return False
        
        # Don't save very short sessions (less than 15 seconds for plank, 3 reps for others)
        duration = int(time.time() - session_data['start_time']) if session_data['start_time'] else 0
        if session_data['exercise'] == 'plank' and duration < 15:
            return False
        if session_data['exercise'] != 'plank' and session_data['reps'] < 3:
            return False
        
        workout = WorkoutSession(
            user_id=user_id,
            exercise_key=session_data['exercise'],
            exercise_name=EXERCISE_CONFIGS.get(session_data['exercise'], {}).get('name', 'Unknown'),
            reps=session_data['reps'],
            calories=round(session_data['calories'], 2),
            duration_seconds=duration,
            form_score=session_data.get('current_form_score', 0)
        )
        
        db.session.add(workout)
        
        # Update exercise stats
        stats = ExerciseStat.query.filter_by(
            user_id=user_id, 
            exercise_key=session_data['exercise']
        ).first()
        
        if not stats:
            stats = ExerciseStat(user_id=user_id, exercise_key=session_data['exercise'])
            db.session.add(stats)
        
        stats.total_reps += session_data['reps']
        stats.total_sessions += 1
        stats.total_calories += workout.calories
        stats.last_performed = datetime.utcnow()
        
        if session_data['reps'] > stats.max_reps_in_session:
            stats.max_reps_in_session = session_data['reps']
        
        db.session.commit()
        
        return True

session_manager = WorkoutSessionManager()
pose_detector = None  # Will initialize with config

@workout_bp.route('/workout')
@login_required
def workout_page(current_user):
    """Render workout page"""
    exercises = [{"key": k, "name": v.name} for k, v in EXERCISE_CONFIGS.items()]
    return render_template('workout.html', exercises=exercises, user=current_user)

@workout_bp.route('/api/set_exercise', methods=['POST'])
@login_required
@rate_limit(limit=10, per=60)  # 10 requests per minute
def set_exercise(current_user):
    """Start a new exercise"""
    data = request.get_json()
    exercise = data.get('exercise')
    
    if exercise not in EXERCISE_CONFIGS:
        return jsonify({'error': 'Invalid exercise'}), 400
    
    # Save previous session if exists
    session_manager.save_session(current_user.id)
    
    # Start new session
    session_manager.sessions[current_user.id] = {
        'exercise': exercise,
        'reps': 0,
        'calories': 0.0,
        'start_time': time.time(),
        'stage': None,
        'current_form_score': 0.0,
        'feedback': 'Start your workout!',
        'session_id': None
    }
    
    return jsonify({
        'success': True,
        'exercise': exercise,
        'message': f'Started {EXERCISE_CONFIGS[exercise].name}'
    })

@workout_bp.route('/api/get_stats')
@login_required
def get_stats(current_user):
    """Get current workout stats"""
    session_data = session_manager.get_or_create(current_user.id)
    
    duration = 0
    if session_data.get('start_time'):
        duration = int(time.time() - session_data['start_time'])
    
    return jsonify({
        'exercise': session_data['exercise'],
        'reps': session_data['reps'],
        'calories': round(session_data['calories'], 2),
        'duration': duration,
        'form_feedback': session_data.get('feedback', 'Ready'),
        'form_score': session_data.get('current_form_score', 0),
        'stage': session_data.get('stage')
    })

@workout_bp.route('/api/reset_workout', methods=['POST'])
@login_required
def reset_workout(current_user):
    """Reset current workout"""
    session_manager.save_session(current_user.id)
    session_manager.reset(current_user.id)
    
    return jsonify({'success': True, 'message': 'Workout reset'})

@workout_bp.route('/api/get_history')
@login_required
def get_history(current_user):
    """Get workout history"""
    history = WorkoutSession.query.filter_by(user_id=current_user.id)\
        .order_by(WorkoutSession.timestamp.desc())\
        .limit(50)\
        .all()
    
    return jsonify([h.to_dict() for h in history])

@workout_bp.route('/api/get_full_report')
@login_required
def get_full_report(current_user):
    """Get comprehensive workout report"""
    workouts = WorkoutSession.query.filter_by(user_id=current_user.id).all()
    stats = ExerciseStat.query.filter_by(user_id=current_user.id).all()
    
    total_reps = sum(w.reps for w in workouts)
    total_calories = sum(w.calories for w in workouts)
    total_sessions = len(workouts)
    
    # Most frequent exercise
    exercise_counts = {}
    for w in workouts:
        exercise_counts[w.exercise_key] = exercise_counts.get(w.exercise_key, 0) + 1
    
    most_frequent = max(exercise_counts, key=exercise_counts.get) if exercise_counts else "None"
    
    # Weekly progress
    weekly_data = {}
    for w in workouts:
        week_key = w.timestamp.strftime('%Y-W%W')
        if week_key not in weekly_data:
            weekly_data[week_key] = {'reps': 0, 'calories': 0}
        weekly_data[week_key]['reps'] += w.reps
        weekly_data[week_key]['calories'] += w.calories
    
    return jsonify({
        'user_name': current_user.name,
        'report_date': datetime.utcnow().strftime('%Y-%m-%d'),
        'total_sessions': total_sessions,
        'total_reps': total_reps,
        'total_calories': round(total_calories, 2),
        'most_frequent_exercise': EXERCISE_CONFIGS.get(most_frequent, {}).get('name', 'None'),
        'weekly_progress': weekly_data,
        'exercise_stats': [{
            'exercise': EXERCISE_CONFIGS.get(s.exercise_key, {}).get('name', s.exercise_key),
            'total_reps': s.total_reps,
            'total_sessions': s.total_sessions,
            'max_reps': s.max_reps_in_session,
            'average_form': round(s.average_form_score, 1)
        } for s in stats]
    })