"""
modules/voice_clone.py
═══════════════════════════════════════════════════════════════
Production ElevenLabs Neural Voice Cloning Studio & Voice Manager
Features:
- Instant Voice Cloning (IVC) via ElevenLabs REST API
- Biometric Acoustic Formant & Pitch Extraction
- Real-Time Multilingual Synthesis (17+ languages)
- Speech-to-Speech (STS) Voice Conversion
- Voice Library & Slot Quota Manager (Inspect, audition, delete slots)
- Voice Parameter Fine-Tuning (Stability, Similarity Boost, Style, Speaker Boost)
═══════════════════════════════════════════════════════════════
"""

import os
import time
import io
import soundfile as sf
import sounddevice as sd
import speech_recognition as sr
import librosa
import numpy as np
import streamlit as st
from core.elevenlabs_client import ElevenLabsClient
from core.tts_engine import TTSEngine
from core.translator import safe_translate

def render_voice_clone_module(LANGUAGES: dict):
    """
    Renders the Production ElevenLabs Voice Cloning Studio.
    """
    client = ElevenLabsClient(st.session_state.get("elevenlabs_api_key"))
    tts_engine = TTSEngine(api_key=st.session_state.get("elevenlabs_api_key"))

    sub_info = client.get_subscription_info()

    # ─── TOP STATUS HUD ───
    tier_label = sub_info.get("tier", "Starter")
    can_clone = sub_info.get("can_clone", True)
    slots_used = sub_info.get("voice_slots_used", 0)
    slots_limit = sub_info.get("voice_limit", 10)
    char_used = sub_info.get("char_used", 0)
    char_limit = sub_info.get("char_limit", 40000)

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(14, 23, 42, 0.95), rgba(8, 14, 30, 0.95)); border: 1px solid #00f2fe; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px; box-shadow: 0 0 25px rgba(0, 242, 254, 0.15);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <span style="font-family:'Orbitron'; color:#00f2fe; font-size:18px; font-weight:800; letter-spacing:1.5px;">🧬 ELEVENLABS NEURAL VOICE CLONING LAB</span>
                <div style="color:#94a3b8; font-size:13px; margin-top:3px;">Studio-Grade Instant Voice Cloning (IVC) · Speech-to-Speech · Voice Slot Management</div>
            </div>
            <div style="display:flex; gap:12px; align-items:center;">
                <span style="background:rgba(0, 242, 254, 0.15); border:1px solid #00f2fe; color:#00f2fe; font-family:'Orbitron'; font-size:11px; padding:6px 12px; border-radius:8px; font-weight:700;">
                    TIER: {tier_label.upper()}
                </span>
                <span style="background:rgba(112, 0, 255, 0.18); border:1px solid #7000ff; color:#c084fc; font-family:'Orbitron'; font-size:11px; padding:6px 12px; border-radius:8px; font-weight:700;">
                    SLOTS: {slots_used}/{slots_limit}
                </span>
                <span style="background:rgba(16, 185, 129, 0.18); border:1px solid #10b981; color:#34d399; font-family:'Orbitron'; font-size:11px; padding:6px 12px; border-radius:8px; font-weight:700;">
                    QUOTA: {char_limit - char_used:,} CHARS
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── STUDIO TABS ───
    tab_clone, tab_sts, tab_library = st.tabs([
        "🧬 1. Instant Voice Cloning Studio",
        "🎭 2. Speech-to-Speech (STS) Voice Changer",
        "📚 3. Voice Library & Slot Manager"
    ])

    # ═════════════════════════════════════════════════════════════════
    # TAB 1: INSTANT VOICE CLONING STUDIO
    # ═════════════════════════════════════════════════════════════════
    with tab_clone:
        st.markdown("### 🎙️ Step 1: Capture or Upload Speaker Audio")
        st.markdown("<p style='color:#94a3b8; font-size:13px;'>Provide 5 to 15 seconds of clean speaker audio for biometric timbre extraction.</p>", unsafe_allow_html=True)

        source_mode = st.radio("Voice Acquisition Method:", ["🎙️ Record Live Voice (Microphone)", "📁 Upload Audio File (.wav, .mp3, .m4a)"], horizontal=True, key="studio_acq_mode")

        os.makedirs("data/temp", exist_ok=True)
        ref_file_path = "data/temp/speaker_ref_audio.wav"

        if source_mode == "🎙️ Record Live Voice (Microphone)":
            col_d, col_info = st.columns([1.5, 3.5])
            with col_d:
                duration = st.slider("Record Duration (seconds):", min_value=4, max_value=15, value=7, step=1, key="studio_rec_dur")
            with col_info:
                st.markdown(f"<div style='padding-top:28px; color:#cbd5e1; font-size:13px;'>💡 Speak naturally into your microphone. Higher durations capture richer vocal formants.</div>", unsafe_allow_html=True)

            if st.button("🔴 Start Recording Microphone", key="btn_studio_rec", type="primary"):
                st.markdown(f'<div style="text-align:center; color:#00f2fe; font-family:Orbitron; font-size:18px; padding:10px;">🔴 RECORDING IN PROGRESS ({duration}s)... SPEAK NOW</div>', unsafe_allow_html=True)
                sample_rate = 16000
                with st.spinner(f"Recording {duration}s from microphone..."):
                    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
                    sd.wait()
                    sf.write(ref_file_path, audio_data, sample_rate)
                st.session_state["studio_sample_ready"] = True
                st.session_state["studio_sample_path"] = ref_file_path
                st.success("Audio sample captured successfully!")
                st.rerun()

        else:
            uploaded_voice = st.file_uploader("Upload Speaker Audio File:", type=["wav", "mp3", "m4a", "flac"], key="studio_up_file")
            if uploaded_voice is not None:
                with open(ref_file_path, "wb") as f_up:
                    f_up.write(uploaded_voice.read())
                st.session_state["studio_sample_ready"] = True
                st.session_state["studio_sample_path"] = ref_file_path
                st.success(f"Voice sample '{uploaded_voice.name}' uploaded successfully!")

        # If sample is ready, show audio player & acoustic badge
        if st.session_state.get("studio_sample_ready") and os.path.exists(ref_file_path):
            st.markdown("#### 🎧 Speaker Reference Sample:")
            st.audio(ref_file_path)

            # Extract biometrics
            try:
                y_user, sr_user = librosa.load(ref_file_path, sr=22050)
                user_f0, user_warmth = TTSEngine._extract_user_acoustics(y_user, sr_user)
            except Exception:
                user_f0, user_warmth = 175.0, 0.5

            gender = "Male (Baritone/Tenor)" if user_f0 < 165 else "Female (Soprano/Alto)"

            st.markdown(f"""
            <div style="background: rgba(112, 0, 255, 0.12); border: 1px solid #7000ff; border-radius: 10px; padding: 12px 18px; margin: 15px 0; display:flex; justify-content:space-around; text-align:center;">
                <div><span style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">ACOUSTIC REGISTER:</span><br><b style="color:#00f2fe;">{gender}</b></div>
                <div><span style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">FUNDAMENTAL PITCH (F0):</span><br><b style="color:#38bdf8;">{int(user_f0)} Hz</b></div>
                <div><span style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">FORMANT WARMTH:</span><br><b style="color:#c084fc;">{int(user_warmth*100)}%</b></div>
                <div><span style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">ENGINE:</span><br><b style="color:#34d399;">ElevenLabs IVC</b></div>
            </div>
            """, unsafe_allow_html=True)

            # Step 2: Register Voice Profile with ElevenLabs
            st.markdown("### 🧬 Step 2: Create & Save Voice Clone in ElevenLabs")
            col_vname, col_btn_create = st.columns([2.5, 1.5])
            with col_vname:
                default_name = f"MyVoice_{time.strftime('%b%d_%H%M')}"
                voice_name_input = st.text_input("Name Your Cloned Voice:", value=st.session_state.get("cloned_voice_name", default_name), key="input_clone_name")
            with col_btn_create:
                st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
                if st.button("⚡ Register Voice Clone with ElevenLabs", key="btn_register_ivc", use_container_width=True, type="primary"):
                    with st.spinner("Connecting to ElevenLabs IVC & Registering Voice Slot..."):
                        try:
                            res_add = client.add_instant_voice_clone(
                                name=voice_name_input.strip(),
                                audio_file_path=ref_file_path,
                                description=f"Live clone created from {gender} sample"
                            )
                            st.session_state["active_cloned_voice_id"] = res_add["voice_id"]
                            st.session_state["cloned_voice_name"] = voice_name_input.strip()
                            st.success(f"🎉 Voice '{voice_name_input}' successfully created! Voice ID: {res_add['voice_id']}")
                            st.rerun()
                        except Exception as ivc_err:
                            st.error(f"❌ Voice Cloning Failed: {str(ivc_err)}")

            active_id = st.session_state.get("active_cloned_voice_id")
            if active_id:
                st.markdown(f"""
                <div style="background: rgba(0, 242, 254, 0.12); border: 1px solid #00f2fe; border-radius: 10px; padding: 10px 16px; margin: 10px 0; color:#00f2fe; font-family:'Orbitron'; font-size:13px; font-weight:700;">
                    ✅ ACTIVE CLONED VOICE: <span style="color:#fff;">{st.session_state.get('cloned_voice_name', 'My Cloned Voice')}</span> · ID: <span style="color:#c084fc;">{active_id}</span>
                </div>
                """, unsafe_allow_html=True)

            # Step 3: Multilingual Voice Synthesis & Fine-Tuning
            st.markdown("### 🌐 Step 3: Multilingual Speech Synthesis in Your Voice")
            col_lang_in, col_lang_out = st.columns(2)
            with col_lang_in:
                input_lang_name = st.selectbox("Speech Input Language:", list(LANGUAGES.keys()), index=0, key="studio_in_lang")
            with col_lang_out:
                output_lang_name = st.selectbox("Output Synthesis Language:", list(LANGUAGES.keys()), index=1, key="studio_out_lang")

            out_lang_code = LANGUAGES[output_lang_name]["code"]

            # Content options
            content_mode = st.radio("Synthesis Text Source:", ["✍️ Type Custom Script to Speak in My Voice", "🗣️ Auto-Transcribe from My Audio Recording"], horizontal=True, key="studio_txt_src")

            custom_prompt = "Hello! This is an authentic neural voice clone synthesized in real time."
            if content_mode == "✍️ Type Custom Script to Speak in My Voice":
                script_text = st.text_area("Script to Synthesize:", value=custom_prompt, height=90, key="studio_script_input")
            else:
                # Transcribe from reference audio
                stt_text = ""
                try:
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(ref_file_path) as src:
                        aud = recognizer.record(src)
                        stt_text = recognizer.recognize_google(aud, language=LANGUAGES[input_lang_name]["speech_code"])
                except Exception:
                    stt_text = "Could not automatically transcribe speech. Please enter custom script."
                script_text = st.text_area("Transcribed Audio Script:", value=stt_text, height=90, key="studio_stt_input")

            # Fine-Tuning Sliders Expander
            with st.expander("🎛️ Advanced Voice Model & Fine-Tuning Sliders", expanded=False):
                col_tun1, col_tun2 = st.columns(2)
                with col_tun1:
                    stability = st.slider("Stability (Clarity vs Expressiveness):", min_value=0.0, max_value=1.0, value=0.50, step=0.05, help="Higher values make speech more stable and consistent; lower values make it more emotionally expressive.")
                    similarity = st.slider("Clarity / Similarity Boost:", min_value=0.0, max_value=1.0, value=0.75, step=0.05, help="Higher values adhere strictly to the original vocal timbre and acoustics.")
                with col_tun2:
                    style = st.slider("Style Exaggeration:", min_value=0.0, max_value=1.0, value=0.00, step=0.05, help="Exaggerates speaking style and emotional inflections.")
                    speaker_boost = st.checkbox("Enable Speaker Boost (Improves voice similarity)", value=True)
                    model_choice = st.selectbox("ElevenLabs Model:", ["eleven_multilingual_v2 (Highest Quality & All Languages)", "eleven_turbo_v2_5 (Lowest Latency)"], index=0)

                selected_model_id = "eleven_multilingual_v2" if "multilingual" in model_choice else "eleven_turbo_v2_5"

            auto_translate_prompt = st.checkbox(f"Auto-Translate Script into {output_lang_name} before speaking", value=True)

            if st.button("🚀 Synthesize Speech in My Cloned Voice", key="btn_exec_studio_synth", type="primary"):
                if not script_text.strip():
                    st.warning("Please provide script text to synthesize.")
                else:
                    target_voice_id = st.session_state.get("active_cloned_voice_id")
                    
                    with st.spinner("Synthesizing Authentic Cloned Voice with ElevenLabs Multilingual v2..."):
                        try:
                            # 1. Translate if requested
                            text_to_speak = script_text.strip()
                            if auto_translate_prompt and input_lang_name != output_lang_name:
                                text_to_speak = safe_translate(text_to_speak, source_lang='auto', target_lang=out_lang_code)

                            # 2. Synthesize
                            cloned_bytes, engine_msg = tts_engine.clone_voice(
                                text=text_to_speak,
                                ref_audio_path_or_bytes=ref_file_path if not target_voice_id else None,
                                voice_id=target_voice_id,
                                voice_name=voice_name_input.strip() if not target_voice_id else None,
                                stability=stability,
                                similarity_boost=similarity,
                                style=style,
                                use_speaker_boost=speaker_boost,
                                model_id=selected_model_id,
                                target_lang=out_lang_code
                            )

                            st.session_state["last_synth_bytes"] = cloned_bytes
                            st.session_state["last_synth_text"] = text_to_speak
                            st.session_state["last_synth_lang"] = output_lang_name
                            st.session_state["last_synth_status"] = engine_msg

                            st.success(f"Synthesized successfully into {output_lang_name}!")
                        except Exception as synth_err:
                            st.error(f"❌ Synthesis Error: {str(synth_err)}")

            if st.session_state.get("last_synth_bytes"):
                st.markdown("---")
                st.markdown("### 🎧 Synthesized Output in Cloned Voice:")
                st.markdown(f"<div style='background:rgba(14, 23, 42, 0.8); border:1px solid #00f2fe; border-radius:10px; padding:12px; margin-bottom:12px;'><b style='color:#00f2fe;'>Spoken Text ({st.session_state.get('last_synth_lang')}):</b> {st.session_state.get('last_synth_text')}</div>", unsafe_allow_html=True)
                st.audio(st.session_state["last_synth_bytes"], format="audio/mp3")

                st.download_button(
                    label=f"📥 Download Cloned Audio ({st.session_state.get('last_synth_lang')})",
                    data=st.session_state["last_synth_bytes"],
                    file_name=f"cloned_voice_{out_lang_code}.mp3",
                    mime="audio/mpeg",
                    key="btn_dl_synth_audio"
                )

    # ═════════════════════════════════════════════════════════════════
    # TAB 2: SPEECH-TO-SPEECH (STS) VOICE CHANGER
    # ═════════════════════════════════════════════════════════════════
    with tab_sts:
        st.markdown("### 🎭 Speech-to-Speech (STS) Neural Voice Morphing")
        st.markdown("<p style='color:#94a3b8; font-size:13px;'>Convert your speech directly into another person's voice or your cloned voice, preserving 100% of your authentic emotion, pause cadence, and inflection.</p>", unsafe_allow_html=True)

        all_voices = client.get_voices()
        voice_choices = {f"{v.get('name')} ({v.get('category','premade').title()})": v.get("voice_id") for v in all_voices}

        if not voice_choices:
            voice_choices = {"Sarah (Mature, Reassuring)": "EXAVITQu4vr4xnSDxMaL", "Charlie (Deep, Confident)": "IKne3meq5aSn9XLyUdCD"}

        col_stsv, col_stsm = st.columns(2)
        with col_stsv:
            selected_target_voice_name = st.selectbox("Target Voice Persona:", list(voice_choices.keys()), index=0, key="sts_voice_target")
            target_sts_voice_id = voice_choices[selected_target_voice_name]
        with col_stsm:
            sts_method = st.radio("STS Audio Input Source:", ["🎙️ Record Microphone", "📁 Upload Voice File"], horizontal=True, key="sts_src_mode")

        sts_file_path = "data/temp/sts_input.wav"
        sts_ready = False

        if sts_method == "🎙️ Record Microphone":
            sts_dur = st.slider("STS Recording Length (seconds):", min_value=3, max_value=12, value=5, step=1, key="sts_dur_slider")
            if st.button("🔴 Record for Voice Morphing", key="btn_rec_sts", type="primary"):
                with st.spinner(f"Recording {sts_dur}s..."):
                    sr_sts = 16000
                    sts_data = sd.rec(int(sts_dur * sr_sts), samplerate=sr_sts, channels=1, dtype='int16')
                    sd.wait()
                    sf.write(sts_file_path, sts_data, sr_sts)
                st.session_state["sts_sample_ready"] = True
                st.success("Input speech captured!")
                st.rerun()
        else:
            up_sts = st.file_uploader("Upload spoken audio to transform:", type=["wav", "mp3", "m4a"], key="sts_uploader")
            if up_sts is not None:
                with open(sts_file_path, "wb") as f_sts:
                    f_sts.write(up_sts.read())
                st.session_state["sts_sample_ready"] = True
                st.success(f"File '{up_sts.name}' uploaded!")

        if st.session_state.get("sts_sample_ready") and os.path.exists(sts_file_path):
            st.markdown("#### 🎧 Source Audio (Your Voice):")
            st.audio(sts_file_path)

            if st.button("⚡ Transform Speech into Target Voice", key="btn_exec_sts", type="primary"):
                with st.spinner("Morphing Voice Timbre via ElevenLabs Speech-to-Speech API..."):
                    try:
                        morphed_bytes, sts_msg = tts_engine.speech_to_speech_elevenlabs(
                            audio_file_path=sts_file_path,
                            voice_id=target_sts_voice_id
                        )
                        st.session_state["morphed_bytes"] = morphed_bytes
                        st.session_state["morphed_voice_name"] = selected_target_voice_name
                        st.success(f"🎉 Speech-to-Speech Transformation Complete!")
                    except Exception as sts_err:
                        st.error(f"❌ STS Error: {str(sts_err)}")

            if st.session_state.get("morphed_bytes"):
                st.markdown("#### 🎭 Morphed Output Speech (Target Voice):")
                st.audio(st.session_state["morphed_bytes"], format="audio/mp3")
                st.download_button(
                    label="📥 Download Morphed Audio (.mp3)",
                    data=st.session_state["morphed_bytes"],
                    file_name="speech_to_speech_morphed.mp3",
                    mime="audio/mpeg",
                    key="btn_dl_sts"
                )

    # ═════════════════════════════════════════════════════════════════
    # TAB 3: VOICE LIBRARY & SLOT MANAGER
    # ═════════════════════════════════════════════════════════════════
    with tab_library:
        st.markdown("### 📚 ElevenLabs Voice Library & Slot Manager")
        st.markdown("<p style='color:#94a3b8; font-size:13px;'>View custom cloned voices and standard library voices. Manage your 10 custom voice slots.</p>", unsafe_allow_html=True)

        if st.button("🔄 Refresh Voice Library", key="btn_refresh_lib"):
            st.rerun()

        all_v = client.get_voices()
        cloned_v = [v for v in all_v if v.get("category") in ["cloned", "generated"] or "custom" in v.get("category", "")]
        premade_v = [v for v in all_v if v not in cloned_v]

        st.markdown(f"#### 🧬 Custom Cloned Voices ({len(cloned_v)} / {slots_limit} Slots Used)")

        if not cloned_v:
            st.info("No custom cloned voices created yet. Use Tab 1 to clone your voice!")
        else:
            for cv in cloned_v:
                c_id = cv.get("voice_id")
                c_name = cv.get("name", "Unnamed Clone")
                c_desc = cv.get("description", "Custom Voice")

                st.markdown(f"""
                <div style="background:rgba(14, 23, 42, 0.85); border:1px solid #7000ff; border-radius:10px; padding:14px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <b style="color:#00f2fe; font-size:15px; font-family:'Orbitron';">{c_name}</b>
                        <div style="color:#94a3b8; font-size:12px; margin-top:2px;">ID: <code style="color:#c084fc;">{c_id}</code> · {c_desc}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_use, col_del = st.columns([3, 1])
                with col_use:
                    if st.button(f"👉 Set '{c_name}' as Active Cloned Voice", key=f"btn_set_{c_id}"):
                        st.session_state["active_cloned_voice_id"] = c_id
                        st.session_state["cloned_voice_name"] = c_name
                        st.success(f"Active Voice set to '{c_name}'!")
                        st.rerun()
                with col_del:
                    if st.button(f"🗑️ Delete Slot", key=f"btn_del_{c_id}"):
                        if client.delete_voice(c_id):
                            st.success(f"Voice slot '{c_name}' deleted!")
                            if st.session_state.get("active_cloned_voice_id") == c_id:
                                st.session_state["active_cloned_voice_id"] = None
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Could not delete voice slot.")

        st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)
        st.markdown(f"#### 🎭 Premade ElevenLabs Library Voices ({len(premade_v)} Voices Available)")

        cols = st.columns(3)
        for idx, pv in enumerate(premade_v[:12]):
            with cols[idx % 3]:
                p_name = pv.get("name", "Voice")
                p_id = pv.get("voice_id")
                labels = pv.get("labels", {})
                gender_lbl = labels.get("gender", "neutral").title()
                accent_lbl = labels.get("accent", "american").title()

                st.markdown(f"""
                <div style="background:rgba(8, 14, 30, 0.7); border:1px solid rgba(0, 242, 254, 0.2); border-radius:10px; padding:12px; margin-bottom:10px;">
                    <div style="color:#00f2fe; font-family:'Orbitron'; font-size:13px; font-weight:700;">{p_name}</div>
                    <div style="color:#94a3b8; font-size:11px; margin:4px 0;">{gender_lbl} · {accent_lbl}</div>
                    <code style="font-size:10px; color:#c084fc;">{p_id[:12]}...</code>
                </div>
                """, unsafe_allow_html=True)

                if pv.get("preview_url"):
                    st.audio(pv.get("preview_url"))
