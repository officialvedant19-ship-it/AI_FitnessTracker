from models.workout import WorkoutSession, ExerciseStat
from models.user import User
from models.database import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import json

class WorkoutService:
    """Business logic for workout tracking and analytics"""
    
    @staticmethod
    def save_workout_session(user_id, exercise_key, exercise_name, reps, calories, duration, form_score=0):
        """Save a completed workout session"""
        workout = WorkoutSession(
            user_id=user_id,
            exercise_key=exercise_key,
            exercise_name=exercise_name,
            reps=reps,
            calories=round(calories, 2),
            duration_seconds=duration,
            form_score=form_score
        )
        
        db.session.add(workout)
        
        # Update or create exercise stats
        stats = ExerciseStat.query.filter_by(
            user_id=user_id,
            exercise_key=exercise_key
        ).first()
        
        if not stats:
            stats = ExerciseStat(user_id=user_id, exercise_key=exercise_key)
            db.session.add(stats)
        
        stats.total_reps += reps
        stats.total_sessions += 1
        stats.total_calories += workout.calories
        stats.last_performed = datetime.utcnow()
        
        if reps > stats.max_reps_in_session:
            stats.max_reps_in_session = reps
        
        # Update average form score
        if stats.total_sessions > 1:
            stats.average_form_score = (
                (stats.average_form_score * (stats.total_sessions - 1) + form_score) / 
                stats.total_sessions
            )
        else:
            stats.average_form_score = form_score
        
        # Update personal best if applicable
        if reps > stats.personal_best:
            stats.personal_best = reps
        
        db.session.commit()
        
        return workout
    
    @staticmethod
    def get_user_stats(user_id, days=30):
        """Get user statistics for last N days"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        workouts = WorkoutSession.query.filter(
            and_(
                WorkoutSession.user_id == user_id,
                WorkoutSession.timestamp >= since_date
            )
        ).all()
        
        total_workouts = len(workouts)
        total_reps = sum(w.reps for w in workouts)
        total_calories = sum(w.calories for w in workouts)
        total_duration = sum(w.duration_seconds for w in workouts)
        avg_form_score = sum(w.form_score for w in workouts) / total_workouts if total_workouts > 0 else 0
        
        # Group by exercise
        exercise_stats = {}
        for w in workouts:
            if w.exercise_key not in exercise_stats:
                exercise_stats[w.exercise_key] = {
                    'name': w.exercise_name,
                    'reps': 0,
                    'sessions': 0,
                    'calories': 0
                }
            exercise_stats[w.exercise_key]['reps'] += w.reps
            exercise_stats[w.exercise_key]['sessions'] += 1
            exercise_stats[w.exercise_key]['calories'] += w.calories
        
        # Daily breakdown
        daily_stats = {}
        for w in workouts:
            date_key = w.timestamp.strftime('%Y-%m-%d')
            if date_key not in daily_stats:
                daily_stats[date_key] = {'reps': 0, 'calories': 0, 'duration': 0}
            daily_stats[date_key]['reps'] += w.reps
            daily_stats[date_key]['calories'] += w.calories
            daily_stats[date_key]['duration'] += w.duration_seconds
        
        return {
            'period_days': days,
            'total_workouts': total_workouts,
            'total_reps': total_reps,
            'total_calories': round(total_calories, 2),
            'total_duration_minutes': round(total_duration / 60, 1),
            'average_form_score': round(avg_form_score, 1),
            'average_workout_length': round((total_duration / total_workouts) / 60, 1) if total_workouts > 0 else 0,
            'exercise_breakdown': exercise_stats,
            'daily_breakdown': daily_stats
        }
    
    @staticmethod
    def get_progress_data(user_id, exercise_key=None):
        """Get progress data for charts and visualization"""
        query = WorkoutSession.query.filter_by(user_id=user_id)
        
        if exercise_key:
            query = query.filter_by(exercise_key=exercise_key)
        
        workouts = query.order_by(WorkoutSession.timestamp).all()
        
        # Prepare data for charts
        dates = []
        reps_data = []
        calories_data = []
        form_scores = []
        
        for w in workouts:
            dates.append(w.timestamp.strftime('%Y-%m-%d'))
            reps_data.append(w.reps)
            calories_data.append(w.calories)
            form_scores.append(w.form_score if w.form_score else 0)
        
        # Calculate moving averages (7-day)
        moving_avg_reps = []
        for i in range(len(reps_data)):
            start = max(0, i - 6)
            avg = sum(reps_data[start:i+1]) / (i - start + 1)
            moving_avg_reps.append(round(avg, 1))
        
        return {
            'dates': dates,
            'reps': reps_data,
            'calories': calories_data,
            'form_scores': form_scores,
            'moving_average_reps': moving_avg_reps,
            'best_workout': max(workouts, key=lambda x: x.reps).to_dict() if workouts else None,
            'total_workouts': len(workouts)
        }
    
    @staticmethod
    def get_achievements(user_id):
        """Calculate user achievements/badges"""
        stats = WorkoutService.get_user_stats(user_id, days=365)
        workouts = WorkoutSession.query.filter_by(user_id=user_id).all()
        
        achievements = []
        
        # Streak calculation
        if workouts:
            workout_dates = sorted(set(w.timestamp.date() for w in workouts))
            current_streak = 1
            longest_streak = 1
            
            for i in range(1, len(workout_dates)):
                if (workout_dates[i] - workout_dates[i-1]).days == 1:
                    current_streak += 1
                    longest_streak = max(longest_streak, current_streak)
                else:
                    current_streak = 1
            
            achievements.append({
                'name': 'Workout Streak',
                'value': longest_streak,
                'badge': '🔥',
                'description': f'{longest_streak} days in a row'
            })
        
        # Volume achievements
        if stats['total_reps'] >= 1000:
            achievements.append({
                'name': 'Rep Master',
                'value': stats['total_reps'],
                'badge': '💪',
                'description': '1000+ total reps completed'
            })
        
        if stats['total_calories'] >= 10000:
            achievements.append({
                'name': 'Calorie Crusher',
                'value': round(stats['total_calories']),
                'badge': '⚡',
                'description': 'Burned 10,000+ calories'
            })
        
        # Consistency
        if stats['total_workouts'] >= 30:
            achievements.append({
                'name': 'Consistency King',
                'value': stats['total_workouts'],
                'badge': '👑',
                'description': '30+ workouts completed'
            })
        
        # Form score
        if stats['average_form_score'] >= 85:
            achievements.append({
                'name': 'Perfect Form',
                'value': round(stats['average_form_score']),
                'badge': '🎯',
                'description': 'Average form score 85%+'
            })
        
        return achievements
    
    @staticmethod
    def get_weekly_report(user_id):
        """Generate weekly performance report"""
        today = datetime.utcnow().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        workouts = WorkoutSession.query.filter(
            and_(
                WorkoutSession.user_id == user_id,
                func.date(WorkoutSession.timestamp) >= start_of_week,
                func.date(WorkoutSession.timestamp) <= end_of_week
            )
        ).all()
        
        # Previous week for comparison
        prev_start = start_of_week - timedelta(days=7)
        prev_end = end_of_week - timedelta(days=7)
        
        prev_workouts = WorkoutSession.query.filter(
            and_(
                WorkoutSession.user_id == user_id,
                func.date(WorkoutSession.timestamp) >= prev_start,
                func.date(WorkoutSession.timestamp) <= prev_end
            )
        ).all()
        
        current_reps = sum(w.reps for w in workouts)
        prev_reps = sum(w.reps for w in prev_workouts)
        
        rep_change = ((current_reps - prev_reps) / prev_reps * 100) if prev_reps > 0 else 100
        
        return {
            'week_start': start_of_week.isoformat(),
            'week_end': end_of_week.isoformat(),
            'total_workouts': len(workouts),
            'total_reps': current_reps,
            'total_calories': round(sum(w.calories for w in workouts), 2),
            'total_duration': round(sum(w.duration_seconds for w in workouts) / 60, 1),
            'improvement_percentage': round(rep_change, 1),
            'best_exercise': max(
                [(w.exercise_name, w.reps) for w in workouts],
                key=lambda x: x[1]
            )[0] if workouts else 'None',
            'recommendation': self._generate_recommendation(workouts, rep_change)
        }
    
    @staticmethod
    def _generate_recommendation(workouts, rep_change):
        """Generate personalized recommendation"""
        if rep_change > 20:
            return "Excellent progress this week! Try increasing weight or reps."
        elif rep_change > 0:
            return "Good consistency! Add one more set to each exercise next week."
        elif rep_change == 0:
            return "Maintaining steady pace. Try a new exercise variation."
        else:
            return "Focus on recovery this week. Reduce volume by 20% and increase protein intake."