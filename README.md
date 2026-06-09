# PoseTrack AI 🏋️‍♂️

### Real-Time AI Fitness Coach Using Computer Vision & Pose Estimation

PoseTrack AI is a full-stack AI-powered fitness tracking platform that uses computer vision and pose estimation to analyze body movements in real time. The system tracks exercises, counts repetitions automatically, provides form feedback, calculates calories burned, and maintains workout history through an interactive web dashboard.

Built using Flask, MediaPipe, OpenCV, and modern web technologies, PoseTrack AI acts as a virtual fitness assistant capable of helping users monitor and improve workout performance directly through their webcam.
---

## 🎥 Demo

<p align="center">
  <a href="[https://youtu.be/YOUR_VIDEO_LINK](https://youtu.be/etn5ok5JK7A)">
    <img src="assets/thumbnail.png" alt="PoseTrack AI Demo" width="900">
  </a>
</p>

<p align="center">
  <b>▶️ Click the image to watch the full demonstration</b>
</p>

---

# 🚀 Key Features

### 🤖 AI-Powered Pose Detection

* Real-time body landmark detection using MediaPipe
* Accurate joint angle calculation
* Live pose tracking through webcam

### 💪 Intelligent Exercise Tracking

Supports automatic repetition counting for:

* Bicep Curl
* Squat
* Push Up
* Shoulder Press
* Lunge
* Deadlift
* Leg Raise
* Lateral Raise

### 📊 Workout Analytics

* Daily workout statistics
* Exercise history tracking
* Calories burned estimation
* Performance monitoring

### 👤 User Management

* Secure authentication system
* Personal workout records
* Individual fitness progress tracking

### 📁 Data Export

* Export workout history to CSV
* Download performance reports

---

# 🏗️ System Architecture

```text
User Webcam
      │
      ▼
MediaPipe Pose Detection
      │
      ▼
Body Landmark Extraction
      │
      ▼
Joint Angle Calculation
      │
      ▼
Exercise Recognition Logic
      │
      ▼
Repetition Counter
      │
      ▼
Calorie Estimation Engine
      │
      ▼
Workout History Storage
      │
      ▼
Analytics Dashboard
```

---

# 🛠️ Technology Stack

## Backend

* Python
* Flask
* Gunicorn

## Artificial Intelligence & Computer Vision

* MediaPipe
* OpenCV
* NumPy

## Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap

## Database & Storage

* SQLite
* CSV Export Support

---

### Supported Environment

✅ Full functionality available on Localhost

* Real-time camera access
* Live pose detection
* Exercise tracking
* Rep counting
* Form analysis

### To Experience the Complete Application

Clone the repository and run it locally:

```bash
git clone https://github.com/pn-dev-in/AI-Powered-Fitness-Tracking-System.git
cd AI-Powered-Fitness-Tracking-System
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

This provides full access to all AI-powered exercise tracking capabilities.


# 📂 Project Structure

```text
PoseTrack-AI/

├── controllers/
├── models/
├── services/
├── static/
├── templates/
├── tests/
├── utils/
├── user_data/
│
├── app.py
├── auth_utils.py
├── config.py
├── setup_db.py
│
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── requirements.txt
└── README.md
```

---

# 🎯 Supported Exercises

| Exercise       | Calories/Rep | Difficulty   |
| -------------- | ------------ | ------------ |
| Bicep Curl     | 0.5          | Beginner     |
| Squat          | 1.2          | Intermediate |
| Push Up        | 1.0          | Intermediate |
| Shoulder Press | 0.8          | Beginner     |
| Lunge          | 1.0          | Intermediate |
| Deadlift       | 1.5          | Advanced     |
| Leg Raise      | 0.7          | Beginner     |
| Lateral Raise  | 0.4          | Beginner     |

---

# 📸 Application Screenshots

### Signup Page
<img width="1919" height="1020" alt="Screenshot 2026-06-09 154012" src="https://github.com/user-attachments/assets/dd081006-1810-4641-87da-dfcfafb60e94" />


### Signin Page
<img width="1919" height="1010" alt="Screenshot 2026-06-09 153952" src="https://github.com/user-attachments/assets/791bc95c-22b1-4b09-a5ad-29bc6412512d" />

### Dashboard

<img width="1919" height="1012" alt="Screenshot 2026-06-09 154056" src="https://github.com/user-attachments/assets/ac651e69-05ab-4204-aee0-fa0639f89ad7" />

### Live Exercise Tracking
<img width="1919" height="1017" alt="Screenshot 2026-06-09 154514" src="https://github.com/user-attachments/assets/fe14dfa7-6ee4-4ed9-b82c-c6c0046598cf" />
<img width="905" height="484" alt="Screenshot 2026-06-09 154444" src="https://github.com/user-attachments/assets/da2a6ed1-ba4f-45db-95ad-9570aed56ed0" />


### AI Coach
<img width="1919" height="1017" alt="Screenshot 2026-06-09 154531" src="https://github.com/user-attachments/assets/cfbe1f5a-c4df-4b51-be21-6e3f3302823c" />

### Analytics Dashboard
<img width="1919" height="1012" alt="Screenshot 2026-06-09 154630" src="https://github.com/user-attachments/assets/ec2fc1ea-49b5-49f1-9c46-bef4bca44508" />
<img width="1919" height="1016" alt="Screenshot 2026-06-09 154551" src="https://github.com/user-attachments/assets/3ea5d36a-16cb-4ef1-b138-90930c29580f" />


---

# ⚡ Local Installation

Clone the repository:

```bash
git clone https://github.com/pn-dev-in/AI-Powered-Fitness-Tracking-System.git

cd AI-Powered-Fitness-Tracking-System
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Initialize database:

```bash
python setup_db.py
```

Run application:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

# 🐳 Docker Setup

Build container:

```bash
docker build -t posetrack-ai .
```

Run container:

```bash
docker run -p 5000:5000 posetrack-ai
```

Using Docker Compose:

```bash
docker-compose up --build
```

---

# 🧪 Testing

Run project tests:

```bash
pytest
```

---

# 📈 Future Enhancements

* AI posture correction feedback
* Exercise auto-classification using ML
* Personalized workout recommendations
* Fitness goal tracking
* Mobile application
* Voice-enabled AI fitness coach
* Wearable device integration
* Advanced analytics and reporting

---

# 🎓 Skills Demonstrated

This project showcases practical experience in:

✅ Computer Vision

✅ Pose Estimation

✅ Artificial Intelligence

✅ Flask Web Development

✅ RESTful Application Design

✅ Authentication Systems

✅ Data Analytics

✅ Docker Containerization

✅ Cloud Deployment

✅ Software Architecture

---

# 📊 Project Highlights

* Real-time AI fitness monitoring
* 8 supported exercise types
* Automated repetition counting
* Live calorie estimation
* User authentication and session management
* Cloud-hosted production deployment
* Docker-ready infrastructure
* Exportable workout data

---

# 👨‍💻 Author

### Pravesh Nandanwar

GitHub: https://github.com/pn-dev-in

LinkedIn: www.linkedin.com/in/pravesh-nandanwar

---

# ⭐ Support

If you found this project useful, consider giving it a star on GitHub.

Contributions, suggestions, and feedback are always welcome.
