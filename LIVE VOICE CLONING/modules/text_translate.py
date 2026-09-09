import streamlit as st
import datetime
from core.translator import TranslationEngine
from core.tts_engine import TTSEngine

def render_text_translate_module(tts_engine: TTSEngine, log_history_cb):
    """
    Module 2: Text Translation & Speech Synthesis (Visual Redesign)
    """
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.markdown('<h2 class="orbitron-text" style="color:#00f2fe; text-shadow:0 0 15px rgba(0,242,254,0.4);">⌨️ TEXT TRANSLATION</h2>', unsafe_allow_html=True)
    st.markdown('<div style="color:#94a3b8; font-size:14px; margin-bottom:15px;">Fast neural text translation engine & audio speech preview.</div>', unsafe_allow_html=True)

    languages = TranslationEngine.get_supported_languages()
    lang_names = list(languages.values())
    lang_codes = list(languages.keys())

    # Glass Card 1: Language Selectors
    st.markdown("""
    <div style="background:rgba(8, 12, 26, 0.85); border:1px solid rgba(0, 220, 255, 0.25); border-radius:14px; padding:16px 20px; margin-bottom:15px;">
        <div style="font-family:'Orbitron', sans-serif; font-size:12px; color:#00f2fe; letter-spacing:1.5px; font-weight:800; margin-bottom:10px;">🌐 LANGUAGE CONFIGURATION</div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        source_idx = st.selectbox("Input Language", ["Auto-Detect"] + lang_names, index=0)
        source_code = "auto" if source_idx == "Auto-Detect" else lang_codes[lang_names.index(source_idx)]

    with col2:
        target_idx = st.selectbox("Output Language", lang_names, index=1)
        target_code = lang_codes[lang_names.index(target_idx)]
    st.markdown('</div>', unsafe_allow_html=True)

    # Glass Card 2: Source Text Input
    st.markdown("""
    <div style="background:rgba(8, 12, 26, 0.85); border:1px solid rgba(0, 220, 255, 0.25); border-radius:14px; padding:16px 20px; margin-bottom:15px;">
        <div style="font-family:'Orbitron', sans-serif; font-size:12px; color:#00f2fe; letter-spacing:1.5px; font-weight:800; margin-bottom:8px;">📝 ENTER SOURCE TEXT</div>
    """, unsafe_allow_html=True)
    input_text = st.text_area("Source Text Prompt", placeholder="Type or paste anything here to translate...", height=120, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # Central Arrow Indicator
    st.markdown("""
    <div style="text-align:center; margin:15px 0;">
        <span style="font-family:'Orbitron', sans-serif; font-size:13px; font-weight:800; color:#00f2fe; letter-spacing:2px; background:rgba(0, 220, 255, 0.1); border:1px solid rgba(0, 220, 255, 0.3); padding:6px 18px; border-radius:20px;">
            ↓ NEURAL TRANSLATION ↓
        </span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 EXECUTE NEURAL TRANSLATION", type="primary"):
        if not input_text.strip():
            st.warning("Please provide input text.")
        else:
            with st.spinner("Translating text via safe neural fallback..."):
                translated_text = TranslationEngine.translate_text(
                    text=input_text,
                    target_lang=target_code,
                    source_lang=source_code
                )
                st.session_state["last_text_translation"] = {
                    "source_text": input_text,
                    "translated_text": translated_text,
                    "target_code": target_code,
                    "target_lang": target_idx
                }

    # Glass Card 3: Translated Output
    if "last_text_translation" in st.session_state:
        res = st.session_state["last_text_translation"]
        
        st.markdown(f"""
        <div class="glass-card-translated">
            <div class="card-label trans">✨ TRANSLATED TEXT ({res['target_lang'].upper()})</div>
            <div class="card-text">{res['translated_text']}</div>
        </div>
        """, unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 2])
        with col_a:
            if st.button("🔊 GENERATE AUDIO PREVIEW"):
                with st.spinner("Synthesizing speech..."):
                    audio_bytes = tts_engine.synthesize_standard(
                        text=res["translated_text"],
                        lang=res["target_code"]
                    )
                    st.session_state["text_audio_bytes"] = audio_bytes
                    
                    # Log to history
                    log_history_cb(
                        module="Text Translation",
                        source_text=res["source_text"],
                        translated_text=res["translated_text"],
                        target_lang=res["target_lang"],
                        has_audio=True
                    )

        with col_b:
            if "text_audio_bytes" in st.session_state and st.session_state["text_audio_bytes"]:
                st.audio(st.session_state["text_audio_bytes"], format="audio/mp3")

    st.markdown('</div>', unsafe_allow_html=True)
