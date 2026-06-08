from flask import Blueprint, request, jsonify, render_template, session
from datetime import datetime, timedelta
from models.plan import WorkoutPlan, NutritionLog
from models.workout import WorkoutSession
from models.database import db
from utils.decorators import login_required
from sqlalchemy import func, and_

planner_bp = Blueprint('planner', __name__)

# Exercise database for suggestions
EXERCISES_DB = {
    "Full Body": [
        {"name": "Burpees", "sets": 3, "reps": 10, "calories_per_set": 15},
        {"name": "Kettlebell Swings", "sets": 4, "reps": 15, "calories_per_set": 12},
        {"name": "Thrusters", "sets": 3, "reps": 12, "calories_per_set": 10},
        {"name": "Deadlifts", "sets": 3, "reps": 8, "calories_per_set": 18}
    ],
    "Upper Body": [
        {"name": "Pushups", "sets": 4, "reps": 12, "calories_per_set": 8},
        {"name": "Dumbbell Press", "sets": 3, "reps": 10, "calories_per_set": 10},
        {"name": "Bent-over Rows", "sets": 3, "reps": 12, "calories_per_set": 9},
        {"name": "Overhead Press", "sets": 3, "reps": 10, "calories_per_set": 9}
    ],
    "Lower Body": [
        {"name": "Squats", "sets": 4, "reps": 12, "calories_per_set": 12},
        {"name": "Lunges", "sets": 3, "reps": 10, "calories_per_set": 10},
        {"name": "Calf Raises", "sets": 3, "reps": 20, "calories_per_set": 5},
        {"name": "Leg Press", "sets": 3, "reps": 12, "calories_per_set": 10}
    ],
    "Cardio": [
        {"name": "Running", "sets": 1, "reps": 30, "unit": "minutes", "calories_per_set": 200},
        {"name": "Jump Rope", "sets": 3, "reps": 60, "unit": "seconds", "calories_per_set": 15},
        {"name": "Cycling", "sets": 1, "reps": 30, "unit": "minutes", "calories_per_set": 180},
        {"name": "HIIT", "sets": 4, "reps": 45, "unit": "seconds", "calories_per_set": 12}
    ],
    "Rest": [
        {"name": "Yoga", "sets": 1, "reps": 20, "unit": "minutes", "calories_per_set": 50},
        {"name": "Stretching", "sets": 1, "reps": 15, "unit": "minutes", "calories_per_set": 30},
        {"name": "Foam Rolling", "sets": 1, "reps": 10, "unit": "minutes", "calories_per_set": 20}
    ]
}

# Nutrition recommendations
NUTRITION_DB = {
    "Full Body": {
        "tip": "Focus on complex carbs and lean protein for energy",
        "meals": ["Oatmeal with banana", "Grilled chicken with quinoa", "Protein shake post-workout"],
        "calories_target": 2500
    },
    "Upper Body": {
        "tip": "Increase protein intake for muscle repair",
        "meals": ["Eggs and avocado toast", "Salmon with sweet potato", "Greek yogurt with berries"],
        "calories_target": 2300
    },
    "Lower Body": {
        "tip": "Eat magnesium-rich foods for muscle recovery",
        "meals": ["Spinach smoothie", "Turkey and brown rice", "Dark chocolate and almonds"],
        "calories_target": 2400
    },
    "Cardio": {
        "tip": "Load on electrolytes and easy-to-digest carbs",
        "meals": ["Banana before workout", "Pasta with lean sauce", "Coconut water"],
        "calories_target": 2600
    },
    "Rest": {
        "tip": "Focus on micronutrients and hydration",
        "meals": ["Fruit salad", "Vegetable soup", "Herbal tea"],
        "calories_target": 2000
    }
}

@planner_bp.route('/planner')
@login_required
def planner_page(current_user):
    """Render planner page"""
    return render_template('planner.html', user=current_user)

@planner_bp.route('/api/planner/save-plan', methods=['POST'])
@login_required
def save_plan(current_user):
    """Save a workout plan"""
    data = request.get_json()
    
    plan_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
    focus = data.get('focus')
    exercises = data.get('exercises', [])
    
    # Check if plan already exists for this date
    existing_plan = WorkoutPlan.query.filter_by(
        user_id=current_user.id,
        plan_date=plan_date
    ).first()
    
    if existing_plan:
        # Update existing plan
        existing_plan.focus = focus
        existing_plan.exercises = exercises
        existing_plan.updated_at = datetime.utcnow()
    else:
        # Create new plan
        plan = WorkoutPlan(
            user_id=current_user.id,
            plan_date=plan_date,
            focus=focus,
            exercises=exercises
        )
        db.session.add(plan)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Plan saved successfully'})

@planner_bp.route('/api/planner/get-plans')
@login_required
def get_plans(current_user):
    """Get user's workout plans"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = WorkoutPlan.query.filter_by(user_id=current_user.id)
    
    if start_date:
        query = query.filter(WorkoutPlan.plan_date >= start_date)
    if end_date:
        query = query.filter(WorkoutPlan.plan_date <= end_date)
    
    plans = query.order_by(WorkoutPlan.plan_date).all()
    
    return jsonify([plan.to_dict() for plan in plans])

@planner_bp.route('/api/planner/delete-plan/<int:plan_id>', methods=['DELETE'])
@login_required
def delete_plan(current_user, plan_id):
    """Delete a workout plan"""
    plan = WorkoutPlan.query.filter_by(id=plan_id, user_id=current_user.id).first()
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    db.session.delete(plan)
    db.session.commit()
    
    return jsonify({'success': True})

@planner_bp.route('/api/planner/complete-plan/<int:plan_id>', methods=['POST'])
@login_required
def complete_plan(current_user, plan_id):
    """Mark a plan as completed"""
    plan = WorkoutPlan.query.filter_by(id=plan_id, user_id=current_user.id).first()
    
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    plan.completed = True
    plan.completed_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})

@planner_bp.route('/api/planner/get-suggestions')
@login_required
def get_suggestions(current_user):
    """Get AI workout suggestions based on history"""
    focus = request.args.get('focus')
    
    if not focus or focus not in EXERCISES_DB:
        return jsonify({'error': 'Invalid focus'}), 400
    
    # Get user's recent workouts to personalize suggestions
    recent_workouts = WorkoutSession.query.filter_by(
        user_id=current_user.id
    ).order_by(WorkoutSession.timestamp.desc()).limit(10).all()
    
    recent_exercises = [w.exercise_key for w in recent_workouts]
    
    # Basic personalization - avoid suggesting same exercise too frequently
    suggestions = EXERCISES_DB[focus].copy()
    
    # Get nutrition recommendation
    nutrition = NUTRITION_DB.get(focus, NUTRITION_DB["Full Body"])
    
    return jsonify({
        'exercises': suggestions,
        'nutrition': nutrition,
        'recent_exercises': recent_exercises[:5]
    })

@planner_bp.route('/api/planner/nutrition-log', methods=['POST'])
@login_required
def add_nutrition_log(current_user):
    """Log nutrition entry"""
    data = request.get_json()
    
    log = NutritionLog(
        user_id=current_user.id,
        log_date=datetime.strptime(data.get('date'), '%Y-%m-%d').date(),
        meal_type=data.get('meal_type'),
        food_name=data.get('food_name'),
        calories=data.get('calories', 0),
        protein=data.get('protein', 0),
        carbs=data.get('carbs', 0),
        fats=data.get('fats', 0)
    )
    
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'success': True, 'log_id': log.id})

@planner_bp.route('/api/planner/nutrition-summary')
@login_required
def get_nutrition_summary(current_user):
    """Get nutrition summary for current week"""
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    logs = NutritionLog.query.filter(
        and_(
            NutritionLog.user_id == current_user.id,
            NutritionLog.log_date >= start_of_week
        )
    ).all()
    
    total_calories = sum(log.calories for log in logs)
    total_protein = sum(log.protein for log in logs)
    total_carbs = sum(log.carbs for log in logs)
    total_fats = sum(log.fats for log in logs)
    
    return jsonify({
        'total_calories': total_calories,
        'total_protein': total_protein,
        'total_carbs': total_carbs,
        'total_fats': total_fats,
        'daily_average': {
            'calories': total_calories // 7,
            'protein': total_protein // 7,
            'carbs': total_carbs // 7,
            'fats': total_fats // 7
        },
        'logs': [{
            'date': log.log_date.isoformat(),
            'meal_type': log.meal_type,
            'food_name': log.food_name,
            'calories': log.calories
        } for log in logs]
    })