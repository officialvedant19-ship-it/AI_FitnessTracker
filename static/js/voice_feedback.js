/**
 * Voice Feedback System
 * Gives audio feedback during workouts - SUPER IMPRESSIVE for resume!
 */

class VoiceCoach {
    constructor() {
        this.synth = window.speechSynthesis;
        this.lastSpoken = '';
        this.lastSpokenTime = 0;
        this.cooldownSeconds = 3; // Don't repeat same feedback too often
        this.enabled = true;
        this.voice = null;
        this.loadVoice();
    }
    
    loadVoice() {
        // Load preferred voice (try to get a natural sounding English voice)
        const loadVoices = () => {
            const voices = this.synth.getVoices();
            this.voice = voices.find(v => v.lang === 'en-US' && v.name.includes('Google')) 
                        || voices.find(v => v.lang === 'en-US')
                        || voices[0];
        };
        
        loadVoices();
        if (this.synth.onvoiceschanged !== undefined) {
            this.synth.onvoiceschanged = loadVoices;
        }
    }
    
    speak(message, priority = false) {
        if (!this.enabled) return;
        
        const now = Date.now() / 1000;
        
        // Don't repeat same message too often
        if (message === this.lastSpoken && now - this.lastSpokenTime < this.cooldownSeconds) {
            return;
        }
        
        // Cancel any ongoing speech
        this.synth.cancel();
        
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.rate = 0.9;  // Slightly slower for clarity
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        if (this.voice) {
            utterance.voice = this.voice;
        }
        
        this.synth.speak(utterance);
        
        this.lastSpoken = message;
        this.lastSpokenTime = now;
    }
    
    celebrate(repCount) {
        const celebrations = [
            `Great job! That's ${repCount} reps!`,
            "Excellent form! Keep it up!",
            "You're crushing it!",
            "Perfect! One more!",
            "Awesome work!",
            "That's how it's done!",
            "You're on fire!"
        ];
        const random = celebrations[Math.floor(Math.random() * celebrations.length)];
        this.speak(random, true);
    }
    
    giveFormFeedback(feedback) {
        const formTips = {
            'FIX: Keep Elbow Close': "Keep your elbow close to your body",
            'FIX: Keep Back Straight': "Straighten your back",
            'FIX: Keep Body Straight': "Keep your body in a straight line",
            'CORRECT': "Good form!",
            'HOLD STEADY': "Hold it steady, you're doing great!"
        };
        
        const message = formTips[feedback] || feedback;
        if (message !== this.lastSpoken) {
            this.speak(message);
        }
    }
    
    welcome() {
        this.speak("Welcome to AI Fitness Tracker! Select an exercise to begin your workout.");
    }
    
    workoutComplete(workout) {
        this.speak(`Workout complete! You did ${workout.reps} reps and burned ${Math.round(workout.calories)} calories. Great work!`);
    }
    
    milestone(reps) {
        if (reps === 10) {
            this.speak("Double digits! Keep pushing!");
        } else if (reps === 20) {
            this.speak("20 reps! You're on fire today!");
        } else if (reps === 50) {
            this.speak("50 reps! That's incredible dedication!");
        } else if (reps === 100) {
            this.speak("100 reps! You're a legend!");
        }
    }
}

// Initialize voice coach
const voiceCoach = new VoiceCoach();

// Add voice control toggle button to UI
function addVoiceControl() {
    const controlDiv = document.createElement('div');
    controlDiv.style.position = 'fixed';
    controlDiv.style.bottom = '20px';
    controlDiv.style.left = '20px';
    controlDiv.style.zIndex = '1000';
    controlDiv.innerHTML = `
        <button id="voiceToggle" class="btn" style="background: rgba(0,0,0,0.7); border-radius: 50px; padding: 10px 15px;">
            <i class="fas fa-microphone"></i> Voice: ON
        </button>
    `;
    document.body.appendChild(controlDiv);
    
    const toggleBtn = document.getElementById('voiceToggle');
    let voiceEnabled = true;
    
    toggleBtn.addEventListener('click', () => {
        voiceEnabled = !voiceEnabled;
        voiceCoach.enabled = voiceEnabled;
        toggleBtn.innerHTML = voiceEnabled ? '<i class="fas fa-microphone"></i> Voice: ON' : '<i class="fas fa-microphone-slash"></i> Voice: OFF';
        
        if (voiceEnabled) {
            voiceCoach.speak("Voice feedback enabled");
        }
    });
}

// Call this when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addVoiceControl);
} else {
    addVoiceControl();
}