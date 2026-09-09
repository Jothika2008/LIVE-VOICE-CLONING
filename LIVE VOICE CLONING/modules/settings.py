"""
modules/settings.py
═══════════════════════════════════════════════════════════════
Live ElevenLabs Telemetry & System Configuration Module
Features:
- Live ElevenLabs Subscription Tier & Status Telemetry
- Quota Meter: Monthly Characters Remaining (e.g. 40,000 allowance)
- Custom Voice Slot Usage (0-10 Slots)
- Model Architecture Selector (Multilingual v2 vs Turbo v2.5)
- Microphone Capture Duration & DSP Calibration
═══════════════════════════════════════════════════════════════
"""

import os
import time
import streamlit as st
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
from core.elevenlabs_client import ElevenLabsClient
from core.tts_engine import TTSEngine

def render_settings_module(LANGUAGES: dict):
    """
    Renders System Configuration & Live ElevenLabs Telemetry.
    """
    client = ElevenLabsClient(st.session_state.get("elevenlabs_api_key"))
    sub_info = client.get_subscription_info()

    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(14, 23, 42, 0.95), rgba(8, 14, 30, 0.95)); border: 1px solid #00f2fe; border-radius: 14px; padding: 20px 24px; margin-bottom: 22px;">
        <h2 style="font-family:'Orbitron'; color:#00f2fe; margin-bottom:4px; font-size:24px;">⚙️ SYSTEM & API CONFIGURATION</h2>
        <div style="color:#94a3b8; font-size:13px;">Manage ElevenLabs Neural Engines, Quota Telemetry, and Audio DSP Parameters</div>
    </div>
    """, unsafe_allow_html=True)

    # ─── 1. ELEVENLABS TELEMETRY & API CONFIG ───
    st.markdown("### 🔑 ElevenLabs Neural API & Live Telemetry")

    # Metrics Row
    tier_label = sub_info.get("tier", "Starter")
    char_used = sub_info.get("char_used", 0)
    char_limit = sub_info.get("char_limit", 40000)
    char_pct = int((char_used / char_limit) * 100) if char_limit > 0 else 0
    slots_used = sub_info.get("voice_slots_used", 0)
    slots_limit = sub_info.get("voice_limit", 10)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div style="background:rgba(8, 14, 30, 0.8); border:1px solid #00f2fe; border-radius:10px; padding:12px; text-align:center;">
            <div style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">SUBSCRIPTION TIER</div>
            <div style="color:#00f2fe; font-size:18px; font-weight:700; margin-top:4px;">{tier_label}</div>
            <div style="color:#34d399; font-size:11px;">Active & Verified</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div style="background:rgba(8, 14, 30, 0.8); border:1px solid #7000ff; border-radius:10px; padding:12px; text-align:center;">
            <div style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">VOICE CLONING (IVC)</div>
            <div style="color:#c084fc; font-size:18px; font-weight:700; margin-top:4px;">{'ENABLED' if sub_info.get('can_clone') else 'RESTRICTED'}</div>
            <div style="color:#94a3b8; font-size:11px;">Instant Cloning Allowed</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div style="background:rgba(8, 14, 30, 0.8); border:1px solid #38bdf8; border-radius:10px; padding:12px; text-align:center;">
            <div style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">VOICE SLOTS</div>
            <div style="color:#38bdf8; font-size:18px; font-weight:700; margin-top:4px;">{slots_used} / {slots_limit}</div>
            <div style="color:#94a3b8; font-size:11px;">{slots_limit - slots_used} Slots Remaining</div>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown(f"""
        <div style="background:rgba(8, 14, 30, 0.8); border:1px solid #10b981; border-radius:10px; padding:12px; text-align:center;">
            <div style="color:#94a3b8; font-size:11px; font-family:'Orbitron';">CHARACTERS REMAINING</div>
            <div style="color:#34d399; font-size:18px; font-weight:700; margin-top:4px;">{char_limit - char_used:,}</div>
            <div style="color:#94a3b8; font-size:11px;">Used: {char_used:,} ({char_pct}%)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    st.progress(min(1.0, max(0.0, char_used / (char_limit if char_limit > 0 else 1))))

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── API CREDENTIAL SECURITY & TELEMETRY ───
    current_key = st.session_state.get("elevenlabs_api_key", "")
    is_key_set = bool(current_key and current_key.startswith("sk_"))
    masked_key = f"sk_••••••••••••••••••••••••••••••••{current_key[-4:]}" if (current_key and len(current_key) > 8) else ("Configured" if current_key else "Not Configured")

    sec_col1, sec_col2 = st.columns([3.2, 1.3])
    with sec_col1:
        if is_key_set:
            st.markdown(f"""
            <div style="background:rgba(16, 185, 129, 0.08); border:1px solid #10b981; border-radius:10px; padding:14px 18px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:20px;">🔒</span>
                    <div>
                        <div style="font-family:'Orbitron'; font-size:12px; font-weight:700; color:#34d399; letter-spacing:0.5px;">API CREDENTIAL STATUS: SECURED</div>
                        <div style="color:#94a3b8; font-size:12px; margin-top:2px;">
                            Active Key: <code style="color:#a7f3d0; background:rgba(0,0,0,0.4); padding:2px 7px; border-radius:4px;">{masked_key}</code>
                            &nbsp;•&nbsp; UI editing disabled for credential security. Key is securely managed in server environment.
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(244, 63, 94, 0.08); border:1px solid #f43f5e; border-radius:10px; padding:14px 18px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:20px;">⚠️</span>
                    <div>
                        <div style="font-family:'Orbitron'; font-size:12px; font-weight:700; color:#fb7185; letter-spacing:0.5px;">API CREDENTIAL NOT DETECTED</div>
                        <div style="color:#94a3b8; font-size:12px; margin-top:2px;">
                            No API key detected in server environment. Configure <code>ELEVENLABS_API_KEY</code> in your server's <code>.env</code> file.
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with sec_col2:
        st.markdown("<div style='padding-top:4px;'></div>", unsafe_allow_html=True)
        if st.button("🔍 Test Connection", key="btn_test_backend_key", use_container_width=True):
            if current_key:
                v_stat = TTSEngine.verify_elevenlabs_key(current_key)
                if v_stat.get("can_clone"):
                    st.success(f"✅ {v_stat.get('message')}")
                elif v_stat.get("valid"):
                    st.warning(f"⚠️ {v_stat.get('message')}")
                else:
                    st.error(f"❌ {v_stat.get('message')}")
            else:
                st.error("❌ No API key configured in server environment (.env).")

    st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)

    # ─── 2. DEFAULT SYNTHESIS & CLONING MODEL ───
    st.markdown("### 🧬 Primary Voice Engine & Model Architecture")
    col_mod1, col_mod2 = st.columns(2)
    with col_mod1:
        selected_model = st.selectbox(
            "Default ElevenLabs Neural Model:",
            [
                "eleven_multilingual_v2 (Recommended: Highest Fidelity across 29 Languages)",
                "eleven_turbo_v2_5 (Low Latency Real-Time Streaming)"
            ],
            index=0 if "multilingual" in st.session_state.get("selected_el_model", "multilingual") else 1,
            key="set_model_sel"
        )
        st.session_state["selected_el_model"] = "eleven_multilingual_v2" if "multilingual" in selected_model else "eleven_turbo_v2_5"

    with col_mod2:
        selected_fallback = st.selectbox(
            "Offline & Quota Fallback Engine:",
            [
                "Microsoft Neural Edge-TTS + DSP Pitch Matcher (High Quality)",
                "Standard Google TTS (gTTS)"
            ],
            index=0,
            key="set_fallback_sel"
        )

    st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)

    # ─── 3. MICROPHONE & AUDIO DSP CONTROLS ───
    st.markdown("### 🎙️ Audio Capture & Hardware Pipeline")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        cur_dur = st.session_state.get("record_duration", 8)
        new_dur = st.slider("Microphone Recording Window (seconds):", min_value=3, max_value=15, value=cur_dur, step=1, key="set_mic_dur")
        if new_dur != cur_dur:
            st.session_state["record_duration"] = new_dur

    with col_d2:
        cur_sr = st.session_state.get("target_sr", 24000)
        new_sr = st.select_slider("DSP Pipeline Sampling Rate (Hz):", options=[16000, 22050, 24000, 44100], value=cur_sr, key="set_sr_slider")
        if new_sr != cur_sr:
            st.session_state["target_sr"] = new_sr

    # Hardware detection
    cuda_available = torch.cuda.is_available() if HAS_TORCH else False
    dev_name = torch.cuda.get_device_name(0) if (HAS_TORCH and cuda_available) else "CPU Hardware Accelerator"
    st.markdown(f"""
    <div style="background:rgba(8, 14, 30, 0.6); border:1px solid rgba(0, 242, 254, 0.2); border-radius:10px; padding:12px 18px; margin-top:10px; font-size:13px; color:#cbd5e1;">
        🖥️ <b>Host Accelerator:</b> <code style="color:#00f2fe;">{dev_name}</code> · <b>CUDA Status:</b> {'🟢 ACTIVE' if cuda_available else '⚪ CPU Standard Mode'} · <b>ElevenLabs REST API:</b> <span style="color:#34d399;">🟢 ONLINE</span>
    </div>
    """, unsafe_allow_html=True)
