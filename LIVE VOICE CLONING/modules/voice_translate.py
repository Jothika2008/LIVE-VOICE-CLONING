"""
modules/voice_translate.py
═══════════════════════════════════════════════════════════════
Production ElevenLabs Real-Time Neural Voice Translation Module
Features:
- Microphone capture & audio file upload
- Speech-to-Text (STT) Recognition
- Resilient Multilingual Text Translation
- Synthesis via ElevenLabs: User Cloned Voice or ElevenLabs Neural Personas
- Futuristic HUD Visualizer & Audio Downloads
═══════════════════════════════════════════════════════════════
"""

import os
import time
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import streamlit as st
from core.elevenlabs_client import ElevenLabsClient
from core.tts_engine import TTSEngine
from core.translator import safe_translate

def render_voice_translate_module(LANGUAGES: dict):
    """
    Renders Real-Time Voice Translation with ElevenLabs Neural Personas or Cloned Voice.
    """
    client = ElevenLabsClient(st.session_state.get("elevenlabs_api_key"))
    tts_engine = TTSEngine(api_key=st.session_state.get("elevenlabs_api_key"))

    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(14, 23, 42, 0.95), rgba(8, 14, 30, 0.95)); border: 1px solid #00f2fe; border-radius: 14px; padding: 20px 24px; margin-bottom: 22px;">
        <h2 style="font-family:'Orbitron'; color:#00f2fe; margin-bottom:4px; font-size:24px;">🎙️ REAL-TIME NEURAL VOICE TRANSLATION</h2>
        <div style="color:#94a3b8; font-size:13px;">Capture live speech ➔ Neural STT ➔ Multilingual Translation ➔ ElevenLabs Voice Synthesis</div>
    </div>
    """, unsafe_allow_html=True)

    # ─── 1. LANGUAGE & VOICE SELECTION ───
    st.markdown("### 🌐 Step 1: Language & Voice Persona Configuration")
    col_s, col_t, col_v = st.columns(3)

    with col_s:
        input_lang_name = st.selectbox("1️⃣ Input Spoken Language:", list(LANGUAGES.keys()), index=0, key="vt_in_lang")
        input_lang_code = LANGUAGES[input_lang_name]["code"]
        input_speech_code = LANGUAGES[input_lang_name]["speech_code"]

    with col_t:
        output_lang_name = st.selectbox("2️⃣ Output Target Language:", list(LANGUAGES.keys()), index=1, key="vt_out_lang")
        output_lang_code = LANGUAGES[output_lang_name]["code"]

    with col_v:
        # Voice Persona options: User Cloned Voice + ElevenLabs Personas
        voice_options = []
        active_clone_id = st.session_state.get("active_cloned_voice_id")
        if active_clone_id:
            clone_name = st.session_state.get("cloned_voice_name", "My Cloned Voice")
            voice_options.append(f"🧬 {clone_name} (Active Clone)")

        voice_options.extend([
            "👩 Sarah (ElevenLabs Mature, Confident)",
            "👨 Charlie (ElevenLabs Deep, Confident)",
            "🧔 George (ElevenLabs Warm Storyteller)",
            "👱 Roger (ElevenLabs Laid-Back Resonant)",
            "👧 Laura (ElevenLabs Enthusiast)",
            "✨ Dynamic Clone (Use This Speaker Recording)"
        ])

        chosen_voice_persona = st.selectbox("3️⃣ Synthesis Voice:", voice_options, index=0, key="vt_persona_sel")

    # ─── 2. AUDIO INPUT SOURCE ───
    st.markdown("### 🎙️ Step 2: Speech Capture")
    input_method = st.radio("Choose Input Method:", ["🎙️ Live Microphone Recording", "📁 Upload Pre-Recorded Audio File"], horizontal=True, key="vt_input_method")

    os.makedirs("data/temp", exist_ok=True)
    vt_audio_path = "data/temp/vt_input.wav"

    if input_method == "🎙️ Live Microphone Recording":
        col_dur, col_info = st.columns([1.5, 3.5])
        with col_dur:
            record_dur = st.slider("Record Duration (seconds):", min_value=3, max_value=15, value=st.session_state.get("record_duration", 7), step=1, key="vt_dur_slider")
        with col_info:
            st.markdown(f"<div style='padding-top:28px; color:#cbd5e1; font-size:13px;'>💡 Speak in <b style='color:#00f2fe;'>{input_lang_name}</b>. Translation and speech synthesis happen automatically.</div>", unsafe_allow_html=True)

        if st.button("🔴 Record & Translate Live Speech", key="btn_rec_vt", type="primary"):
            st.markdown(f'<div style="text-align:center; color:#00f2fe; font-family:Orbitron; font-size:18px; padding:10px;">🔴 RECORDING LIVE ({record_dur}s)... SPEAK NOW</div>', unsafe_allow_html=True)
            sample_rate = 16000
            with st.spinner(f"Recording {record_dur}s from microphone..."):
                audio_data = sd.rec(int(record_dur * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
                sd.wait()
                sf.write(vt_audio_path, audio_data, sample_rate)
            st.session_state["vt_sample_ready"] = True
            st.session_state["vt_sample_path"] = vt_audio_path
            st.rerun()

    else:
        uploaded_vt = st.file_uploader("Upload Speech Audio File (.wav, .mp3, .m4a):", type=["wav", "mp3", "m4a"], key="vt_file_up")
        if uploaded_vt is not None:
            with open(vt_audio_path, "wb") as f_up:
                f_up.write(uploaded_vt.read())
            st.session_state["vt_sample_ready"] = True
            st.session_state["vt_sample_path"] = vt_audio_path
            st.success(f"File '{uploaded_vt.name}' uploaded!")

    # ─── 3. PROCESS SPEECH & TRANSLATE ───
    if st.session_state.get("vt_sample_ready") and os.path.exists(vt_audio_path):
        st.markdown("#### 🎧 Recorded Input Audio:")
        st.audio(vt_audio_path)

        if st.button("⚡ Execute Neural Translation & Voice Synthesis", key="btn_exec_vt_pipeline", type="primary"):
            with st.spinner("Recognizing Speech & Translating..."):
                try:
                    # 1. Speech Recognition
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(vt_audio_path) as source:
                        audio_content = recognizer.record(source)
                        recognized_text = recognizer.recognize_google(audio_content, language=input_speech_code)

                    # 2. Translation
                    if input_lang_name == output_lang_name:
                        translated_text = recognized_text
                    else:
                        translated_text = safe_translate(recognized_text, source_lang=input_lang_code, target_lang=output_lang_code)

                    st.session_state["vt_orig_text"] = recognized_text
                    st.session_state["vt_trans_text"] = translated_text

                    # 3. ElevenLabs Synthesis
                    with st.spinner(f"Synthesizing Translated Speech in {output_lang_name}..."):
                        # Determine voice mode
                        if "Active Clone" in chosen_voice_persona and active_clone_id:
                            # Use existing cloned voice
                            out_audio, status_msg = tts_engine.clone_voice(
                                text=translated_text,
                                voice_id=active_clone_id,
                                target_lang=output_lang_code
                            )
                        elif "Dynamic Clone" in chosen_voice_persona:
                            # Clone reference audio
                            out_audio, status_msg = tts_engine.clone_voice(
                                text=translated_text,
                                ref_audio_path_or_bytes=vt_audio_path,
                                target_lang=output_lang_code
                            )
                        else:
                            # ElevenLabs persona
                            out_audio, status_msg = tts_engine.synthesize_ai_voice(
                                text=translated_text,
                                target_lang=output_lang_code,
                                voice_profile=chosen_voice_persona
                            )

                        st.session_state["vt_out_audio"] = out_audio
                        st.session_state["vt_status_msg"] = status_msg
                        st.success("Voice Translation & Synthesis Complete!")

                except sr.UnknownValueError:
                    st.error("❌ Audio unclear or speech not recognized. Please speak closer to microphone.")
                except Exception as vt_err:
                    st.error(f"❌ Processing Error: {str(vt_err)}")

        # Display Cards if output is available
        if st.session_state.get("vt_orig_text") and st.session_state.get("vt_trans_text"):
            st.markdown("---")
            st.markdown(f"""
            <div class="glass-card-original">
                <div class="card-label orig">📝 RECOGNIZED SPEECH ({input_lang_name})</div>
                <div class="card-text">{st.session_state.get('vt_orig_text')}</div>
            </div>
            <div style="text-align:center; font-size:24px; color:#7000ff; margin: -5px 0;">⬇️</div>
            <div class="glass-card-translated">
                <div class="card-label trans">✨ TRANSLATED SPEECH ({output_lang_name})</div>
                <div class="card-text" style="color:#00f2fe; font-size:20px;">{st.session_state.get('vt_trans_text')}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("vt_out_audio"):
                st.markdown(f"### 🎧 Output Audio ({output_lang_name}):")
                st.markdown(f"<p style='color:#00f2fe; font-size:13px; font-style:italic;'>⚡ {st.session_state.get('vt_status_msg', '')}</p>", unsafe_allow_html=True)
                st.audio(st.session_state["vt_out_audio"], format="audio/mp3")

                st.download_button(
                    label=f"📥 Download Translated Speech (.mp3)",
                    data=st.session_state["vt_out_audio"],
                    file_name=f"translated_speech_{output_lang_code}.mp3",
                    mime="audio/mpeg",
                    key="btn_dl_vt_audio"
                )
