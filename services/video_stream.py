import cv2
import mediapipe as mp
import time
import numpy as np
from flask import session
from services.pose_detection import PoseDetector, EXERCISE_CONFIGS
from controllers.workout_controller import session_manager

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Global pose detector instance
pose_detector = None

def generate_frames(user_id):
    """Generate video frames with pose detection overlay"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    # Set camera properties for better performance
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Performance optimization
    FRAME_SKIP = 3
    frame_count = 0
    last_results = None
    
    # Stage tracking for rep counting
    stage_tracker = {}
    
    with mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            frame_count += 1
            height, width, _ = frame.shape
            
            # Get current workout session data
            session_data = session_manager.get_or_create(user_id)
            current_exercise = session_data.get('exercise', 'none')
            
            # Process every Nth frame for performance
            if frame_count % FRAME_SKIP == 0:
                # Resize for faster processing
                small_frame = cv2.resize(frame, (640, 360))
                image_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                image_rgb.flags.writeable = False
                last_results = pose.process(image_rgb)
                image_rgb.flags.writeable = True
            
            # Draw pose landmarks on full resolution frame
            if last_results and last_results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    last_results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
                )
                
                # Get landmarks for exercise detection
                landmarks = last_results.pose_landmarks.landmark
                
                if current_exercise != 'none':
                    # Detect exercise form and count reps
                    feedback, rep_delta, form_score = pose_detector.detect_exercise_form(
                        landmarks, current_exercise
                    )
                    
                    # Update session data
                    if rep_delta > 0:
                        session_data['reps'] += rep_delta
                        session_data['calories'] += EXERCISE_CONFIGS.get(
                            current_exercise, 
                            EXERCISE_CONFIGS['bicep_curl']
                        ).calories_per_rep * rep_delta
                    
                    session_data['feedback'] = feedback
                    session_data['current_form_score'] = form_score
                    
                    # Draw form score overlay
                    cv2.rectangle(frame, (width - 200, 20), (width - 20, 70), (0, 0, 0), -1)
                    cv2.putText(frame, f"Form: {int(form_score)}%", 
                               (width - 190, 55),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                               (0, 255, 0) if form_score > 70 else (0, 255, 255) if form_score > 50 else (0, 0, 255),
                               2)
            
            # Draw UI overlay
            # Top left - Stats panel
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (350, 180), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
            
            # Exercise name
            ex_name = EXERCISE_CONFIGS.get(current_exercise, EXERCISE_CONFIGS['bicep_curl']).name if current_exercise != 'none' else 'Select Exercise'
            cv2.putText(frame, f"EXERCISE: {ex_name}", (15, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Reps/Time display
            if current_exercise == 'plank':
                duration = int(time.time() - session_data.get('start_time', time.time()))
                mins, secs = divmod(duration, 60)
                cv2.putText(frame, f"TIME: {mins:02d}:{secs:02d}", (15, 80),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, f"CALORIES: {session_data.get('calories', 0):.1f}", (15, 120),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 215, 0), 2)
            else:
                cv2.putText(frame, f"REPS: {session_data.get('reps', 0)}", (15, 80),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(frame, f"CALORIES: {session_data.get('calories', 0):.1f}", (15, 120),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 215, 0), 2)
            
            # Top right - Timer
            if session_data.get('start_time'):
                duration = int(time.time() - session_data['start_time'])
                mins, secs = divmod(duration, 60)
                cv2.putText(frame, f"SESSION: {mins:02d}:{secs:02d}", (width - 200, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Bottom - Feedback banner
            feedback = session_data.get('feedback', 'Ready')
            cv2.rectangle(frame, (0, height - 80), (width, height), (0, 0, 0), -1)
            
            # Color based on feedback type
            if 'CORRECT' in feedback or 'Good' in feedback:
                color = (0, 255, 0)
            elif 'FIX' in feedback or 'ERROR' in feedback:
                color = (0, 0, 255)
            else:
                color = (255, 255, 0)
            
            # Center the text
            text_size = cv2.getTextSize(feedback, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            text_x = (width - text_size[0]) // 2
            cv2.putText(frame, feedback, (text_x, height - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # Encode frame for streaming
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    cap.release()