import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import time

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

@dataclass
class ExerciseConfig:
    """Configuration for each exercise"""
    name: str
    calories_per_rep: float
    ideal_angles: Dict[str, int]
    angle_tolerance: int = 15
    
EXERCISE_CONFIGS = {
    "bicep_curl": ExerciseConfig(
        name="Bicep Curl",
        calories_per_rep=0.5,
        ideal_angles={"elbow": 30, "shoulder": 10},
        angle_tolerance=15
    ),
    "squat": ExerciseConfig(
        name="Squat",
        calories_per_rep=1.2,
        ideal_angles={"knee": 90, "back": 170},
        angle_tolerance=10
    ),
    "pushup": ExerciseConfig(
        name="Push Up",
        calories_per_rep=1.0,
        ideal_angles={"elbow": 90, "body": 180},
        angle_tolerance=10
    ),
    "tricep_ext": ExerciseConfig(
        name="Tricep Extension",
        calories_per_rep=0.6,
        ideal_angles={"elbow": 45, "tricep": 20},
        angle_tolerance=15
    ),
    "shoulder_press": ExerciseConfig(
        name="Shoulder Press",
        calories_per_rep=0.8,
        ideal_angles={"elbow": 160, "shoulder": 90},
        angle_tolerance=15
    ),
    "lunge": ExerciseConfig(
        name="Forward Lunge",
        calories_per_rep=1.0,
        ideal_angles={"front_knee": 90, "back_knee": 90},
        angle_tolerance=10
    ),
    "deadlift": ExerciseConfig(
        name="Deadlift",
        calories_per_rep=1.5,
        ideal_angles={"hip": 100, "knee": 160},
        angle_tolerance=10
    ),
    "leg_raise": ExerciseConfig(
        name="Leg Raise",
        calories_per_rep=0.7,
        ideal_angles={"hip": 90},
        angle_tolerance=10
    ),
    "lateral_raise": ExerciseConfig(
        name="Lateral Raise",
        calories_per_rep=0.4,
        ideal_angles={"elbow": 170, "shoulder_abduction": 90},
        angle_tolerance=10
    ),
    "plank": ExerciseConfig(
        name="Plank",
        calories_per_rep=0.0,
        ideal_angles={"body": 180},
        angle_tolerance=10
    )
}

class PoseDetector:
    """Handles pose detection and exercise counting"""
    
    def __init__(self, config):
        self.config = config
        self.pose = mp_pose.Pose(
            min_detection_confidence=config.POSE_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.POSE_TRACKING_CONFIDENCE
        )
        
    @staticmethod
    def calculate_angle(a, b, c):
        """Calculate angle between three points"""
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        return 360 - angle if angle > 180 else angle
    
    @staticmethod
    def get_form_score(angles: Dict[str, float], exercise: str) -> float:
        """Calculate form score (0-100) based on how close angles are to ideal"""
        if exercise not in EXERCISE_CONFIGS:
            return 100.0
        
        config = EXERCISE_CONFIGS[exercise]
        scores = []
        
        for joint, current_angle in angles.items():
            if joint in config.ideal_angles:
                ideal = config.ideal_angles[joint]
                deviation = abs(current_angle - ideal)
                score = max(0, 100 - (deviation / config.angle_tolerance) * 100)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 100.0
    
    def detect_exercise_form(self, landmarks, exercise: str) -> Tuple[str, int, float]:
        """
        Detect exercise movement and count reps
        Returns: (feedback, rep_count_delta, form_score)
        """
        if not landmarks or exercise == "none":
            return "Select an exercise", 0, 0.0
        
        try:
            # Get key landmarks
            left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, 
                            landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, 
                         landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
            left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, 
                         landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
            left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, 
                       landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, 
                        landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, 
                         landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
            
            angles = {}
            feedback = "Correct form"
            rep_increment = 0
            
            # Exercise-specific logic
            if exercise == 'bicep_curl':
                elbow_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
                shoulder_angle = self.calculate_angle(left_hip, left_shoulder, left_elbow)
                angles = {'elbow': elbow_angle, 'shoulder': shoulder_angle}
                
                if shoulder_angle > 45:
                    feedback = "Keep elbow close to body"
                elif elbow_angle > 160:
                    self.stage = 'down'
                    feedback = "Lower slowly"
                elif elbow_angle < 30 and getattr(self, 'stage', None) == 'down':
                    self.stage = 'up'
                    rep_increment = 1
                    feedback = "Good rep!"
                    
            elif exercise == 'squat':
                knee_angle = self.calculate_angle(left_hip, left_knee, left_ankle)
                back_angle = self.calculate_angle(left_shoulder, left_hip, left_knee)
                angles = {'knee': knee_angle, 'back': back_angle}
                
                if back_angle < 150:
                    feedback = "Keep back straight"
                elif knee_angle > 160:
                    self.stage = 'up'
                    feedback = "Go down"
                elif knee_angle < 90 and getattr(self, 'stage', None) == 'up':
                    self.stage = 'down'
                    rep_increment = 1
                    feedback = "Great squat!"
                    
            elif exercise == 'pushup':
                elbow_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
                body_angle = self.calculate_angle(left_shoulder, left_hip, left_ankle)
                angles = {'elbow': elbow_angle, 'body': body_angle}
                
                if body_angle < 160:
                    feedback = "Keep body straight"
                elif elbow_angle > 160:
                    self.stage = 'up'
                    feedback = "Lower chest"
                elif elbow_angle < 90 and getattr(self, 'stage', None) == 'up':
                    self.stage = 'down'
                    rep_increment = 1
                    feedback = "Push up!"
                    
            # Add other exercises similarly...
            
            # Calculate form score
            form_score = self.get_form_score(angles, exercise)
            
            return feedback, rep_increment, form_score
            
        except Exception as e:
            return f"Error: Ensure full body visible", 0, 0.0