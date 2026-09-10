import streamlit as st
import streamlit.components.v1 as components
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import json
import time
import pypdf
import librosa
import importlib
from core.tts_engine import TTSEngine
from core.elevenlabs_client import ElevenLabsClient
from core.translator import safe_translate
from modules.conversation_mode import render_conversation_mode_module
import modules.accent_coach
importlib.reload(modules.accent_coach)
from modules.accent_coach import render_accent_coach_module
from modules.user_guide import render_user_guide_module
from modules.voice_clone import render_voice_clone_module
from modules.voice_translate import render_voice_translate_module
from modules.settings import render_settings_module

# ═══════════════════════════════════════════════════════════
# 1. PAGE CONFIG
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="AI Translator Pro — Futuristic AI Command Center", page_icon="⚡", layout="wide")

# ═══════════════════════════════════════════════════════════
# 2. LOCAL JSON DATABASE
# ═══════════════════════════════════════════════════════════
DB_FILE = "users_data.json"
HISTORY_FILE = "translation_history.json"

def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"admin@gmail.com": "12345", "project_test@gmail.com": "abcd@123"}
    return {"admin@gmail.com": "12345", "project_test@gmail.com": "abcd@123"}

def save_user(email, password):
    users = load_users()
    users[email] = password
    with open(DB_FILE, "w", encoding='utf-8') as f:
        json.dump(users, f, indent=4)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_history(entry):
    history = load_history()
    history.insert(0, entry)
    if len(history) > 50:
        history = history[:50]
    with open(HISTORY_FILE, "w", encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def delete_history_item(index: int):
    history = load_history()
    if 0 <= index < len(history):
        history.pop(index)
        with open(HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

def clear_all_history():
    with open(HISTORY_FILE, "w", encoding='utf-8') as f:
        json.dump([], f, indent=4, ensure_ascii=False)

# ═══════════════════════════════════════════════════════════
# 3. FUTURISTIC AI COMMAND CENTER CSS & HUD ANIMATIONS
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Space+Grotesk:wght@500;700&family=Rajdhani:wght@500;600;700&family=Poppins:wght@300;400;500;600;700&display=swap');

/* 🌌 AI NEURAL SPACE - BASE BACKGROUND OVERRIDE (NEAR-BLACK) */
.stApp {
    background-color: #05070d !important;
    background-image: 
        radial-gradient(circle at 15% 20%, rgba(0, 242, 254, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 85% 30%, rgba(112, 0, 255, 0.08) 0%, transparent 45%),
        radial-gradient(circle at 50% 80%, rgba(0, 180, 255, 0.05) 0%, transparent 50%) !important;
    background-attachment: fixed !important;
    color: #F5F7FF;
    font-family: 'Poppins', sans-serif;
}

/* Futuristic Thin Cyber Grid Overlay */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    background-image: 
        linear-gradient(to right, rgba(0, 220, 255, 0.03) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(0, 220, 255, 0.03) 1px, transparent 1px);
    background-size: 45px 45px;
    pointer-events: none;
    z-index: 0;
}

/* Floating Ambient Particles */
.particle {
    position: fixed; width: 3px; height: 3px;
    background: radial-gradient(circle, #00f2fe, #7000ff);
    border-radius: 50%; pointer-events: none;
    box-shadow: 0 0 8px #00f2fe, 0 0 15px #7000ff;
    animation: floatUp 12s linear infinite; z-index: 0;
}
@keyframes floatUp {
    0% { transform: translateY(105vh) scale(0); opacity: 0; }
    20% { opacity: 0.7; } 80% { opacity: 0.7; }
    100% { transform: translateY(-10vh) scale(1.4); opacity: 0; }
}

/* Keep Streamlit header transparent so the sidebar toggle (collapse/expand) button stays visible & functional */
[data-testid="stHeader"] {
    background: transparent !important;
    color: #00f2fe !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}
#MainMenu, footer {
    visibility: hidden;
}

/* ⚡ SIDEBAR COLLAPSE & EXPAND TOGGLE BUTTON - CYBERPUNK NEON HUD STYLING */
[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
button[kind="header"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    color: #00f2fe !important;
    background: rgba(8, 14, 30, 0.92) !important;
    border: 1px solid rgba(0, 242, 254, 0.5) !important;
    border-radius: 10px !important;
    box-shadow: 0 0 16px rgba(0, 242, 254, 0.35) !important;
    padding: 6px 12px !important;
    transition: all 0.25s ease-in-out !important;
    z-index: 999999 !important;
}

[data-testid="collapsedControl"]:hover,
button[data-testid="stSidebarCollapseButton"]:hover,
button[kind="header"]:hover {
    background: rgba(0, 242, 254, 0.25) !important;
    border-color: #00f2fe !important;
    box-shadow: 0 0 25px rgba(0, 242, 254, 0.7) !important;
    transform: scale(1.08) !important;
}

[data-testid="collapsedControl"] svg,
button[data-testid="stSidebarCollapseButton"] svg,
button[kind="header"] svg {
    fill: #00f2fe !important;
    stroke: #00f2fe !important;
}

/* Glowing Header & Titles */
.glow-title {
    font-family: 'Orbitron', sans-serif; text-align: center;
    font-size: 34px; font-weight: 900; letter-spacing: 3px;
    color: #ffffff;
    text-shadow: 0 0 20px rgba(0, 242, 254, 0.5), 0 0 40px rgba(0, 242, 254, 0.2);
    margin-bottom: 6px;
}

.subtitle-anim {
    font-family: 'Space Grotesk', sans-serif; text-align: center;
    color: #94a3b8; font-size: 15px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase; margin-bottom: 20px;
}

/* Modern Cyber Divider */
.neon-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0, 220, 255, 0.4), rgba(112, 0, 255, 0.4), transparent);
    margin: 18px 0 25px 0; border: none;
}

/* STREAMLIT INPUT OVERRIDES - NO WHITE BOXES REMAINING */
label p {
    color: #00f2fe !important; font-weight: 700 !important;
    font-family: 'Space Grotesk', sans-serif !important; letter-spacing: 1.5px;
    font-size: 14px !important; text-transform: uppercase;
}

div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea, .stTextArea textarea, .stTextInput input {
    background: rgba(8, 12, 24, 0.90) !important;
    color: #F5F7FF !important;
    border: 1px solid rgba(0, 220, 255, 0.30) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(14px) !important;
    box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.6) !important;
}

div[data-baseweb="select"] > div:hover, div[data-baseweb="input"] > div:hover, textarea:hover, .stTextInput input:hover {
    border-color: rgba(0, 220, 255, 0.6) !important;
}

div[data-baseweb="select"] > div:focus-within, div[data-baseweb="input"] > div:focus-within, textarea:focus, .stTextInput input:focus {
    border-color: #00d2ff !important;
    box-shadow: 0 0 0 1px rgba(0, 220, 255, 0.4), 0 0 25px rgba(0, 220, 255, 0.15) !important;
}

/* CONTROL BUTTON DESIGN */
.stButton > button {
    width: 100% !important;
    background: rgba(8, 14, 30, 0.85) !important;
    color: #ffffff !important;
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    border: 1px solid rgba(0, 220, 255, 0.4) !important;
    padding: 12px 20px !important;
    border-radius: 12px !important;
    transition: all 0.25s ease-in-out !important;
    box-shadow: 0 0 15px rgba(0, 220, 255, 0.15) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    border-color: #00f2fe !important;
    box-shadow: 0 0 25px rgba(0, 220, 255, 0.4), 0 0 10px rgba(0, 220, 255, 0.2) !important;
}

.stButton > button:active {
    transform: translateY(1px) !important;
}

/* Transparent Hardware Dashboard Cards */
.dash-card {
    background: rgba(8, 12, 26, 0.75);
    border: 1px solid rgba(0, 220, 255, 0.20);
    border-radius: 14px; padding: 24px 18px; text-align: center;
    backdrop-filter: blur(16px);
    box-shadow: 0 10px 35px rgba(0, 0, 0, 0.5);
    transition: all 0.3s ease-in-out;
    height: 100%; position: relative; overflow: hidden;
}
.dash-card:hover {
    transform: translateY(-3px);
    border-color: rgba(0, 220, 255, 0.45);
    box-shadow: 0 12px 40px rgba(0, 220, 255, 0.15);
}
.dash-icon { font-size: 48px; margin-bottom: 12px; display: inline-block; filter: drop-shadow(0 0 12px rgba(0, 220, 255, 0.5)); }
.dash-title { color: #ffffff; font-size: 18px; font-weight: 700; font-family: 'Orbitron', sans-serif; margin-bottom: 8px; letter-spacing: 1.5px; }
.dash-desc { color: #94a3b8; font-size: 13px; margin-bottom: 18px; line-height: 1.5; }

/* Status Badges */
.badge-ready {
    background: rgba(0, 255, 136, 0.1);
    color: #00ff88;
    border: 1px solid #00ff88;
    padding: 0.25rem 0.6rem;
    border-radius: 12px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 1px;
    display: inline-block;
    box-shadow: 0 0 8px rgba(0, 255, 136, 0.2);
}

/* Glassmorphism Text Result Cards */
.glass-card-original {
    background: rgba(8, 14, 30, 0.8);
    border: 1px solid rgba(0, 220, 255, 0.35);
    border-left: 4px solid #00f2fe;
    border-radius: 14px; padding: 20px; margin: 15px 0;
    backdrop-filter: blur(14px);
}
.glass-card-translated {
    background: rgba(14, 10, 32, 0.8);
    border: 1px solid rgba(112, 0, 255, 0.4);
    border-left: 4px solid #7000ff;
    border-radius: 14px; padding: 20px; margin: 15px 0;
    backdrop-filter: blur(14px);
}

.card-label {
    font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 800;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;
}
.card-label.orig { color: #00f2fe; }
.card-label.trans { color: #7000ff; }
.card-text { font-size: 17px; font-weight: 500; color: #ffffff; line-height: 1.5; }

/* AI Processing Pipeline Visualizer */
.pipeline-box {
    background: rgba(8, 12, 26, 0.8);
    border: 1px solid rgba(0, 220, 255, 0.25);
    border-radius: 14px; padding: 18px; margin: 18px 0; text-align: center;
}
.pipeline-header {
    font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 800;
    color: #00f2fe; letter-spacing: 2px; margin-bottom: 12px; text-transform: uppercase;
}
.pipeline-steps { display: flex; align-items: center; justify-content: space-around; gap: 8px; flex-wrap: wrap; }
.step-item {
    background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(0, 220, 255, 0.2);
    border-radius: 10px; padding: 8px 14px; font-family: 'Space Grotesk', sans-serif;
    font-size: 13px; font-weight: 700; color: #94a3b8; transition: all 0.3s;
}
.step-item.active {
    background: rgba(0, 220, 255, 0.12); border-color: #00f2fe; color: #00f2fe;
    box-shadow: 0 0 15px rgba(0, 220, 255, 0.4); transform: scale(1.04);
}
.step-item.completed {
    background: rgba(0, 255, 136, 0.08); border-color: #00ff88; color: #00ff88;
}
.step-item.cloning-core {
    position: relative;
    box-shadow: 0 0 20px rgba(112, 0, 255, 0.5);
    animation: corePulse 2s infinite ease-in-out;
}
@keyframes corePulse {
    0%, 100% { box-shadow: 0 0 15px rgba(112, 0, 255, 0.4); }
    50% { box-shadow: 0 0 30px rgba(0, 242, 254, 0.7); }
}
.pipeline-arrow { color: rgba(0, 220, 255, 0.6); font-weight: 900; font-size: 16px; }

/* Radar Wave Visualizer */
.wave-container { display: flex; align-items: center; justify-content: center; gap: 5px; height: 60px; margin: 15px 0; }
.wave-bar { width: 5px; background: linear-gradient(to top, #00f2fe, #7000ff); border-radius: 8px; animation: wave 1.2s ease-in-out infinite; }
.wave-bar:nth-child(1)  { animation-delay: 0.0s; } .wave-bar:nth-child(2)  { animation-delay: 0.1s; }
.wave-bar:nth-child(3)  { animation-delay: 0.2s; } .wave-bar:nth-child(4)  { animation-delay: 0.3s; }
.wave-bar:nth-child(5)  { animation-delay: 0.4s; } .wave-bar:nth-child(6)  { animation-delay: 0.5s; }
.wave-bar:nth-child(7)  { animation-delay: 0.4s; } .wave-bar:nth-child(8)  { animation-delay: 0.3s; }
@keyframes wave { 0%, 100% { height: 10px; } 50% { height: 50px; } }

.countdown-display {
    font-family: 'Orbitron', sans-serif; font-size: 50px; font-weight: 900;
    text-align: center; color: #00f2fe;
    text-shadow: 0 0 30px rgba(0, 242, 254, 0.8);
    animation: countdownPulse 0.9s ease-in-out infinite;
}
@keyframes countdownPulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.06); } }

/* Toast Badge */
.toast {
    position: fixed; top: 25px; right: 25px;
    background: rgba(8, 14, 30, 0.95); border: 1px solid #00f2fe; color: white;
    padding: 12px 22px; border-radius: 12px; font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 700;
    box-shadow: 0 0 25px rgba(0, 242, 254, 0.4);
    z-index: 9999; animation: toastIn 0.5s ease-out, toastOut 0.5s ease-in 2.5s forwards;
}
@keyframes toastIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@keyframes toastOut { to { transform: translateX(400px); opacity: 0; } }

/* Sidebar Panel */
section[data-testid="stSidebar"] {
    background: rgba(4, 6, 12, 0.95) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(0, 220, 255, 0.15) !important;
}

/* History Card */
.history-item {
    background: rgba(8, 12, 26, 0.75);
    border: 1px solid rgba(0, 220, 255, 0.2);
    border-radius: 12px; padding: 16px; margin-bottom: 12px;
}

/* ROBOT ASSISTANT STYLES - PRESERVED UNTOUCHED */
.robot-stage {
    position: fixed; bottom: 10px; right: 35px; z-index: 9998;
    display: flex; flex-direction: column; align-items: center;
    animation: robotEnter 1.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes robotEnter {
    0% { transform: translateY(180px) scale(0.8); opacity: 0; }
    100% { transform: translateY(0) scale(1); opacity: 1; }
}

.speech-bubble {
    position: relative;
    background: rgba(8, 14, 30, 0.92);
    border: 1px solid #00f2fe;
    border-radius: 18px; padding: 14px 20px; margin-bottom: 12px;
    font-family: 'Poppins', sans-serif; font-size: 14px; font-weight: 600; color: #ffffff;
    max-width: 340px; box-shadow: 0 0 25px rgba(0, 242, 254, 0.3);
    backdrop-filter: blur(14px);
    animation: bubblePulse 2.5s ease-in-out infinite;
}
.speech-bubble::after {
    content: ''; position: absolute; bottom: -12px; right: 45px;
    border-width: 12px 12px 0; border-style: solid;
    border-color: #00f2fe transparent;
}
@keyframes bubblePulse { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }

.robot-body {
    width: 120px; height: 150px; position: relative;
    animation: floatRobot 3s ease-in-out infinite;
}
@keyframes floatRobot { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }

.robot-head {
    width: 95px; height: 75px;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-radius: 24px 24px 18px 18px; margin: 0 auto; position: relative;
    box-shadow: inset 0 0 15px rgba(0, 242, 254, 0.2), 0 4px 20px rgba(0, 242, 254, 0.4);
    border: 2px solid #00f2fe;
}
.robot-antenna {
    position: absolute; top: -18px; left: 50%; transform: translateX(-50%);
    width: 4px; height: 18px; background: #00f2fe; box-shadow: 0 0 8px #00f2fe;
}
.robot-antenna::after {
    content: ''; position: absolute; top: -10px; left: -5px;
    width: 14px; height: 14px; background: #ff00e6; border-radius: 50%;
    box-shadow: 0 0 15px #ff00e6; animation: antennaPulse 1s infinite alternate;
}
@keyframes antennaPulse { 0% { transform: scale(0.8); opacity: 0.5; } 100% { transform: scale(1.2); opacity: 1; } }

.robot-eye {
    position: absolute; top: 22px; width: 18px; height: 18px;
    background: #00f2fe; border-radius: 50%;
    box-shadow: 0 0 14px #00f2fe; animation: eyeGlow 3s infinite;
}
.robot-eye.left { left: 18px; } .robot-eye.right { right: 18px; }
@keyframes eyeGlow { 0%, 92%, 100% { transform: scaleY(1); } 96% { transform: scaleY(0.15); } }

.robot-mouth {
    position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%);
    width: 36px; height: 6px; background: #00f2fe; border-radius: 4px;
    box-shadow: 0 0 10px #00f2fe; animation: mouthGlow 0.5s infinite alternate;
}
@keyframes mouthGlow { 0% { height: 4px; opacity: 0.7; } 100% { height: 12px; opacity: 1; } }

.robot-neck { width: 36px; height: 10px; background: #334155; margin: 0 auto; border-radius: 5px; }

.robot-torso {
    width: 105px; height: 65px; margin: 0 auto;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-radius: 16px; position: relative;
    border: 2px solid #7000ff;
    box-shadow: inset 0 0 15px rgba(112, 0, 255, 0.2), 0 4px 18px rgba(112, 0, 255, 0.4);
}
.robot-chest-light {
    position: absolute; top: 18px; left: 50%; transform: translateX(-50%);
    width: 22px; height: 22px; background: radial-gradient(circle, #00f2fe, #7000ff); border-radius: 50%;
    box-shadow: 0 0 20px #00f2fe; animation: reactorPulse 1.8s infinite;
}
@keyframes reactorPulse { 0%, 100% { transform: translateX(-50%) scale(1); opacity: 0.8; } 50% { transform: translateX(-50%) scale(1.2); opacity: 1; } }

.robot-arm {
    position: absolute; top: 8px; width: 12px; height: 50px;
    background: linear-gradient(180deg, #334155, #0f172a); border-radius: 6px; border: 1px solid #7000ff;
}
.robot-arm.left { left: -18px; animation: waveArm 2s ease-in-out infinite; transform-origin: top center; }
.robot-arm.right { right: -18px; }
@keyframes waveArm { 0%, 100% { transform: rotate(-10deg); } 50% { transform: rotate(18deg); } }
</style>

<!-- Floating Particles -->
<div class="particle" style="left:8%; animation-delay:0s;"></div>
<div class="particle" style="left:22%; animation-delay:2.5s;"></div>
<div class="particle" style="left:40%; animation-delay:5s;"></div>
<div class="particle" style="left:62%; animation-delay:1.5s;"></div>
<div class="particle" style="left:78%; animation-delay:3.5s;"></div>
<div class="particle" style="left:92%; animation-delay:6s;"></div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 3.5 ROBOT HELPER FUNCTIONS (WITH GUARANTEED VOICE)
# ═══════════════════════════════════════════════════════════
def show_robot(message_text, speak_text):
    """Shows animated robot + speaks via components.html"""
    st.markdown(f"""
    <div class="robot-stage">
        <div class="speech-bubble">{message_text}</div>
        <div class="robot-body">
            <div class="robot-head">
                <div class="robot-antenna"></div>
                <div class="robot-eye left"></div>
                <div class="robot-eye right"></div>
                <div class="robot-mouth"></div>
            </div>
            <div class="robot-neck"></div>
            <div class="robot-torso">
                <div class="robot-chest-light"></div>
                <div class="robot-arm left"></div>
                <div class="robot-arm right"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    components.html(f"""
    <script>
        function speak() {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                var u = new SpeechSynthesisUtterance("{speak_text}");
                u.lang = 'en-US';
                u.rate = 1.0; u.pitch = 1.1; u.volume = 1.0;
                window.speechSynthesis.speak(u);
            }}
        }}
        speak();
        setTimeout(speak, 500);
    </script>
    """, height=0, width=0)

# ═══════════════════════════════════════════════════════════
# 4. GLOBAL LANGUAGES DICTIONARY (17 LANGUAGES)
# ═══════════════════════════════════════════════════════════
LANGUAGES = {
    "English": {"code": "en", "speech_code": "en-US"},
    "Tamil": {"code": "ta", "speech_code": "ta-IN"},
    "Hindi": {"code": "hi", "speech_code": "hi-IN"},
    "Telugu": {"code": "te", "speech_code": "te-IN"},
    "Kannada": {"code": "kn", "speech_code": "kn-IN"},
    "Malayalam": {"code": "ml", "speech_code": "ml-IN"},
    "Korean": {"code": "ko", "speech_code": "ko-KR"},
    "Chinese": {"code": "zh-CN", "speech_code": "zh-CN"},
    "Urdu": {"code": "ur", "speech_code": "ur-PK"},
    "Bengali": {"code": "bn", "speech_code": "bn-IN"},
    "Arabic": {"code": "ar", "speech_code": "ar-SA"},
    "Punjabi": {"code": "pa", "speech_code": "pa-IN"},
    "French": {"code": "fr", "speech_code": "fr-FR"},
    "Spanish": {"code": "es", "speech_code": "es-ES"},
    "German": {"code": "de", "speech_code": "de-DE"},
    "Japanese": {"code": "ja", "speech_code": "ja-JP"},
    "Russian": {"code": "ru", "speech_code": "ru-RU"}
}

# ═══════════════════════════════════════════════════════════
# 5. SESSION STATES
# ═══════════════════════════════════════════════════════════
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    if not st.session_state.get("_user_explicit_logout", False):
        st.session_state["logged_in"] = True
        st.session_state["view"] = "main"

if "page" not in st.session_state: st.session_state["page"] = "dashboard"
if "nav_menu" not in st.session_state: st.session_state["nav_menu"] = "🏠 Dashboard"

# Voice Flags
if "register_voice_played" not in st.session_state: st.session_state["register_voice_played"] = False
if "reg_success_voice" not in st.session_state: st.session_state["reg_success_voice"] = False
if "home_voice_played" not in st.session_state: st.session_state["home_voice_played"] = False
if "text_voice_played" not in st.session_state: st.session_state["text_voice_played"] = False
if "voice_t_voice_played" not in st.session_state: st.session_state["voice_t_voice_played"] = False
if "voice_c_voice_played" not in st.session_state: st.session_state["voice_c_voice_played"] = False
if "doc_voice_played" not in st.session_state: st.session_state["doc_voice_played"] = False
if "conv_voice_played" not in st.session_state: st.session_state["conv_voice_played"] = False
if "coach_voice_played" not in st.session_state: st.session_state["coach_voice_played"] = False
if "conversation_transcript" not in st.session_state: st.session_state["conversation_transcript"] = []
if "conversation_history" not in st.session_state: st.session_state["conversation_history"] = []
if "coach_last_spoken" not in st.session_state: st.session_state["coach_last_spoken"] = ""
if "conv_spkA_lang" not in st.session_state: st.session_state["conv_spkA_lang"] = "English"
if "conv_spkB_lang" not in st.session_state: st.session_state["conv_spkB_lang"] = "Tamil"
if "elevenlabs_api_key" not in st.session_state: st.session_state["elevenlabs_api_key"] = ElevenLabsClient._resolve_api_key()
if "cloning_engine_choice" not in st.session_state: st.session_state["cloning_engine_choice"] = "ElevenLabs Instant Voice Cloning"
if "active_cloned_voice_id" not in st.session_state: st.session_state["active_cloned_voice_id"] = None
if "cloned_voice_name" not in st.session_state: st.session_state["cloned_voice_name"] = "My Authentic Voice"
if "selected_el_model" not in st.session_state: st.session_state["selected_el_model"] = "eleven_multilingual_v2"
if "record_duration" not in st.session_state: st.session_state["record_duration"] = 8

# ═══════════════════════════════════════════════════════════
# 6. HELPER UI COMPONENTS & PIPELINE VISUALIZER
# ═══════════════════════════════════════════════════════════
def show_sound_wave():
    st.markdown("""<div class="wave-container">
        <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
        <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
    </div>""", unsafe_allow_html=True)

def show_countdown(seconds):
    st.markdown(f"""<div class="countdown-display">{seconds}</div>
    <div class="wave-container"><div class="wave-bar"></div><div class="wave-bar"></div>
    <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div></div>""", unsafe_allow_html=True)

def show_toast(message):
    st.markdown(f'<div class="toast">⚡ {message}</div>', unsafe_allow_html=True)

def show_ai_pipeline(module_type="text", active_step=1):
    """Renders Futuristic Dynamic Module-Specific AI Processing Pipeline"""
    if module_type == "text":
        title = "⌨️ NEURAL TEXT TRANSLATION WORKFLOW"
        steps = [
            ("01 ⌨️", "Text Input"),
            ("02 🌐", "Text Translation"),
            ("03 📝", "Translated Text")
        ]
    elif module_type == "voice":
        title = "🎙️ REAL-TIME VOICE TRANSLATION WORKFLOW"
        steps = [
            ("01 🎙️", "Speech Input"),
            ("02 🧠", "Speech Recognition"),
            ("03 🌐", "Text Translation"),
            ("04 🔊", "Translated Speech")
        ]
    elif module_type == "clone":
        title = "🧬 ZERO-SHOT VOICE CLONING WORKFLOW"
        steps = [
            ("01 🎙️", "Speech Recognition"),
            ("02 🌐", "Text Translation"),
            ("03 📝", "Translated Text"),
            ("04 🧬", "Voice Cloning"),
            ("05 🔊", "Cloned Audio")
        ]
    elif module_type == "doc":
        title = "📂 DOCUMENT AUDIO WORKFLOW"
        steps = [
            ("01 📄", "Document Input"),
            ("02 🔍", "Text Extraction"),
            ("03 🌐", "Text Translation"),
            ("04 🔊", "Audio Synthesis")
        ]
    elif module_type == "conv":
        title = "💬 DUAL INTERPRETER WORKFLOW"
        steps = [
            ("01 🗣️", "Speaker Input"),
            ("02 🧠", "Speech / Text"),
            ("03 🌐", "Cross Translation"),
            ("04 🎧", "Recipient Feed")
        ]
    elif module_type == "coach":
        title = "🎯 ACCENT & GRAMMAR WORKFLOW"
        steps = [
            ("01 🎙️", "Speech Input"),
            ("02 🧠", "Speech Recognition"),
            ("03 🔍", "NLP Grammar Inspection"),
            ("04 📊", "Accuracy Evaluation")
        ]
    else:
        title = "⚡ NEURAL PROCESSING PIPELINE"
        steps = [
            ("01 🎙️", "Speech Capture"),
            ("02 🧠", "Recognition"),
            ("03 🌐", "Translation"),
            ("04 🔊", "Voice Synthesis")
        ]

    html = f'''<div class="pipeline-box">
        <div class="pipeline-header">{title}</div>
        <div class="pipeline-steps">'''
    
    total_steps = len(steps)
    for idx, (icon, label) in enumerate(steps, 1):
        if idx < active_step:
            status_cls = "completed"
            check_icon = "✓ "
        elif idx == active_step:
            status_cls = "active"
            check_icon = ""
        else:
            status_cls = ""
            check_icon = ""

        html += f'<div class="step-item {status_cls}">{check_icon}{icon} {label}</div>'
        if idx < total_steps:
            html += '<div class="pipeline-arrow">➔</div>'

    html += '</div></div>'
    st.markdown(html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 7. LOGIN & REGISTER PAGES
# ═══════════════════════════════════════════════════════════
if not st.session_state["logged_in"] and st.session_state["view"] == "login":
    if st.session_state["reg_success_voice"]:
        st.session_state["reg_success_voice"] = False
        show_robot("✅ Account Created!<br>Please login to enter AI Command Center.", "Account Created, please login")
    
    col_spacer1, col_main, col_spacer2 = st.columns([0.8, 2.4, 0.8])
    with col_main:
        st.markdown("""
        <div class="ai-glass-card" style="text-align:center; margin-top:20px; padding:35px 30px !important;">
            <div style="font-size:55px; filter:drop-shadow(0 0 18px #00f2fe); margin-bottom:12px;">⚡</div>
            <div class='glow-title' style="font-size:32px; margin-bottom:4px;">AI NEURAL TRANSLATOR</div>
            <div class='subtitle-anim' style="font-size:14px; margin-bottom:20px;">Welcome Back • Enter Operator Credentials</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
        
        email_input = st.text_input("📬 User Email ID", placeholder="Enter Email ID", key="login_email")
        password_input = st.text_input("🔑 Password", type="password", placeholder="Enter Password", key="login_pass")
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Access Portal 🚀", key="sub_btn", use_container_width=True):
                current_users = load_users()
                if email_input in current_users and current_users[email_input] == password_input:
                    st.session_state["logged_in"] = True
                    st.session_state["page"] = "dashboard"
                    st.session_state["nav_menu"] = "🏠 Dashboard"
                    st.session_state["home_voice_played"] = False
                    show_toast("Access Granted! Welcome Operator.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials! Use demo: admin@gmail.com / 12345")
        with col2:
            if st.button("Create Profile 📝", key="reg_btn", use_container_width=True):
                st.session_state["view"] = "register"
                st.session_state["register_voice_played"] = False
                st.rerun()

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("⚡ Instant Demo Login (Go Directly to Dashboard)", key="guest_demo_btn", use_container_width=True):
            st.session_state["logged_in"] = True
            st.session_state["page"] = "dashboard"
            st.session_state["nav_menu"] = "🏠 Dashboard"
            st.session_state["home_voice_played"] = False
            st.rerun()

elif not st.session_state["logged_in"] and st.session_state["view"] == "register":
    col_spacer1, col_main, col_spacer2 = st.columns([0.8, 2.4, 0.8])
    with col_main:
        st.markdown("""
        <div class="ai-glass-card" style="text-align:center; margin-top:20px; padding:35px 30px !important;">
            <div style="font-size:55px; filter:drop-shadow(0 0 18px #7000ff); margin-bottom:12px;">📝</div>
            <div class='glow-title' style="font-size:32px; margin-bottom:4px;">OPERATOR REGISTRATION</div>
            <div class='subtitle-anim' style="font-size:14px; margin-bottom:20px;">Join the Future of Real-Time Voice Cloning</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
        
        new_email = st.text_input("📬 New User Email ID", placeholder="example@gmail.com", key="reg_email_field")
        new_password = st.text_input("🔑 New Password", type="password", key="reg_pass_field")
        confirm_password = st.text_input("🔄 Confirm Password", type="password", key="reg_conf_field")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Save Credentials 💾", key="save_pwd"):
            email_clean = new_email.strip()
            pass_clean = new_password.strip()
            conf_clean = confirm_password.strip()

            if not email_clean or not pass_clean:
                st.error("⚠️ Please fill all required fields!")
            elif conf_clean and pass_clean != conf_clean:
                st.error("❌ Passwords do not match!")
            else:
                save_user(email_clean, pass_clean)
                st.session_state["logged_in"] = True
                st.session_state["page"] = "dashboard"
                st.session_state["nav_menu"] = "🏠 Dashboard"
                st.session_state["home_voice_played"] = False
                show_toast("Account Registered & Logged In!")
                time.sleep(0.5)
                st.rerun()
        if st.button("Back to Portal 🔙", key="back_home"):
            st.session_state["view"] = "login"
            st.rerun()
    
    if not st.session_state["register_voice_played"]:
        st.session_state["register_voice_played"] = True
        show_robot("Hi! 👋<br>Create your AI Command credentials 👇", "Hi, create your credentials")

# ═══════════════════════════════════════════════════════════
# 8. MAIN APP (LOGGED IN)
# ═══════════════════════════════════════════════════════════
else:
    # ─── SIDEBAR CONTROL PANEL ───
    with st.sidebar:
        st.markdown("<div style='font-family: Orbitron; font-size:20px; color:#ffffff; font-weight:900; letter-spacing:2.5px; text-shadow:0 0 15px rgba(0, 220, 255, 0.4); text-align:center;'>AI TRANSLATOR</div>", unsafe_allow_html=True)
        st.markdown("<hr class='neon-divider' style='margin:12px 0 10px 0;'>", unsafe_allow_html=True)
        
        # Live ElevenLabs Telemetry Indicator
        el_key_present = bool(st.session_state.get("elevenlabs_api_key"))
        badge_text = "⚡ ELEVENLABS ACTIVE (STARTER)" if el_key_present else "⚠️ ELEVENLABS OFFLINE"
        badge_col = "#00f2fe" if el_key_present else "#f43f5e"
        st.markdown(f"""
        <div style="background: rgba(0, 242, 254, 0.08); border: 1px solid {badge_col}; border-radius: 8px; padding: 6px 10px; margin-bottom: 14px; text-align: center;">
            <span style="font-family:'Orbitron'; font-size:10px; color:{badge_col}; font-weight:700; letter-spacing:1px;">{badge_text}</span>
        </div>
        """, unsafe_allow_html=True)
        
        current_page = st.session_state.get("page", "dashboard")
        
        menu_items = [
            ("🏠 Dashboard", "dashboard"),
            ("💬 Dual Conversation", "conversation_mode"),
            ("⌨️ Text Translation", "text_translate"),
            ("🎙️ Voice Translation", "voice_translate"),
            ("🧬 Voice Cloning", "voice_clone"),
            ("📄 Document Translator", "doc_translate"),
            ("🎯 Accent Coach", "accent_coach"),
            ("📜 History", "history"),
            ("⚙️ Settings", "settings")
        ]
        
        for label, page_id in menu_items:
            is_active = (current_page == page_id)
            btn_type = "primary" if is_active else "secondary"
            icon_prefix = "👉 " if is_active else ""
            if st.button(f"{icon_prefix}{label}", key=f"nav_btn_{page_id}", use_container_width=True, type=btn_type):
                st.session_state["page"] = page_id
                st.session_state["nav_menu"] = label
                st.rerun()

        st.markdown("<hr class='neon-divider' style='margin:20px 0 12px 0;'>", unsafe_allow_html=True)
        
        if st.button("🔒 Logout", key="btn_logout_sidebar", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["_user_explicit_logout"] = True
            st.session_state["view"] = "login"
            st.rerun()

    # ─────────────────────────────────────────────────────────
    # SCREEN: DASHBOARD HOME (6-CARD GRID)
    # ─────────────────────────────────────────────────────────
    if st.session_state["page"] == "dashboard":
        st.markdown("""
        <div class="ai-glass-card" style="text-align:center; padding:35px 25px !important; margin-bottom:25px;">
            <h1 class="glow-title" style="font-size:36px; margin-bottom:6px;">AI TRANSLATOR</h1>
            <div class="subtitle-anim" style="font-size:15px; margin-bottom:18px;">Futuristic AI Neural Translation System</div>
            <p style="color:#cbd5e1; max-width:600px; margin:0 auto 20px auto; font-size:14px; line-height:1.6;">
                Real-Time Voice, Text, Dual Conversation, Document Translation & Pronunciation Coaching.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<hr class='neon-divider' style='margin: 20px 0 25px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#00f2fe; font-family:Orbitron; text-align:center; margin-bottom:20px;'>⚡ SYSTEM NEURAL MODULES</h4>", unsafe_allow_html=True)
        
        # ROW 1: Text, Voice, Clone
        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            st.markdown("""
            <div class="dash-card">
                <div class="dash-icon">⌨️</div>
                <div class="dash-title">TEXT</div>
                <div class="dash-desc">Translate written text in real-time.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("OPEN MODULE 🚀", key="btn_dash_text"):
                st.session_state["page"] = "text_translate"
                st.session_state["nav_menu"] = "⌨️ Text Translation" 
                st.session_state["text_voice_played"] = False
                st.rerun()
            
        with r1_c2:
            st.markdown("""
            <div class="dash-card">
                <div class="dash-icon">🎙️</div>
                <div class="dash-title">VOICE</div>
                <div class="dash-desc">Speech recognition ➔ translation ➔ translated speech.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("OPEN MODULE 🚀", key="btn_dash_voice"):
                st.session_state["page"] = "voice_translate"
                st.session_state["nav_menu"] = "🎙️ Voice Translation"
                st.session_state["voice_t_voice_played"] = False
                st.rerun()
            
        with r1_c3:
            st.markdown("""
            <div class="dash-card">
                <div class="dash-icon">🧬</div>
                <div class="dash-title">CLONE</div>
                <div class="dash-desc">Voice cloning & voice profile synthesis.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("OPEN MODULE 🚀", key="btn_dash_clone"):
                st.session_state["page"] = "voice_clone"
                st.session_state["nav_menu"] = "🧬 Voice Cloning"
                st.session_state["voice_c_voice_played"] = False
                st.rerun()

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

        # ROW 2: Dual Conversation, Document Translator, Accent Coach
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            st.markdown("""
            <div class="dash-card">
                <div class="dash-icon">💬</div>
                <div class="dash-title">DUAL CONVERSATION</div>
                <div class="dash-desc">Two-way conversation interface with Text / Voice modes.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("OPEN MODULE 🚀", key="btn_dash_dual"):
                st.session_state["page"] = "conversation_mode"
                st.session_state["nav_menu"] = "💬 Dual Conversation"
                st.session_state["conv_voice_played"] = False
                st.rerun()

        with r2_c2:
            st.markdown("""
            <div class="dash-card">
                <div class="dash-icon">📄</div>
                <div class="dash-title">DOCUMENT TRANSLATOR</div>
                <div class="dash-desc">Translate uploaded TXT and PDF documents easily.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("OPEN MODULE 🚀", key="btn_dash_doc"):
                st.session_state["page"] = "doc_translate"
                st.session_state["nav_menu"] = "📄 Document Translator"
                st.session_state["doc_voice_played"] = False
                st.rerun()

        with r2_c3:
            st.markdown("""
            <div class="dash-card">
                <div class="dash-icon">🎯</div>
                <div class="dash-title">ACCENT COACH</div>
                <div class="dash-desc">Practice and evaluate pronunciation & accent accuracy.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("OPEN MODULE 🚀", key="btn_dash_coach"):
                st.session_state["page"] = "accent_coach"
                st.session_state["nav_menu"] = "🎯 Accent Coach"
                st.session_state["coach_voice_played"] = False
                st.rerun()

        if not st.session_state["home_voice_played"]:
            st.session_state["home_voice_played"] = True
            show_robot("🎉 Welcome to AI Translator!<br>Select a module card to begin.", "Welcome to AI Translator")

    # ─────────────────────────────────────────────────────────
    # SCREEN: TEXT TRANSLATION
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "text_translate":
        col_spacer, col_main, col_side = st.columns([0.1, 2.8, 0.1])
        with col_main:
            if st.button("← Back to Dashboard", key="text_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["nav_menu"] = "🏠 Dashboard"
                st.session_state["text_voice_played"] = False
                st.rerun()
            
            st.markdown("<div class='glow-title' style='font-size:32px;'>⌨️ NEURAL TEXT MODULE</div>", unsafe_allow_html=True)
            st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)

            sub_feature = st.radio("Select Text Processing Feature:", ["⚡ Standard Translation", "💬 Dual Conversation", "📄 Document Translator", "🎯 Accent Coach"], horizontal=True, key="sub_feat_text")
            st.markdown("<br>", unsafe_allow_html=True)

            if sub_feature == "💬 Dual Conversation":
                render_conversation_mode_module(LANGUAGES)
            elif sub_feature == "📄 Document Translator":
                # Render document translator workflow
                st.markdown("### 🌐 Target Language Configuration")
                output_lang_name = st.selectbox("Select Target Language:", list(LANGUAGES.keys()), index=1, key="doc_out_lang_sub")
                output_lang_code = LANGUAGES[output_lang_name]["code"]
                uploaded_file = st.file_uploader("Upload .txt or .pdf file:", type=["txt", "pdf"], key="doc_uploader_sub")
                if uploaded_file is not None and st.button("⚡ Extract & Translate Document", key="btn_doc_sub_proc"):
                    extracted_text = ""
                    if uploaded_file.name.endswith(".txt"): extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
                    elif uploaded_file.name.endswith(".pdf"): extracted_text = "\n".join([page.extract_text() for page in pypdf.PdfReader(uploaded_file).pages if page.extract_text()])
                    if extracted_text.strip():
                        translated_doc = safe_translate(extracted_text[:3000], source_lang='auto', target_lang=output_lang_code)
                        st.success(f"Extracted & Translated {len(extracted_text)} characters!")
                        st.write("Preview:", translated_doc[:500])
            elif sub_feature == "🎯 Accent Coach":
                render_accent_coach_module(LANGUAGES)
            else:
                # Standard Text Translation Workflow
                show_ai_pipeline("text", active_step=1)

                st.markdown("### 🌐 Language Configuration")
                col_in, col_out = st.columns(2)
                with col_in:
                    input_lang_name = st.selectbox("1️⃣ Input Language:", list(LANGUAGES.keys()), index=0, key="tt_in")
                with col_out:
                    output_lang_name = st.selectbox("2️⃣ Output Language:", list(LANGUAGES.keys()), index=1, key="tt_out")
            
                input_lang_code = LANGUAGES[input_lang_name]["code"]
                output_lang_code = LANGUAGES[output_lang_name]["code"]

                st.markdown("### ⚡ Type Text to Translate")
                quick_text = st.text_area("Enter text here:", placeholder="Type anything...", height=130)
                
                if st.button("⚡ Execute Neural Translation"):
                    if quick_text.strip():
                        try:
                            show_ai_pipeline("text", active_step=2)
                            
                            # Handle same language selection vs explicit source/target translation
                            if input_lang_name == output_lang_name:
                                translated = quick_text
                            else:
                                translated = safe_translate(quick_text, source_lang=input_lang_code, target_lang=output_lang_code)
                            
                            show_ai_pipeline("text", active_step=3)
                            # Glassmorphism Cards Output
                            st.markdown(f"""
                            <div class="glass-card-original">
                                <div class="card-label orig">📝 ORIGINAL ({input_lang_name})</div>
                                <div class="card-text">{quick_text}</div>
                            </div>
                            <div style="text-align:center; font-size:24px; color:#7000ff; margin: -5px 0;">⬇️</div>
                            <div class="glass-card-translated">
                                <div class="card-label trans">✨ TRANSLATED ({output_lang_name})</div>
                                <div class="card-text" style="color:#00f2fe; font-size:22px;">{translated}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            save_history({
                                "time": time.strftime("%Y-%m-%d %H:%M"),
                                "original": quick_text, "translated": translated,
                                "from": input_lang_name, "to": output_lang_name
                            })
                            show_toast("Translation Logged!")
                            show_robot("✅ Translation complete!<br>Enter text to translate again.", "Translation complete")
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("Please enter text to translate.")
                
                if not st.session_state["text_voice_played"]:
                    st.session_state["text_voice_played"] = True
                    show_robot("⌨️ Type your text below.<br>I will translate it in milliseconds!", "Type your text below, I will translate it in milliseconds")

    # ─────────────────────────────────────────────────────────
    # SCREEN: VOICE TRANSLATION
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "voice_translate":
        col_spacer, col_main, col_side = st.columns([0.1, 2.8, 0.1])
        with col_main:
            if st.button("← Back to Dashboard", key="vt_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["nav_menu"] = "🏠 Dashboard"
                st.session_state["voice_t_voice_played"] = False
                st.rerun()
            render_voice_translate_module(LANGUAGES)

    # ─────────────────────────────────────────────────────────
    # SCREEN: VOICE CLONING LAB
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "voice_clone":
        col_spacer, col_main, col_side = st.columns([0.1, 2.8, 0.1])
        with col_main:
            if st.button("← Back to Dashboard", key="vc_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["nav_menu"] = "🏠 Dashboard"
                st.session_state["voice_c_voice_played"] = False
                st.rerun()
            render_voice_clone_module(LANGUAGES)

    # ─────────────────────────────────────────────────────────
    # SCREEN: DOCUMENT & FILE
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "doc_translate":
        col_spacer, col_main, col_side = st.columns([0.2, 2.6, 0.2])
        with col_main:
            if st.button("← Back to Dashboard", key="doc_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["doc_voice_played"] = False
                st.rerun()
            
            st.markdown("<div class='glow-title' style='font-size:32px;'>📂 DOCUMENT & FILE</div>", unsafe_allow_html=True)
            st.markdown("<div class='subtitle-anim'>Extract Text from .TXT / .PDF, Translate & Synthesize Audio Stream</div>", unsafe_allow_html=True)
            st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)
            
            st.markdown("### 🌐 Target Language Configuration")
            output_lang_name = st.selectbox("Select Target Language:", list(LANGUAGES.keys()), index=1, key="doc_out_lang")
            output_lang_code = LANGUAGES[output_lang_name]["code"]
            
            st.markdown("### 📂 Upload Document (.txt or .pdf)")
            uploaded_file = st.file_uploader("Upload file:", type=["txt", "pdf"], key="doc_uploader")
            
            if uploaded_file is not None:
                file_size_kb = uploaded_file.size / 1024.0
                st.info(f"📄 File Uploaded: **{uploaded_file.name}** ({file_size_kb:.1f} KB)")
                
                if st.button("⚡ Extract, Translate & Synthesize Audio", key="btn_doc_process"):
                    extracted_text = ""
                    with st.spinner("Extracting Document Text..."):
                        try:
                            if uploaded_file.type == "text/plain" or uploaded_file.name.endswith(".txt"):
                                extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
                            elif uploaded_file.type == "application/pdf" or uploaded_file.name.endswith(".pdf"):
                                pdf_reader = pypdf.PdfReader(uploaded_file)
                                extracted_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
                        except Exception as ext_err:
                            st.error(f"Text Extraction Error: {ext_err}")
                    
                    if extracted_text and extracted_text.strip():
                        st.success(f"Successfully Extracted {len(extracted_text)} Characters!")
                        
                        with st.spinner("Translating Document Text..."):
                            try:
                                text_to_translate = extracted_text[:4500] if len(extracted_text) > 4500 else extracted_text
                                translated_doc_text = safe_translate(text_to_translate, source_lang='auto', target_lang=output_lang_code)
                                
                                # Glassmorphism Preview Cards
                                st.markdown(f"""
                                <div class="glass-card-original">
                                    <div class="card-label orig">📝 ORIGINAL DOCUMENT SAMPLE ({uploaded_file.name})</div>
                                    <div class="card-text">{text_to_translate[:400]}...</div>
                                </div>
                                <div style="text-align:center; font-size:24px; color:#7000ff; margin: -5px 0;">⬇️</div>
                                <div class="glass-card-translated">
                                    <div class="card-label trans">✨ TRANSLATED DOCUMENT TEXT ({output_lang_name})</div>
                                    <div class="card-text" style="color:#00f2fe; font-size:20px;">{translated_doc_text[:600]}...</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Audio Stream Synthesis
                                with st.spinner("Synthesizing Document Audio with ElevenLabs Multilingual Engine..."):
                                    client = ElevenLabsClient(st.session_state.get("elevenlabs_api_key"))
                                    audio_bytes = None
                                    if client.is_configured():
                                        try:
                                            narrator_id = st.session_state.get("active_cloned_voice_id") or "JBFqnCBsd6RMkjVDRZzb"
                                            audio_bytes = client.text_to_speech(
                                                text=translated_doc_text[:2000],
                                                voice_id=narrator_id,
                                                model_id="eleven_multilingual_v2"
                                            )
                                        except Exception as el_doc_err:
                                            print(f"[ElevenLabs Doc Warning]: {el_doc_err}")

                                    if not audio_bytes or len(audio_bytes) < 500:
                                        tts = gTTS(text=translated_doc_text[:2000], lang=output_lang_code, slow=False)
                                        doc_audio_path = "data/temp/doc_translated_audio.mp3"
                                        os.makedirs("data/temp", exist_ok=True)
                                        tts.save(doc_audio_path)
                                        with open(doc_audio_path, "rb") as f_aud:
                                            audio_bytes = f_aud.read()
                                
                                st.markdown(f"### 🎧 Synthesized Document Audio ({output_lang_name})")
                                st.audio(audio_bytes, format="audio/mp3")
                                
                                st.markdown("### 📥 Downloads & Export Options")
                                col_d1, col_d2 = st.columns(2)
                                with col_d1:
                                    st.download_button(
                                        label="📥 Download Translated Text (.txt)",
                                        data=translated_doc_text,
                                        file_name=f"translated_{output_lang_code}_{uploaded_file.name}.txt",
                                        mime="text/plain",
                                        key="dl_doc_txt"
                                    )
                                with col_d2:
                                    st.download_button(
                                        label="🎧 Download Audio Stream (.mp3)",
                                        data=audio_bytes,
                                        file_name=f"translated_audio_{output_lang_code}.mp3",
                                        mime="audio/mp3",
                                        key="dl_doc_mp3"
                                    )
                                
                                save_history({
                                    "time": time.strftime("%Y-%m-%d %H:%M"),
                                    "original": f"Doc: {uploaded_file.name}", "translated": translated_doc_text[:100],
                                    "from": "Document", "to": output_lang_name
                                })
                                show_toast("Document Translation Complete!")
                                show_robot("✅ Document Translated & Audio Synthesized!<br>Download files below.", "Document Translated and Audio Synthesized")
                                
                            except Exception as trans_err:
                                st.error(f"Translation/Synthesis Error: {trans_err}")
                    else:
                        st.warning("No readable text could be extracted from this document.")

            if not st.session_state["doc_voice_played"]:
                st.session_state["doc_voice_played"] = True
                show_robot("📂 Upload a .txt or .pdf document.<br>I will extract text, translate, and synthesize audio!", "Upload a document to extract text and synthesize audio")

    # ─────────────────────────────────────────────────────────
    # SCREEN: USER GUIDE & MANUAL
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "user_guide":
        col_spacer, col_main, col_side = st.columns([0.1, 2.8, 0.1])
        with col_main:
            if st.button("← Back to Dashboard", key="guide_back"):
                st.session_state["page"] = "dashboard"
                st.rerun()
            render_user_guide_module()

    # ─────────────────────────────────────────────────────────
    # SCREEN: LIVE DUAL-USER CONVERSATION INTERPRETER
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "conversation_mode":
        col_spacer, col_main, col_side = st.columns([0.1, 2.8, 0.1])
        with col_main:
            if st.button("← Back to Dashboard", key="conv_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["conv_voice_played"] = False
                st.rerun()
            render_conversation_mode_module(LANGUAGES)

    # ─────────────────────────────────────────────────────────
    # SCREEN: AI PRONUNCIATION & ACCENT COACH
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "accent_coach":
        col_spacer, col_main, col_side = st.columns([0.1, 2.8, 0.1])
        with col_main:
            if st.button("← Back to Dashboard", key="coach_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["coach_voice_played"] = False
                st.rerun()
            render_accent_coach_module(LANGUAGES)

    # ─────────────────────────────────────────────────────────
    # SCREEN: HISTORY
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "history":
        col_spacer, col_main, col_side = st.columns([0.05, 2.9, 0.05])
        with col_main:
            if st.button("← Back to Dashboard", key="history_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["nav_menu"] = "🏠 Dashboard"
                st.rerun()
            st.markdown("<div class='glow-title' style='font-size:32px;'>📜 TRANSLATION & CHAT HISTORY LOGS</div>", unsafe_allow_html=True)
            st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)
        
            history = load_history()
            if history:
                # Top Toolbar: Stats, Export, and Delete All
                t_col1, t_col2, t_col3 = st.columns([2.2, 1.1, 1.3])
                with t_col1:
                    st.markdown(f"""
                    <div style="padding-top:6px; color:#94a3b8; font-family:'Orbitron'; font-size:12px;">
                        TOTAL RECORDS: <span style="color:#00f2fe; font-weight:700; font-size:15px;">{len(history)}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with t_col2:
                    json_str = json.dumps(history, indent=4, ensure_ascii=False)
                    st.download_button(
                        label="💾 Export JSON",
                        data=json_str,
                        file_name="translation_history.json",
                        mime="application/json",
                        key="btn_export_history",
                        use_container_width=True
                    )
                with t_col3:
                    if st.button("🗑️ Delete All History", key="btn_clear_all_history", use_container_width=True):
                        clear_all_history()
                        show_toast("Chat and translation history deleted!")
                        st.rerun()

                st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

                for idx, item in enumerate(history):
                    c_card, c_del = st.columns([5.2, 1.0])
                    with c_card:
                        st.markdown(f"""<div class="history-item" style="margin-bottom:0px;">
                            <div style="color:#00f2fe; font-family:'Orbitron'; font-size:12px; margin-bottom:6px;">🕒 {item.get('time','')} | 🔄 {item.get('from','')} ➔ {item.get('to','')}</div>
                            <div style="color:#cbd5e1; font-size:14px; margin-bottom:4px;"><b>🔵 Original:</b> {item.get('original','')}</div>
                            <div style="color:#00f2fe; font-size:15px; font-weight:600;"><b>🟢 Translated:</b> {item.get('translated','')}</div>
                        </div>""", unsafe_allow_html=True)
                    with c_del:
                        st.markdown("<div style='padding-top:18px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️ Delete", key=f"del_history_{idx}", use_container_width=True, help="Remove this history record"):
                            delete_history_item(idx)
                            show_toast("History record deleted!")
                            st.rerun()
                    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
            else:
                st.warning("No translation or chat logs found.")

    # ─────────────────────────────────────────────────────────
    # SCREEN: REGISTRATION ADMIN
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "registration":
        st.markdown("<div class='glow-title' style='font-size:32px;'>📧 USER MANAGEMENT</div>", unsafe_allow_html=True)
        st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### ➕ Register New Operator")
            new_email = st.text_input("📬 New User Email", key="admin_new_email")
            new_pwd = st.text_input("🔑 New Password", type="password", key="admin_new_pwd")
            if st.button("Register Operator", key="admin_reg_btn"):
                if new_email and new_pwd:
                    save_user(new_email.strip(), new_pwd.strip())
                    show_toast("User Registered!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Please fill all required fields.")
            
        with col2:
            st.markdown("### 👥 Active Operators")
            users = load_users()
            st.info(f"Total Registered Users: {len(users)}")
            for u in users:
                st.markdown(f"""<div style="background:rgba(13, 18, 45, 0.6); border:1px solid rgba(0, 242, 254, 0.2); border-radius:10px; padding:12px; margin-bottom:8px; color:#fff; font-family:'Orbitron'; font-size:13px;">👤 {u}</div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # SCREEN: SETTINGS
    # ─────────────────────────────────────────────────────────
    elif st.session_state["page"] == "settings":
        col_spacer, col_main, col_side = st.columns([0.1, 2.8, 0.1])
        with col_main:
            if st.button("← Back to Dashboard", key="settings_back"):
                st.session_state["page"] = "dashboard"
                st.session_state["nav_menu"] = "🏠 Dashboard"
                st.rerun()
            render_settings_module(LANGUAGES)
