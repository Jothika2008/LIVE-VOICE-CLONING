# AI Translator Pro — Real-Time Neural Voice Translation System

A production-grade, modular Streamlit application for real-time neural voice translation, text translation, and voice cloning built with Python 3.10+, PyTorch/Coqui XTTS-v2, Audio DSP (`librosa`, `scipy`, `numpy`, `soundfile`), and a Cyberpunk/Neon HUD interface.

---

## 🌟 Key Features

1. **Cyberpunk Neon HUD Interface:**
   - Dark gradient styling (`#0a0a12`), glassmorphism cards (`backdrop-filter: blur`), Orbitron & Poppins Google typography, animated robot mascot assistant, and audio wave visualizer animations.
   - Top Dashboard 3-card live metrics: Total Translations, Active Voice Model, Compute Device.
   - Dynamic multi-view routing via custom sidebar navigation.

2. **Core Audio DSP Pipeline (`core/audio_dsp.py`):**
   - Spectral Denoising & Butterworth Bandpass filtering.
   - High-Quality Resampling (16000, 22050, 24000, 44100 Hz).
   - Silence trimming (`librosa.effects.trim`).
   - Peak & RMS amplitude normalization (-1.0 dBFS target).

3. **Multi-Engine TTS & Voice Cloning (`core/tts_engine.py`):**
   - Standard Mode: Fast `gTTS` multi-lingual synthesis.
   - Cloning Mode: Coqui XTTS-v2 speaker conditioning.
   - High-Quality DSP Pitch & Timbre Conditioning Fallback (zero-crash execution).

4. **6 Dedicated Modules:**
   - **Module 1: Authentication (`auth.py`)** — Hashed PBKDF2 user authentication and profile store.
   - **Module 2: Text Translation (`text_translate.py`)** — Instant multi-lingual text translation & audio preview.
   - **Module 3: Real-Time Voice Translation (`voice_translate.py`)** — Mic input / file recording, STT, translation, and auto speech playback.
   - **Module 4: Neural Voice Cloning Engine (`voice_clone.py`)** — Reference audio DSP clean & speaker voice cloning.
   - **Module 5: History & Export (`history.py`)** — Timestamped transcripts, search filters, and JSON/WAV export.
   - **Module 6: Settings (`settings.py`)** — CUDA GPU/CPU device toggle, sample rate, and noise threshold configuration.

---

## 🚀 How to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch Streamlit Application
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.
