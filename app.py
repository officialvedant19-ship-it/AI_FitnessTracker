from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, session
from flask_session import Session
import cv2
import mediapipe as mp
import numpy as np
import time
import os
import base64
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import OperationalError

# Import configurations and models
from config import config
from models.database import db, init_db
from models.user import User
from models.workout import WorkoutSession, ExerciseStat

# Create Flask app
app = Flask(__name__)

# Load configuration
env = os.getenv("FLASK_ENV", "production")
app.config.from_object(config.get(env, config["production"]))

# Initialize extensions
Session(app)
print("DATABASE URI:")
print(app.config.get("SQLALCHEMY_DATABASE_URI"))
init_db(app)

def wait_for_database(app, retries=10, delay=3):
    with app.app_context():
        for i in range(retries):
            try:
                with app.app_context():
                    print("✅ Database connection successful!")
                return
            except OperationalError as e:
                print(f"⚠️ Database not ready (attempt {i+1}/{retries}): {e}")
                time.sleep(delay)
    raise Exception("❌ Could not connect to the database after multiple retries.")

# Create tables if they don't exist
with app.app_context():
    db.create_all()
    print("✅ Database tables created/verified")
    
    # Create demo user if no users exist
    if User.query.count() == 0:
        demo_user = User(email="demo@fit.com", name="Demo User")
        demo_user.set_password("password")
        db.session.add(demo_user)
        db.session.commit()
        print("✅ Demo user created: demo@fit.com / password")

# ---------------- MediaPipe setup ----------------
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# ---------------- Global variables (per user session) ----------------
user_workouts = {}

def get_user_workout(user_id):
    """Get or create workout state for a user"""
    if user_id not in user_workouts:
        user_workouts[user_id] = {
            'current_exercise': "none",
            'rep_counter': 0,
            'stage': None,
            'form_feedback': "SELECT AN EXERCISE",
            'session_start_time': None,
            'calories_burned': 0.0
        }
    return user_workouts[user_id]

# Exercise configurations
EXERCISE_CONFIG = {
    "bicep_curl": {"name": "Bicep Curl", "calories_per_rep": 0.5},
    "squat": {"name": "Squat", "calories_per_rep": 1.2},
    "pushup": {"name": "Push Up", "calories_per_rep": 1.0},
    "tricep_ext": {"name": "Tricep Ext.", "calories_per_rep": 0.6},
    "shoulder_press": {"name": "Shoulder Press", "calories_per_rep": 0.8},
    "lunge": {"name": "Forward Lunge", "calories_per_rep": 1.0},
    "deadlift": {"name": "Deadlift", "calories_per_rep": 1.5},
    "leg_raise": {"name": "Leg Raise (Abs)", "calories_per_rep": 0.7},
    "lateral_raise": {"name": "Lateral Raise", "calories_per_rep": 0.4},
    "plank": {"name": "Plank (Time)", "calories_per_rep": 0.0}
}

# ---------------- Form Assessment Helpers ----------------
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180 else angle

def calculate_back_angle(shoulder, hip):
    """Calculate angle between torso and vertical (0, -1)"""
    vector = np.array([shoulder[0] - hip[0], shoulder[1] - hip[1]])
    vertical = np.array([0, -1])
    if np.linalg.norm(vector) == 0:
        return 180
    unit_vector = vector / np.linalg.norm(vector)
    dot = np.clip(np.dot(unit_vector, vertical), -1, 1)
    angle = np.degrees(np.arccos(dot))
    return angle

def get_joint_status(angle, good_ranges, warning_ranges):
    """Determine if angle is good, warning, or poor based on ranges"""
    for low, high in good_ranges:
        if low <= angle <= high:
            return 'correct'
    for low, high in warning_ranges:
        if low <= angle <= high:
            return 'warning'
    return 'poor'

def get_color_from_status(status):
    if status == 'correct':
        return '#00ff00'  # green
    elif status == 'warning':
        return '#ffff00'  # yellow
    else:
        return '#ff0000'  # red

# Exercise-specific form thresholds
def get_form_thresholds(exercise, joint):
    thresholds = {
        'bicep_curl': {
            'elbow': {'good': [(0, 45), (150, 180)], 'warning': [(45, 90), (120, 150)]},
            'back': {'good': [(0, 180)], 'warning': []}  # not used
        },
        'squat': {
            'knee': {'good': [(0, 110)], 'warning': [(110, 135)]},
            'back': {'good': [(160, 180)], 'warning': [(150, 160)]}
        },
        'pushup': {
            'elbow': {'good': [(80, 120)], 'warning': [(60, 80), (120, 140)]},
            'back': {'good': [(170, 180)], 'warning': [(160, 170)]}
        },
        'shoulder_press': {
            'elbow': {'good': [(40, 100)], 'warning': [(100, 130)]},
            'back': {'good': [(160, 180)], 'warning': [(150, 160)]}
        },
        'lunge': {
            'knee': {'good': [(0, 100)], 'warning': [(100, 120)]},
            'back': {'good': [(160, 180)], 'warning': [(150, 160)]}
        },
        'deadlift': {
            'knee': {'good': [(0, 140)], 'warning': [(140, 160)]},
            'back': {'good': [(150, 180)], 'warning': [(130, 150)]}
        }
    }
    default = {'good': [(0, 180)], 'warning': []}
    return thresholds.get(exercise, {}).get(joint, default)

# ---------------- Utility functions ----------------
def sanitize_input(text, max_length=500):
    if not text:
        return ""
    import html
    text = html.escape(str(text))
    if len(text) > max_length:
        text = text[:max_length]
    return text

def save_workout_to_db(user_id, exercise_key, reps, calories, duration):
    """Save completed workout to database"""
    workout = WorkoutSession(
        user_id=user_id,
        exercise_key=exercise_key,
        exercise_name=EXERCISE_CONFIG.get(exercise_key, {}).get('name', exercise_key),
        reps=reps,
        calories=calories,
        duration_seconds=duration,
        form_score=85.0
    )
    db.session.add(workout)
    db.session.commit()
    print(f"✅ Workout saved: {reps} reps of {exercise_key}")

# ---------------- Authentication Decorator ----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- Routes ----------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('signin'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', '').strip())
        email = sanitize_input(request.form.get('email', '').strip().lower())
        password = request.form.get('password', '')
        
        if len(name) < 2:
            return render_template('signup.html', error="Name must be at least 2 characters")
        if len(password) < 6:
            return render_template('signup.html', error="Password must be at least 6 characters")
        
        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template('signup.html', error="Email already registered")
        
        user = User(email=email, name=name)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        session.clear()
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = sanitize_input(request.form.get('email', '').strip().lower())
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return render_template('signin.html', error="Invalid email or password")
        
        session.clear()
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        
        return redirect(url_for('dashboard'))
    
    return render_template('signin.html')

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id and user_id in user_workouts:
        del user_workouts[user_id]
    session.clear()
    return redirect(url_for('signin'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user={'name': session.get('user_name')})

@app.route('/planner')
@login_required
def planner():
    return render_template("planner.html", user={'name': session.get('user_name')})

@app.route('/workout')
@login_required
def workout():
    exercises = [{"key": k, "name": v["name"]} for k, v in EXERCISE_CONFIG.items()]
    return render_template('workout.html', exercises=exercises, user={'name': session.get('user_name')})

@app.route('/progress')
@login_required
def progress():
    return render_template('progress.html', user={'name': session.get('user_name')})

# ---------------- Client‑Side Camera + Pose Detection ----------------
@app.route('/process_frame', methods=['POST'])
@login_required
def process_frame():
    try:
        data = request.get_json()
        image_data = data.get('image')
        if not image_data:
            return jsonify({'error': 'No image data'}), 400
        
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'error': 'Invalid image'}), 400
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = frame.shape
        
        user_id = session.get('user_id')
        workout = get_user_workout(user_id)
        
        current_exercise = workout['current_exercise']
        rep_counter = workout['rep_counter']
        calories_burned = workout['calories_burned']
        stage = workout.get('stage')
        feedback = workout['form_feedback']
        
        # Prepare lists
        landmark_points = []
        angle_value = 0
        joint_angles = []
        landmark_colors = {}
        
        with mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as pose:

            results = pose.process(frame)

            if results.pose_landmarks:
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    
                    # Get pixel coordinates for angle calculation
                    def get_pixel_coords(lm):
                        return [lm.x * width, lm.y * height]
                    
                    left_shoulder = get_pixel_coords(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value])
                    right_shoulder = get_pixel_coords(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value])
                    left_elbow = get_pixel_coords(landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value])
                    right_elbow = get_pixel_coords(landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value])
                    left_wrist = get_pixel_coords(landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value])
                    right_wrist = get_pixel_coords(landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value])
                    left_hip = get_pixel_coords(landmarks[mp_pose.PoseLandmark.LEFT_HIP.value])
                    right_hip = get_pixel_coords(landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value])
                    left_knee = get_pixel_coords(landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value])
                    right_knee = get_pixel_coords(landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value])
                    left_ankle = get_pixel_coords(landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value])
                    right_ankle = get_pixel_coords(landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value])
                    
                    # Calculate joint angles
                    left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
                    right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
                    left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
                    right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
                    back_angle = calculate_back_angle(left_shoulder, left_hip)
                    
                    # Determine form status for each joint
                    elbow_thresholds = get_form_thresholds(current_exercise, 'elbow')
                    knee_thresholds = get_form_thresholds(current_exercise, 'knee')
                    back_thresholds = get_form_thresholds(current_exercise, 'back')
                    
                    left_elbow_status = get_joint_status(left_elbow_angle, elbow_thresholds['good'], elbow_thresholds['warning'])
                    right_elbow_status = get_joint_status(right_elbow_angle, elbow_thresholds['good'], elbow_thresholds['warning'])
                    left_knee_status = get_joint_status(left_knee_angle, knee_thresholds['good'], knee_thresholds['warning'])
                    right_knee_status = get_joint_status(right_knee_angle, knee_thresholds['good'], knee_thresholds['warning'])
                    back_status = get_joint_status(back_angle, back_thresholds['good'], back_thresholds['warning'])
                    
                    # Map landmark indices to colors
                    landmark_colors = {
                        mp_pose.PoseLandmark.LEFT_ELBOW.value: get_color_from_status(left_elbow_status),
                        mp_pose.PoseLandmark.RIGHT_ELBOW.value: get_color_from_status(right_elbow_status),
                        mp_pose.PoseLandmark.LEFT_KNEE.value: get_color_from_status(left_knee_status),
                        mp_pose.PoseLandmark.RIGHT_KNEE.value: get_color_from_status(right_knee_status),
                        # Color shoulders and hips based on back angle
                        mp_pose.PoseLandmark.LEFT_SHOULDER.value: get_color_from_status(back_status),
                        mp_pose.PoseLandmark.RIGHT_SHOULDER.value: get_color_from_status(back_status),
                        mp_pose.PoseLandmark.LEFT_HIP.value: get_color_from_status(back_status),
                        mp_pose.PoseLandmark.RIGHT_HIP.value: get_color_from_status(back_status),
                    }
                    
                    # Prepare angles for frontend labels
                    joint_angles = [
                        {"name": "L Elbow", "angle": round(left_elbow_angle, 1), "landmark_id": mp_pose.PoseLandmark.LEFT_ELBOW.value},
                        {"name": "R Elbow", "angle": round(right_elbow_angle, 1), "landmark_id": mp_pose.PoseLandmark.RIGHT_ELBOW.value},
                        {"name": "L Knee", "angle": round(left_knee_angle, 1), "landmark_id": mp_pose.PoseLandmark.LEFT_KNEE.value},
                        {"name": "R Knee", "angle": round(right_knee_angle, 1), "landmark_id": mp_pose.PoseLandmark.RIGHT_KNEE.value},
                    ]
                    # Back angle - position at mid-spine
                    mid_spine_x = (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x + landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x) / 2
                    mid_spine_y = (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y + landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y + 
                                   landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y + landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y) / 4
                    joint_angles.append({
                        "name": "Back", "angle": round(back_angle, 1),
                        "position": {"x": mid_spine_x, "y": mid_spine_y}
                    })
                    
                    # Collect normalized landmarks for frontend drawing
                    for i, lm in enumerate(landmarks):
                        color = landmark_colors.get(i, '#ff0000')  # default red
                        landmark_points.append({
                            'id': i,
                            'x': lm.x,
                            'y': lm.y,
                            'z': lm.z if hasattr(lm, 'z') else 0,
                            'visibility': lm.visibility if hasattr(lm, 'visibility') else 1.0,
                            'color': color
                        })
                    
                    # Update rep counting logic (unchanged from original)
                    new_reps = rep_counter
                    new_stage = stage
                    new_feedback = feedback
                    
                    if current_exercise == 'bicep_curl':
                        angle = left_elbow_angle
                        shoulder_angle = calculate_angle(left_hip, left_shoulder, left_elbow)
                        if shoulder_angle > 45:
                            new_feedback = "Keep elbow close!"
                        else:
                            new_feedback = f"Angle: {int(angle)}° - Good form!"
                            if angle > 160:
                                new_stage = "down"
                            if angle < 30 and new_stage == "down":
                                new_stage = "up"
                                new_reps += 1
                                workout['calories_burned'] += EXERCISE_CONFIG['bicep_curl']['calories_per_rep']
                    
                    elif current_exercise == 'squat':
                        angle = left_knee_angle
                        if back_angle < 150:
                            new_feedback = "Keep back straight!"
                        else:
                            new_feedback = f"Angle: {int(angle)}° - Good form!"
                            if angle > 160:
                                new_stage = "up"
                            if angle < 90 and new_stage == "up":
                                new_stage = "down"
                                new_reps += 1
                                workout['calories_burned'] += EXERCISE_CONFIG['squat']['calories_per_rep']
                    
                    elif current_exercise == 'pushup':
                        angle = left_elbow_angle
                        body_angle = calculate_angle(left_shoulder, left_hip, left_ankle)
                        if body_angle < 160:
                            new_feedback = "Keep body straight!"
                        else:
                            new_feedback = f"Angle: {int(angle)}° - Good form!"
                            if angle > 160:
                                new_stage = "up"
                            if angle < 90 and new_stage == "up":
                                new_stage = "down"
                                new_reps += 1
                                workout['calories_burned'] += EXERCISE_CONFIG['pushup']['calories_per_rep']
                    
                    # Update workout state
                    workout['rep_counter'] = new_reps
                    workout['stage'] = new_stage
                    workout['form_feedback'] = new_feedback
                    rep_counter = new_reps
                    calories_burned = workout['calories_burned']
                    feedback = new_feedback
                    angle_value = left_elbow_angle if current_exercise == 'bicep_curl' else (left_knee_angle if current_exercise == 'squat' else left_elbow_angle)
                else:
                    feedback = "No pose detected. Stand in frame."
                    workout['form_feedback'] = feedback
            else:
                return        
        
        return jsonify({
            'reps': rep_counter,
            'calories': round(calories_burned, 2),
            'feedback': feedback,
            'angle': round(angle_value, 1),
            'landmarks': landmark_points,
            'angles': joint_angles
        })
    except Exception as e:
        print(f"Process frame error: {e}")
        return jsonify({'error': str(e)}), 500

# ---------------- API Endpoints ----------------
@app.route('/set_exercise', methods=['POST'])
@login_required
def set_exercise():
    user_id = session.get('user_id')
    exercise = request.form['exercise']
    
    workout = get_user_workout(user_id)
    
    if workout['current_exercise'] != "none" and workout['rep_counter'] > 0:
        save_workout_to_db(
            user_id, 
            workout['current_exercise'],
            workout['rep_counter'],
            workout['calories_burned'],
            int(time.time() - workout['session_start_time']) if workout['session_start_time'] else 0
        )
    
    workout['current_exercise'] = exercise
    workout['rep_counter'] = 0
    workout['stage'] = None
    workout['calories_burned'] = 0.0
    workout['session_start_time'] = time.time()
    workout['form_feedback'] = "START YOUR WORKOUT" if exercise != "plank" else "HOLD POSITION"
    
    return jsonify({'status': 'success', 'exercise': exercise})

@app.route('/get_stats')
@login_required
def get_stats():
    user_id = session.get('user_id')
    workout = get_user_workout(user_id)
    
    duration = 0
    if workout.get('session_start_time'):
        duration = int(time.time() - workout['session_start_time'])
    
    return jsonify({
        'exercise': EXERCISE_CONFIG.get(workout['current_exercise'], {"name": "None"})["name"],
        'reps': workout['rep_counter'],
        'calories': round(workout['calories_burned'], 2),
        'duration': duration,
        'form_feedback': workout['form_feedback'],
        'stage': workout.get('stage')
    })

@app.route('/reset_workout', methods=['POST'])
@login_required
def reset_workout():
    user_id = session.get('user_id')
    workout = get_user_workout(user_id)
    
    if workout['current_exercise'] != "none" and workout['rep_counter'] > 0:
        save_workout_to_db(
            user_id,
            workout['current_exercise'],
            workout['rep_counter'],
            workout['calories_burned'],
            int(time.time() - workout['session_start_time']) if workout['session_start_time'] else 0
        )
    
    workout['current_exercise'] = "none"
    workout['rep_counter'] = 0
    workout['stage'] = None
    workout['calories_burned'] = 0.0
    workout['session_start_time'] = None
    workout['form_feedback'] = "SELECT AN EXERCISE"
    
    return jsonify({'status': 'reset'})

@app.route('/get_history')
@login_required
def get_history():
    user_id = session.get('user_id')
    workouts = WorkoutSession.query.filter_by(user_id=user_id).order_by(WorkoutSession.timestamp.desc()).limit(50).all()
    return jsonify([{
        'exercise': w.exercise_key,
        'reps': w.reps,
        'calories': w.calories,
        'duration': w.duration_seconds,
        'timestamp': w.timestamp.isoformat()
    } for w in workouts])

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    try:
        data = request.get_json()
        user_message = data.get('message', '').lower()
        user_id = session.get('user_id')
        workouts = WorkoutSession.query.filter_by(user_id=user_id).all()
        
        total_reps = sum(w.reps for w in workouts)
        total_calories = sum(w.calories for w in workouts)
        total_sessions = len(workouts)
        
        if 'hello' in user_message or 'hi' in user_message:
            response = f"👋 Hello! You've completed {total_sessions} workouts!"
        elif 'reps' in user_message:
            response = f"💪 You've completed {total_reps} total reps!"
        elif 'calorie' in user_message:
            response = f"🔥 You've burned {total_calories:.1f} calories!"
        elif 'workout' in user_message or 'session' in user_message:
            response = f"📊 You've completed {total_sessions} workout sessions!"
        elif total_sessions == 0:
            response = "📝 No workouts yet. Start your first workout!"
        else:
            response = "Ask me about your reps, calories, or workouts!"
        
        return jsonify({'reply': response})
    except Exception as e:
        return jsonify({'reply': "Ask me about your reps or calories!"})

@app.route('/api/get_workout_stats')
@login_required
def get_workout_stats():
    user_id = session.get('user_id')
    workouts = WorkoutSession.query.filter_by(user_id=user_id).all()
    total_reps = sum(w.reps for w in workouts)
    total_calories = sum(w.calories for w in workouts)
    total_sessions = len(workouts)
    return jsonify({
        'total_reps': total_reps,
        'total_calories': round(total_calories, 1),
        'total_sessions': total_sessions
    })

@app.route('/export_workout_data')
@login_required
def export_workout_data():
    import csv
    from io import StringIO
    user_id = session.get('user_id')
    workouts = WorkoutSession.query.filter_by(user_id=user_id).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Date', 'Exercise', 'Reps', 'Calories', 'Duration'])
    for w in workouts:
        writer.writerow([
            w.timestamp.strftime('%Y-%m-%d %H:%M'),
            w.exercise_name,
            w.reps,
            round(w.calories, 1),
            w.duration_seconds
        ])
    output = si.getvalue()
    return Response(output, mimetype='text/csv',
                   headers={"Content-Disposition": "attachment;filename=workout_data.csv"})
    
@app.route('/health')
def health_check():
    """Quick health check for Railway"""
    return "OK", 200

# ---------------- Run ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)