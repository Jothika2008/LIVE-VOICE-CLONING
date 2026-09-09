import streamlit as st

def render_user_guide_module():
    """
    📖 System User Guide
    Clean guide page explaining Text Translation, Voice Translation, Voice Cloning, Dual Interpreter, History, Registration, and Settings.
    """
    st.markdown("<div class='glow-title' style='font-size:30px;'>📖 USER GUIDE & SYSTEM MANUAL</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle-anim'>Step-by-Step Operating Guide for AI Translator Pro</div>", unsafe_allow_html=True)
    st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)

    # 1. TEXT TRANSLATION
    with st.expander("⌨️ 1. TEXT TRANSLATION", expanded=True):
        st.markdown("""
        <div style="background:rgba(8, 12, 26, 0.8); border:1px solid rgba(0, 220, 255, 0.25); border-radius:12px; padding:16px;">
            <h4 style="color:#00f2fe; font-family:'Orbitron'; margin-top:0;">Fast Multilingual Text Translation</h4>
            <ol style="color:#cbd5e1; line-height:1.8;">
                <li>Select source language (or Auto-Detect) and target language.</li>
                <li>Enter or paste text into the input prompt container.</li>
                <li>Click <code>Execute Neural Translation</code> to translate instantly.</li>
                <li>Preview synthesized TTS audio using the audio preview button.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    # 2. VOICE TRANSLATION
    with st.expander("🎙️ 2. VOICE TRANSLATION"):
        st.markdown("""
        <div style="background:rgba(8, 12, 26, 0.8); border:1px solid rgba(0, 220, 255, 0.25); border-radius:12px; padding:16px;">
            <h4 style="color:#00f2fe; font-family:'Orbitron'; margin-top:0;">Real-Time Microphone Speech Translation</h4>
            <ol style="color:#cbd5e1; line-height:1.8;">
                <li>Choose input and target output languages.</li>
                <li>Click <code>🔴 Start Recording</code> and speak into your microphone.</li>
                <li>System transcribes speech, translates text, and plays synthesized voice output automatically.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    # 3. VOICE CLONING
    with st.expander("🧬 3. VOICE CLONING"):
        st.markdown("""
        <div style="background:rgba(8, 12, 26, 0.8); border:1px solid rgba(0, 220, 255, 0.25); border-radius:12px; padding:16px;">
            <h4 style="color:#00f2fe; font-family:'Orbitron'; margin-top:0;">Zero-Shot Vocal Identity Preservation</h4>
            <ol style="color:#cbd5e1; line-height:1.8;">
                <li>Record a sample of your voice (or select reference profile).</li>
                <li>System extracts pitch and timbre acoustic embeddings.</li>
                <li>Synthesizes translated speech matching your authentic vocal identity.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    # 4. DUAL INTERPRETER
    with st.expander("💬 4. DUAL INTERPRETER"):
        st.markdown("""
        <div style="background:rgba(8, 12, 26, 0.8); border:1px solid rgba(0, 220, 255, 0.25); border-radius:12px; padding:16px;">
            <h4 style="color:#00f2fe; font-family:'Orbitron'; margin-top:0;">2-Way Real-Time Dialogue Conversation</h4>
            <ol style="color:#cbd5e1; line-height:1.8;">
                <li>Select mode at the top: <code>🎙️ Voice Mode</code> or <code>⌨️ Text Mode</code>.</li>
                <li>Configure <code>FROM</code> and <code>TO</code> languages.</li>
                <li>Messages are displayed in a clean messaging app chat feed: User on right, AI Translation on left with audio playback.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    # 5. HISTORY
    with st.expander("📜 5. HISTORY"):
        st.markdown("""
        <div style="background:rgba(8, 12, 26, 0.8); border:1px solid rgba(0, 220, 255, 0.25); border-radius:12px; padding:16px;">
            <h4 style="color:#00f2fe; font-family:'Orbitron'; margin-top:0;">Translation Log Archive</h4>
            <ol style="color:#cbd5e1; line-height:1.8;">
                <li>View all saved past translations with timestamps, language codes, source text, and translated text.</li>
                <li>Click audio player to re-listen to historical translations.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    # 6. REGISTRATION
    with st.expander("📧 6. REGISTRATION"):
        st.markdown("""
        <div style="background:rgba(8, 12, 26, 0.8); border:1px solid rgba(0, 220, 255, 0.25); border-radius:12px; padding:16px;">
            <h4 style="color:#00f2fe; font-family:'Orbitron'; margin-top:0;">Operator Profile Management</h4>
            <ol style="color:#cbd5e1; line-height:1.8;">
                <li>Register new email credentials or log in to access your personal workspace.</li>
                <li>User data is securely stored in local session state & user credentials database.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    # 7. SETTINGS
    with st.expander("⚙️ 7. SETTINGS"):
        st.markdown("""
        <div style="background:rgba(8, 12, 26, 0.8); border:1px solid rgba(0, 220, 255, 0.25); border-radius:12px; padding:16px;">
            <h4 style="color:#00f2fe; font-family:'Orbitron'; margin-top:0;">System Preferences & Duration Control</h4>
            <ol style="color:#cbd5e1; line-height:1.8;">
                <li>Adjust Microphone Recording Duration slider (3 to 15 seconds).</li>
                <li>Configure ElevenLabs API Key for neural voice cloning.</li>
                <li>Explore supported global language pairs.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
