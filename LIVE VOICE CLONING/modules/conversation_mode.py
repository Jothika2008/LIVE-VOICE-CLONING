"""
modules/conversation_mode.py
═══════════════════════════════════════════════════════════════
Dual Conversation Module — ChatGPT Request & Response UI
Clean linear conversational stream with prompt cards, AI responses,
inline TTS voice synthesis, live microphone input, and sleek dock.
═══════════════════════════════════════════════════════════════
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import time
import io
import html as _html
import os
from gtts import gTTS
from core.translator import safe_translate
from core.elevenlabs_client import ElevenLabsClient

# Optional audio recording imports
try:
    import sounddevice as sd
    import soundfile as sf
    import speech_recognition as sr
    HAS_AUDIO_INPUT = True
except ImportError:
    HAS_AUDIO_INPUT = False


# ─── Language Metadata ───────────────────────────────────────
LANG_FLAGS = {
    "English": "🇺🇸", "Tamil": "🇮🇳", "Hindi": "🇮🇳", "Telugu": "🇮🇳",
    "Kannada": "🇮🇳", "Malayalam": "🇮🇳", "Korean": "🇰🇷", "Chinese": "🇨🇳",
    "Urdu": "🇵🇰", "Bengali": "🇧🇩", "Arabic": "🇸🇦", "Punjabi": "🇮🇳",
    "French": "🇫🇷", "Spanish": "🇪🇸", "German": "🇩🇪", "Japanese": "🇯🇵",
    "Russian": "🇷🇺"
}

LANG_DISPLAY = {
    "English": "English",
    "Tamil": "Tamil (தமிழ்)",
    "Hindi": "Hindi (हिन्दी)",
    "Telugu": "Telugu (తెలుగు)",
    "Kannada": "Kannada (ಕನ್ನಡ)",
    "Malayalam": "Malayalam (മലയാളം)",
    "Korean": "Korean (한국어)",
    "Chinese": "Chinese (中文)",
    "Urdu": "Urdu (اردو)",
    "Bengali": "Bengali (বাংলা)",
    "Arabic": "Arabic (العربية)",
    "Punjabi": "Punjabi (ਪੰਜਾਬੀ)",
    "French": "French (Français)",
    "Spanish": "Spanish (Español)",
    "German": "German (Deutsch)",
    "Japanese": "Japanese (日本語)",
    "Russian": "Russian (Русский)"
}


# ════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════
def _esc(text):
    """HTML-escape text to prevent XSS / rendering issues."""
    if text is None:
        return ""
    return _html.escape(str(text))


def _clean_html(text: str) -> str:
    """Strip all leading and trailing whitespace per line to avoid CommonMark code block parsing."""
    if not text:
        return ""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _now_time():
    """Current time formatted as 'HH:MM AM/PM'."""
    return time.strftime("%I:%M %p")


def _gen_audio_b64(text, lang_code, sender="A"):
    """Generate high-fidelity ElevenLabs neural TTS audio bytes encoded as base64 string with gTTS fallback."""
    try:
        if not text or not str(text).strip():
            return ""
        
        key = st.session_state.get("elevenlabs_api_key")
        client = ElevenLabsClient(key)
        if client.is_configured():
            try:
                if sender == "A":
                    # If user has an active cloned voice, use it; otherwise Charlie (Male)
                    v_id = st.session_state.get("active_cloned_voice_id") or "IKne3meq5aSn9XLyUdCD"
                else:
                    # Speaker B uses Sarah (Female)
                    v_id = "EXAVITQu4vr4xnSDxMaL"

                audio_bytes = client.text_to_speech(text=str(text), voice_id=v_id)
                if audio_bytes and len(audio_bytes) > 500:
                    return base64.b64encode(audio_bytes).decode("utf-8")
            except Exception:
                pass

        # Fallback to gTTS
        tts = gTTS(text=str(text), lang=lang_code, slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return base64.b64encode(mp3_fp.read()).decode("utf-8")
    except Exception:
        return ""


def _send_from_speaker(sender, text, LANGUAGES):
    """
    Handles sending from a specific speaker ('A' or 'B').
    Translates text to the recipient's language, creates TTS audio,
    stores receipt in recipient's console, and logs to conversation history.
    """
    text = (text or "").strip()
    if not text:
        return False

    def _parse_lang(sel_val, fallback):
        if not sel_val:
            return fallback
        for k in LANGUAGES.keys():
            if k in str(sel_val):
                return k
        return fallback

    spkA_lang = _parse_lang(st.session_state.get("conv_sel_lang_a"), st.session_state.get("conv_spkA_lang", "English"))
    spkB_lang = _parse_lang(st.session_state.get("conv_sel_lang_b"), st.session_state.get("conv_spkB_lang", "Tamil"))

    if sender == "A":
        src_lang_name = spkA_lang
        tgt_lang_name = spkB_lang
        recipient_role = "B"
    else:
        src_lang_name = spkB_lang
        tgt_lang_name = spkA_lang
        recipient_role = "A"

    src_code = LANGUAGES.get(src_lang_name, {}).get("code", "en")
    tgt_code = LANGUAGES.get(tgt_lang_name, {}).get("code", "ta")

    # Translation
    if src_lang_name == tgt_lang_name:
        translated = text
    else:
        try:
            translated = safe_translate(text, source_lang=src_code, target_lang=tgt_code) or text
        except Exception:
            translated = text

    # TTS Synthesis
    audio_b64 = _gen_audio_b64(translated, tgt_code, sender=sender)

    st.session_state["conv_msg_counter"] = st.session_state.get("conv_msg_counter", 0) + 1
    msg_id = f"convmsg_{int(time.time()*1000)}_{st.session_state['conv_msg_counter']}"
    time_str = _now_time()

    msg = {
        "id": msg_id,
        "speaker": sender,
        "original": text,
        "translated": translated,
        "trans_lang_name": tgt_lang_name,
        "src_lang_name": src_lang_name,
        "src_code": src_code,
        "tgt_code": tgt_code,
        "time": time_str,
        "audio_b64": audio_b64 or ""
    }

    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    st.session_state["conversation_history"].append(msg)
    st.session_state["conversation_transcript"] = st.session_state["conversation_history"]

    # Delivery Receipt to the other speaker's console
    receipt = {
        "id": msg_id,
        "text": translated,
        "original": text,
        "from_speaker": f"Speaker {sender}",
        "src_lang": src_lang_name,
        "tgt_lang": tgt_lang_name,
        "audio_b64": audio_b64 or "",
        "time": time_str
    }

    if sender == "A":
        st.session_state["conv_last_for_b"] = receipt
        st.session_state["conv_active_speaker"] = "B"
    else:
        st.session_state["conv_last_for_a"] = receipt
        st.session_state["conv_active_speaker"] = "A"

    return True


def _render_received_banner(receipt, role_color):
    """Render the incoming translated message card inside a speaker's input console."""
    if not receipt:
        return ""
    rec_text = _esc(receipt.get("text", ""))
    orig_text = _esc(receipt.get("original", ""))
    from_spk = _esc(receipt.get("from_speaker", ""))
    tgt_lang = _esc(receipt.get("tgt_lang", ""))
    src_lang = _esc(receipt.get("src_lang", ""))
    flag_tgt = LANG_FLAGS.get(tgt_lang, "🌐")
    flag_src = LANG_FLAGS.get(src_lang, "🌐")
    audio_b64 = receipt.get("audio_b64", "")
    time_str = _esc(receipt.get("time", ""))
    msg_id = receipt.get("id", str(int(time.time()*1000)))

    audio_html = ""
    if audio_b64:
        audio_html = f"""<div class="gpt-audio-pill" style="margin-top:8px;">
<button class="gpt-play-btn" onclick="
var a=document.getElementById('aud_rx_{msg_id}');
var b=this;
if(a.paused){{ a.play(); b.innerHTML='⏸'; }}
else{{ a.pause(); a.currentTime=0; b.innerHTML='▶'; }}
a.onended=function(){{ b.innerHTML='▶'; }};
">▶</button>
<span class="gpt-audio-label">LISTEN IN {tgt_lang.upper()}</span>
<audio id="aud_rx_{msg_id}" src="data:audio/mp3;base64,{audio_b64}" preload="none"></audio>
</div>"""

    html = f"""<div class="gpt-rx-banner {role_color}">
<div class="gpt-rx-label">
<span>📩 MESSAGE RECEIVED FROM {from_spk.upper()}</span>
<span>{time_str}</span>
</div>
<div style="font-size:12px; color:#cbd5e1; margin-bottom:4px;">{from_spk} said ({flag_src} {src_lang}): <b style="color:#ffffff;">"{orig_text}"</b></div>
<div style="font-size:11px; color:#38bdf8; font-weight:700; margin-top:6px; margin-bottom:2px;">TRANSLATION FOR YOU ({flag_tgt} {tgt_lang}):</div>
<div class="gpt-rx-text">{rec_text}</div>
{audio_html}
</div>"""
    return _clean_html(html)


def _render_dual_message(msg):
    """
    Render a real human-to-human dual speaker message.
    Only renders the actual message sent by the speaker (Speaker A or Speaker B)
    with the translated text & voice playback for the opposite speaker.
    NO automated or fake AI responses are generated.
    """
    speaker = msg.get("speaker", "A")
    is_a = (speaker == "A")
    
    spk_color = "purple" if is_a else "cyan"
    spk_avatar = "🧑" if is_a else "👩"
    spk_name = f"Speaker {speaker}"
    align_class = "spk-a-row" if is_a else "spk-b-row"
    recipient_name = "Speaker B" if is_a else "Speaker A"

    src_lang = msg.get("src_lang_name", "English")
    tgt_lang = msg.get("trans_lang_name", "Tamil")
    src_flag = LANG_FLAGS.get(src_lang, "🌐")
    tgt_flag = LANG_FLAGS.get(tgt_lang, "🌐")

    msg_id = msg.get("id", "")
    original_text = _esc(msg.get("original", ""))
    translated_text = _esc(msg.get("translated", ""))
    time_str = _esc(msg.get("time", ""))
    audio_b64 = msg.get("audio_b64", "")

    # Audio Playback Block for translation
    audio_html = ""
    if audio_b64:
        bars_html = "".join([
            f'<div class="gpt-audio-bar" style="height:{h}px; animation-delay:{d}s;"></div>'
            for h, d in [(7, 0.0), (13, 0.1), (18, 0.2), (10, 0.3), (16, 0.4),
                         (20, 0.5), (11, 0.6), (15, 0.7), (8, 0.8), (14, 0.9)]
        ])
        audio_html = (
            f'<div class="gpt-audio-pill">'
            f'<button class="gpt-play-btn" onclick="'
            f'var a=document.getElementById(\'aud_{msg_id}\');'
            f'var b=this;'
            f'if(a.paused){{ a.play(); b.innerHTML=\'⏸\'; }}'
            f'else{{ a.pause(); a.currentTime=0; b.innerHTML=\'▶\'; }}'
            f'a.onended=function(){{ b.innerHTML=\'▶\'; }};'
            f'">▶</button>'
            f'<div class="gpt-wave-bars">{bars_html}</div>'
            f'<span class="gpt-audio-label">LISTEN IN {tgt_lang.upper()}</span>'
            f'<audio id="aud_{msg_id}" src="data:audio/mp3;base64,{audio_b64}" preload="none"></audio>'
            f'</div>'
        )

    escaped_for_js = translated_text.replace("'", "\\'").replace('"', '&quot;').replace('\n', ' ')

    turn_html = f"""<div class="dual-msg-wrapper {align_class}">
<div class="dual-msg-avatar {spk_color}">{spk_avatar}</div>
<div class="dual-msg-bubble {spk_color}">
<div class="dual-msg-header">
<span class="gpt-badge {spk_color}">{spk_avatar} {spk_name} ({src_flag} {src_lang})</span>
<span class="gpt-time">{time_str}</span>
</div>
<div class="dual-msg-original">{original_text}</div>
<div class="dual-msg-translation-box">
<div class="dual-msg-trans-header">
<span>🌐 Translated for {recipient_name} ({tgt_flag} {tgt_lang}):</span>
</div>
<div class="dual-msg-trans-text">{translated_text}</div>
</div>
<div class="gpt-action-bar" style="margin-top: 8px;">
{audio_html}
<button class="gpt-action-btn" title="Copy Translation" onclick="
navigator.clipboard.writeText('{escaped_for_js}');
var btn = this;
var old = btn.innerHTML;
btn.innerHTML = '✓ Copied';
btn.style.color = '#00f2fe';
setTimeout(function(){{ btn.innerHTML = old; btn.style.color = ''; }}, 2000);
">📋 Copy</button>
</div>
</div>
</div>"""
    return _clean_html(turn_html)


# ════════════════════════════════════════════════════════════
# CSS INJECTION — CHATGPT CLEAN DARK THEME
# ════════════════════════════════════════════════════════════
def _inject_css():
    st.markdown("""
    <style>
    /* ═══════════════ CHATGPT-STYLE DUAL CONVERSATION ═══════════════ */
    
    /* ─── Top Header Bar ─── */
    .gpt-header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 20px;
        background: rgba(18, 18, 28, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        backdrop-filter: blur(14px);
        margin-bottom: 18px;
    }
    .gpt-header-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .gpt-logo-orb {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #00f2fe, #7000ff);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
    }
    .gpt-header-text h2 {
        font-family: 'Poppins', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .gpt-header-text p {
        font-family: 'Poppins', sans-serif;
        font-size: 12px;
        color: #94a3b8;
        margin: 0;
    }
    .gpt-model-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(0, 242, 254, 0.1);
        border: 1px solid rgba(0, 242, 254, 0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-family: 'Orbitron', sans-serif;
        font-size: 11px;
        color: #00f2fe;
        font-weight: 600;
    }
    .gpt-pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #10b981;
        box-shadow: 0 0 8px #10b981;
        animation: pulseDot 1.6s infinite;
    }
    @keyframes pulseDot {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.3); opacity: 0.7; }
    }

    /* ─── Speaker Language Selector Cards ─── */
    .gpt-speakers-bar {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        gap: 12px;
        align-items: center;
        background: rgba(14, 15, 23, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 12px 16px;
        margin-bottom: 22px;
    }
    .gpt-speaker-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        background: rgba(25, 26, 38, 0.7);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .gpt-speaker-card.cyan { border-color: rgba(0, 242, 254, 0.3); }
    .gpt-speaker-card.purple { border-color: rgba(168, 85, 247, 0.3); }
    .gpt-spk-icon {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }
    .gpt-spk-icon.cyan { background: rgba(0, 242, 254, 0.15); border: 1px solid rgba(0, 242, 254, 0.4); }
    .gpt-spk-icon.purple { background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.4); }
    
    .gpt-spk-meta { flex: 1; }
    .gpt-spk-title {
        font-family: 'Poppins', sans-serif;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
    }
    .gpt-spk-title.cyan { color: #00f2fe; }
    .gpt-spk-title.purple { color: #c084fc; }
    .gpt-spk-desc {
        font-family: 'Poppins', sans-serif;
        font-size: 13px;
        color: #f1f5f9;
        font-weight: 600;
    }

    /* ─── Chat Thread Stream (ChatGPT Layout) ─── */
    .gpt-chat-stream {
        display: flex;
        flex-direction: column;
        gap: 24px;
        max-width: 900px;
        margin: 0 auto 20px auto;
    }
    .gpt-turn-container {
        display: flex;
        flex-direction: column;
        gap: 14px;
        animation: turnSlide 0.3s ease-out;
    }
    @keyframes turnSlide {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ─── Request Bubble (User Prompt on Right) ─── */
    .gpt-request-row {
        display: flex;
        justify-content: flex-end;
        align-items: flex-start;
        gap: 12px;
        padding-left: 60px;
    }
    .gpt-request-bubble {
        max-width: 82%;
        background: #272838;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 18px 4px 18px 18px;
        padding: 14px 18px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    }
    .gpt-request-bubble.purple {
        border-color: rgba(168, 85, 247, 0.35);
        background: linear-gradient(135deg, #2a1b38, #231d2e);
    }
    .gpt-request-bubble.cyan {
        border-color: rgba(0, 242, 254, 0.35);
        background: linear-gradient(135deg, #13243a, #1b2636);
    }
    .gpt-request-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    .gpt-badge {
        font-family: 'Poppins', sans-serif;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 10px;
    }
    .gpt-badge.purple { background: rgba(168, 85, 247, 0.25); color: #d8b4fe; }
    .gpt-badge.cyan { background: rgba(0, 242, 254, 0.25); color: #67e8f9; }
    .gpt-lang-pill {
        font-family: 'Poppins', sans-serif;
        font-size: 11px;
        color: #94a3b8;
        background: rgba(0, 0, 0, 0.3);
        padding: 2px 8px;
        border-radius: 10px;
    }
    .gpt-time {
        font-size: 11px;
        color: #64748b;
        margin-left: auto;
    }
    .gpt-request-text {
        font-family: 'Poppins', sans-serif;
        font-size: 15px;
        color: #ffffff;
        line-height: 1.55;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
    .gpt-user-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.4);
    }
    .gpt-user-avatar.purple { background: #6b21a8; border: 1px solid #c084fc; }
    .gpt-user-avatar.cyan { background: #0e7490; border: 1px solid #22d3ee; }

    /* ─── Response Block (AI Output on Left / Full Width) ─── */
    .gpt-response-row {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        padding-right: 40px;
    }
    .gpt-ai-avatar {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: linear-gradient(135deg, #10b981, #0284c7);
        box-shadow: 0 0 14px rgba(16, 185, 129, 0.45);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
    }
    .gpt-ai-avatar.cyan {
        background: linear-gradient(135deg, #06b6d4, #0284c7);
        box-shadow: 0 0 14px rgba(6, 182, 212, 0.45);
        border: 1px solid #22d3ee;
    }
    .gpt-ai-avatar.purple {
        background: linear-gradient(135deg, #a855f7, #7c3aed);
        box-shadow: 0 0 14px rgba(168, 85, 247, 0.45);
        border: 1px solid #c084fc;
    }
    .gpt-response-card {
        flex: 1;
        background: rgba(20, 21, 31, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 4px 18px 18px 18px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(16px);
    }
    .gpt-response-card.cyan {
        border-color: rgba(0, 242, 254, 0.35);
        background: linear-gradient(135deg, #101c2c, #162232);
    }
    .gpt-response-card.purple {
        border-color: rgba(168, 85, 247, 0.35);
        background: linear-gradient(135deg, #22152e, #201a2c);
    }
    .gpt-response-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
    }
    .gpt-ai-meta {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .gpt-ai-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
    }
    .gpt-ai-title.cyan { color: #00f2fe; }
    .gpt-ai-title.purple { color: #c084fc; }
    .gpt-route-tag {
        font-family: 'Poppins', sans-serif;
        font-size: 11px;
        background: rgba(255, 255, 255, 0.06);
        color: #cbd5e1;
        padding: 2px 10px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .gpt-response-text {
        font-family: 'Poppins', sans-serif;
        font-size: 17px;
        font-weight: 500;
        color: #f8fafc;
        line-height: 1.6;
        margin-bottom: 14px;
        word-wrap: break-word;
        white-space: pre-wrap;
    }

    /* ─── ChatGPT Action Toolbar ─── */
    .gpt-action-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        padding-top: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    .gpt-audio-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(0, 242, 254, 0.1);
        border: 1px solid rgba(0, 242, 254, 0.35);
        border-radius: 20px;
        padding: 4px 12px 4px 6px;
    }
    .gpt-play-btn {
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #00f2fe;
        border: none;
        color: #05070d;
        font-size: 11px;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: transform 0.2s;
    }
    .gpt-play-btn:hover { transform: scale(1.1); background: #38bdf8; }
    .gpt-wave-bars {
        display: flex;
        align-items: center;
        gap: 2px;
        height: 18px;
    }
    .gpt-audio-bar {
        width: 3px;
        background: #00f2fe;
        border-radius: 2px;
        animation: gptWave 1.2s ease-in-out infinite;
    }
    @keyframes gptWave {
        0%, 100% { transform: scaleY(0.4); opacity: 0.5; }
        50% { transform: scaleY(1); opacity: 1; }
    }
    .gpt-audio-label {
        font-family: 'Orbitron', sans-serif;
        font-size: 9px;
        font-weight: 700;
        color: #00f2fe;
        letter-spacing: 1px;
    }

    .gpt-action-btn {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #94a3b8;
        border-radius: 8px;
        padding: 5px 12px;
        font-size: 12px;
        font-family: 'Poppins', sans-serif;
        cursor: pointer;
        transition: all 0.2s;
    }
    .gpt-action-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
        border-color: rgba(255, 255, 255, 0.25);
    }
    .gpt-model-tag {
        font-family: 'Orbitron', sans-serif;
        font-size: 9px;
        color: #64748b;
        letter-spacing: 1px;
        margin-left: auto;
    }

    /* ─── Dual Speaker Consoles ─── */
    .gpt-console-card {
        background: rgba(18, 20, 32, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 18px 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(16px);
        margin-bottom: 24px;
        transition: border-color 0.3s, box-shadow 0.3s;
    }
    .gpt-console-card.purple {
        border-color: rgba(168, 85, 247, 0.35);
        background: linear-gradient(135deg, rgba(28, 20, 42, 0.9), rgba(18, 20, 32, 0.85));
    }
    .gpt-console-card.cyan {
        border-color: rgba(0, 242, 254, 0.35);
        background: linear-gradient(135deg, rgba(14, 28, 42, 0.9), rgba(18, 20, 32, 0.85));
    }
    .gpt-console-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .gpt-console-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: 'Poppins', sans-serif;
        font-size: 15px;
        font-weight: 700;
    }
    .gpt-console-title.purple { color: #d8b4fe; }
    .gpt-console-title.cyan { color: #67e8f9; }
    
    .gpt-turn-badge {
        font-family: 'Orbitron', sans-serif;
        font-size: 10px;
        padding: 3px 10px;
        border-radius: 20px;
        font-weight: 700;
        letter-spacing: 1px;
    }
    .gpt-turn-badge.active {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.4);
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }
    .gpt-turn-badge.waiting {
        background: rgba(255, 255, 255, 0.05);
        color: #64748b;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .gpt-rx-banner {
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 14px;
        backdrop-filter: blur(12px);
    }
    .gpt-rx-banner.purple {
        background: rgba(168, 85, 247, 0.12);
        border: 1px solid rgba(168, 85, 247, 0.35);
        box-shadow: 0 0 16px rgba(168, 85, 247, 0.15);
    }
    .gpt-rx-banner.cyan {
        background: rgba(0, 242, 254, 0.12);
        border: 1px solid rgba(0, 242, 254, 0.35);
        box-shadow: 0 0 16px rgba(0, 242, 254, 0.15);
    }
    .gpt-rx-label {
        font-family: 'Poppins', sans-serif;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #94a3b8;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    .gpt-rx-text {
        font-family: 'Poppins', sans-serif;
        font-size: 16px;
        font-weight: 600;
        color: #ffffff;
        line-height: 1.5;
        margin-bottom: 4px;
        word-wrap: break-word;
    }
    .gpt-rx-orig {
        font-size: 12px;
        color: #94a3b8;
        font-style: italic;
    }

    /* ─── Dual Human Message Bubbles ─── */
    .dual-msg-wrapper {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 20px;
        width: 100%;
    }
    .dual-msg-wrapper.spk-a-row {
        flex-direction: row;
        justify-content: flex-start;
    }
    .dual-msg-wrapper.spk-b-row {
        flex-direction: row-reverse;
        justify-content: flex-start;
    }
    .dual-msg-avatar {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
    }
    .dual-msg-avatar.purple {
        background: linear-gradient(135deg, #7c3aed, #a855f7);
        border: 1px solid #c084fc;
    }
    .dual-msg-avatar.cyan {
        background: linear-gradient(135deg, #0284c7, #06b6d4);
        border: 1px solid #22d3ee;
    }
    .dual-msg-bubble {
        max-width: 78%;
        border-radius: 18px;
        padding: 16px 18px;
        backdrop-filter: blur(16px);
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35);
    }
    .dual-msg-bubble.purple {
        background: linear-gradient(135deg, rgba(35, 22, 54, 0.92), rgba(22, 20, 36, 0.88));
        border: 1px solid rgba(168, 85, 247, 0.35);
        border-top-left-radius: 4px;
    }
    .dual-msg-bubble.cyan {
        background: linear-gradient(135deg, rgba(14, 32, 50, 0.92), rgba(18, 24, 38, 0.88));
        border: 1px solid rgba(0, 242, 254, 0.35);
        border-top-right-radius: 4px;
    }
    .dual-msg-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
        gap: 12px;
    }
    .dual-msg-original {
        font-family: 'Poppins', sans-serif;
        font-size: 16px;
        font-weight: 500;
        color: #ffffff;
        line-height: 1.5;
        margin-bottom: 10px;
        word-wrap: break-word;
    }
    .dual-msg-translation-box {
        background: rgba(0, 0, 0, 0.32);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 4px;
    }
    .dual-msg-trans-header {
        font-family: 'Poppins', sans-serif;
        font-size: 11px;
        font-weight: 600;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .dual-msg-trans-text {
        font-family: 'Poppins', sans-serif;
        font-size: 15px;
        font-weight: 600;
        color: #f1f5f9;
        line-height: 1.45;
        word-wrap: break-word;
    }

    /* ─── Empty State (ChatGPT Look) ─── */
    .gpt-empty-container {
        text-align: center;
        padding: 50px 20px 30px 20px;
        max-width: 680px;
        margin: 0 auto;
    }
    .gpt-empty-orb {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(0, 242, 254, 0.35), rgba(112, 0, 255, 0.15));
        border: 1px solid rgba(0, 242, 254, 0.5);
        box-shadow: 0 0 30px rgba(0, 242, 254, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 34px;
        margin: 0 auto 16px auto;
    }
    .gpt-empty-title {
        font-family: 'Poppins', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
    }
    .gpt-empty-subtitle {
        font-family: 'Poppins', sans-serif;
        font-size: 14px;
        color: #94a3b8;
        margin-bottom: 24px;
    }

    /* ─── ChatGPT Bottom Floating Dock ─── */
    .gpt-dock-spacer { height: 160px; }
    
    .gpt-dock-wrapper {
        position: fixed !important;
        bottom: 16px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: min(880px, 92vw) !important;
        z-index: 9999 !important;
        background: rgba(18, 19, 28, 0.95) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 24px !important;
        padding: 12px 16px !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6), 0 0 30px rgba(0, 242, 254, 0.15) !important;
    }

    /* Active Speaker Toggle Bar inside Dock */
    .gpt-speaker-switch {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
    }
    .gpt-speaker-switch [data-testid="stButton"] > button {
        border-radius: 20px !important;
        padding: 6px 14px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        font-family: 'Poppins', sans-serif !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(255, 255, 255, 0.05) !important;
        color: #94a3b8 !important;
        transition: all 0.2s !important;
    }
    .gpt-spk-a-active button {
        background: rgba(168, 85, 247, 0.2) !important;
        border-color: #a855f7 !important;
        color: #d8b4fe !important;
        box-shadow: 0 0 12px rgba(168, 85, 247, 0.3) !important;
    }
    .gpt-spk-b-active button {
        background: rgba(0, 242, 254, 0.2) !important;
        border-color: #00f2fe !important;
        color: #67e8f9 !important;
        box-shadow: 0 0 12px rgba(0, 242, 254, 0.3) !important;
    }

    /* ChatGPT Capsule Input Row */
    .gpt-input-row [data-testid="stTextInput"] input {
        background: rgba(28, 29, 42, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 18px !important;
        color: #ffffff !important;
        font-family: 'Poppins', sans-serif !important;
        padding: 14px 20px !important;
        font-size: 14px !important;
    }
    .gpt-input-row [data-testid="stTextInput"] input:focus {
        border-color: #00f2fe !important;
        box-shadow: 0 0 0 2px rgba(0, 242, 254, 0.25) !important;
    }
    .gpt-btn-circle button {
        width: 46px !important;
        height: 46px !important;
        border-radius: 50% !important;
        font-size: 18px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #cbd5e1 !important;
        transition: all 0.2s !important;
    }
    .gpt-btn-circle button:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: #00f2fe !important;
        color: #00f2fe !important;
        transform: scale(1.08) !important;
    }
    .gpt-send-btn button {
        background: linear-gradient(135deg, #00f2fe, #7000ff) !important;
        border: none !important;
        color: #05070d !important;
        box-shadow: 0 0 16px rgba(0, 242, 254, 0.4) !important;
    }
    .gpt-send-btn button:hover {
        transform: scale(1.1) !important;
        box-shadow: 0 0 22px rgba(0, 242, 254, 0.7) !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ════════════════════════════════════════════════════════════
def render_conversation_mode_module(LANGUAGES):
    """Main render function for the ChatGPT-styled Dual Conversation Module."""

    # ─── State Management ───
    if st.session_state.get("_conv_do_swap"):
        old_a = st.session_state.get("conv_sel_lang_a")
        old_b = st.session_state.get("conv_sel_lang_b")
        st.session_state["conv_sel_lang_a"] = old_b
        st.session_state["conv_sel_lang_b"] = old_a
        del st.session_state["_conv_do_swap"]

    if st.session_state.get("_conv_clear_input"):
        st.session_state["conv_msg_input"] = ""
        del st.session_state["_conv_clear_input"]

    if st.session_state.get("_conv_insert_prompt"):
        st.session_state["conv_msg_input"] = st.session_state["_conv_insert_prompt"]
        del st.session_state["_conv_insert_prompt"]

    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    if "conv_spkA_lang" not in st.session_state:
        st.session_state["conv_spkA_lang"] = "English"
    if "conv_spkB_lang" not in st.session_state:
        st.session_state["conv_spkB_lang"] = "Tamil"
    if "conv_active_speaker" not in st.session_state:
        st.session_state["conv_active_speaker"] = "A"
    if "conv_mode" not in st.session_state:
        st.session_state["conv_mode"] = "Text"
    if "conv_msg_counter" not in st.session_state:
        st.session_state["conv_msg_counter"] = 0

    # ─── Build Language Options ───
    lang_keys = list(LANGUAGES.keys())
    lang_options = [f"{LANG_FLAGS.get(l, '🌐')} {LANG_DISPLAY.get(l, l)}" for l in lang_keys]

    if "conv_sel_lang_a" not in st.session_state:
        a_name = st.session_state.get("conv_spkA_lang", "English")
        a_idx = lang_keys.index(a_name) if a_name in lang_keys else 0
        st.session_state["conv_sel_lang_a"] = lang_options[a_idx]

    if "conv_sel_lang_b" not in st.session_state:
        b_name = st.session_state.get("conv_spkB_lang", "Tamil")
        b_idx = lang_keys.index(b_name) if b_name in lang_keys else (1 if len(lang_keys) > 1 else 0)
        st.session_state["conv_sel_lang_b"] = lang_options[b_idx]

    _inject_css()

    # ════════════════════════════════════════════════════════
    # 1. TOP ACTION BAR
    # ════════════════════════════════════════════════════════
    col_spacer, col_dash_btn, col_btn = st.columns([5.5, 1.8, 1.5])
    with col_dash_btn:
        if st.button("🏠 Dashboard", key="conv_back_dash", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.session_state["nav_menu"] = "🏠 Dashboard"
            st.rerun()
    with col_btn:
        if st.button("🗑️ Delete Chat", key="conv_clear_chat", use_container_width=True, help="Delete all chat history"):
            st.session_state["conversation_history"] = []
            st.session_state["conversation_transcript"] = []
            st.session_state["conv_last_for_a"] = None
            st.session_state["conv_last_for_b"] = None
            st.toast("Chat history deleted", icon="🗑️")
            st.rerun()

    # ════════════════════════════════════════════════════════
    # 2. SPEAKER & LANGUAGE SELECTOR BAR
    # ════════════════════════════════════════════════════════
    spk_a_col, swap_col, spk_b_col = st.columns([2.5, 0.6, 2.5])

    with spk_a_col:
        a_val = st.session_state.get("conv_sel_lang_a", lang_options[0])
        a_idx = lang_options.index(a_val) if a_val in lang_options else 0
        a_name = lang_keys[a_idx]
        a_flag = LANG_FLAGS.get(a_name, "🌐")
        a_disp = LANG_DISPLAY.get(a_name, a_name)

        st.markdown(f"""
        <div class="gpt-speaker-card purple">
            <div class="gpt-spk-icon purple">🧑</div>
            <div class="gpt-spk-meta">
                <div class="gpt-spk-title purple">Speaker A (Primary)</div>
                <div class="gpt-spk-desc">{a_flag} {a_disp}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        sel_a = st.selectbox("Speaker A Language", lang_options, index=a_idx,
                             key="conv_sel_lang_a", label_visibility="collapsed")
        for k in lang_keys:
            if k in str(sel_a):
                st.session_state["conv_spkA_lang"] = k

    with swap_col:
        st.markdown("<div style='text-align:center; padding-top: 18px;'>", unsafe_allow_html=True)
        if st.button("🔄", key="conv_swap_lang_btn", help="Swap Speaker Languages"):
            st.session_state["_conv_do_swap"] = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with spk_b_col:
        b_val = st.session_state.get("conv_sel_lang_b", lang_options[1] if len(lang_options) > 1 else lang_options[0])
        b_idx = lang_options.index(b_val) if b_val in lang_options else 0
        b_name = lang_keys[b_idx]
        b_flag = LANG_FLAGS.get(b_name, "🌐")
        b_disp = LANG_DISPLAY.get(b_name, b_name)

        st.markdown(f"""
        <div class="gpt-speaker-card cyan">
            <div class="gpt-spk-icon cyan">👩</div>
            <div class="gpt-spk-meta">
                <div class="gpt-spk-title cyan">Speaker B (Partner)</div>
                <div class="gpt-spk-desc">{b_flag} {b_disp}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        sel_b = st.selectbox("Speaker B Language", lang_options, index=b_idx,
                             key="conv_sel_lang_b", label_visibility="collapsed")
        for k in lang_keys:
            if k in str(sel_b):
                st.session_state["conv_spkB_lang"] = k

    # Clear Inputs Handlers
    if st.session_state.get("_clear_input_a"):
        st.session_state["input_spk_a"] = ""
        del st.session_state["_clear_input_a"]

    if st.session_state.get("_clear_input_b"):
        st.session_state["input_spk_b"] = ""
        del st.session_state["_clear_input_b"]

    # ════════════════════════════════════════════════════════
    # 3. DUAL SPEAKER CONSOLES (Turn-Taking: Speaker A ➔ Speaker B)
    # ════════════════════════════════════════════════════════
    spkA_lang_active = st.session_state.get("conv_spkA_lang", "English")
    spkB_lang_active = st.session_state.get("conv_spkB_lang", "Tamil")
    flag_a = LANG_FLAGS.get(spkA_lang_active, "🌐")
    flag_b = LANG_FLAGS.get(spkB_lang_active, "🌐")

    active_spk = st.session_state.get("conv_active_speaker", "A")
    is_turn_a = (active_spk == "A")
    is_turn_b = (active_spk == "B")

    # Status indicator banner
    if is_turn_a:
        st.markdown(f"""
        <div style="background: rgba(168,85,247,0.12); border: 1px solid rgba(168,85,247,0.35); border-radius: 12px; padding: 10px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div style="font-family:'Poppins',sans-serif; font-size:13px; color:#d8b4fe; font-weight:600;">
                🟢 <b>Speaker A's Turn:</b> Type or speak a message in {spkA_lang_active}. Speaker B will receive the translation.
            </div>
            <span style="font-family:'Orbitron',sans-serif; font-size:10px; background:#7c3aed; color:#fff; padding:3px 8px; border-radius:12px;">SPEAKER A ACTIVE</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: rgba(6,182,212,0.12); border: 1px solid rgba(6,182,212,0.35); border-radius: 12px; padding: 10px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div style="font-family:'Poppins',sans-serif; font-size:13px; color:#67e8f9; font-weight:600;">
                🟢 <b>Waiting for Speaker B:</b> Speaker B received Speaker A's message. Waiting for Speaker B's input response...
            </div>
            <span style="font-family:'Orbitron',sans-serif; font-size:10px; background:#0891b2; color:#fff; padding:3px 8px; border-radius:12px;">WAITING FOR SPEAKER B</span>
        </div>
        """, unsafe_allow_html=True)

    c_spk_a, c_spk_b = st.columns(2)

    # ───────────────── 🧑 SPEAKER A CONSOLE ─────────────────
    with c_spk_a:
        cls_card_a = "active-turn" if is_turn_a else ""
        badge_cls_a = "active" if is_turn_a else "waiting"
        badge_txt_a = "● YOUR TURN TO SEND" if is_turn_a else "⏳ WAITING FOR SPEAKER B"

        st.markdown(f"""
        <div class="gpt-console-card purple {cls_card_a}">
            <div class="gpt-console-header">
                <div class="gpt-console-title purple">
                    <span style="font-size: 22px;">🧑</span>
                    <span>Speaker A Console ({flag_a} {spkA_lang_active})</span>
                </div>
                <span class="gpt-turn-badge {badge_cls_a}">{badge_txt_a}</span>
            </div>
        """, unsafe_allow_html=True)

        # Incoming message received from Speaker B (if any)
        last_for_a = st.session_state.get("conv_last_for_a")
        if last_for_a:
            st.markdown(_render_received_banner(last_for_a, "purple"), unsafe_allow_html=True)

        ph_a = f"Type message in {spkA_lang_active} for Speaker B..." if is_turn_a else "⏳ Message delivered to Speaker B. Waiting for Speaker B's response..."
        txt_a = st.text_input(
            "Speaker A Input",
            placeholder=ph_a,
            key="input_spk_a",
            disabled=not is_turn_a,
            label_visibility="collapsed"
        )

        col_send_a, col_mic_a = st.columns([4, 1])
        with col_send_a:
            btn_send_a = st.button("🚀 Send to Speaker B ➔", key="btn_send_a", use_container_width=True,
                                   type="primary" if is_turn_a else "secondary", disabled=not is_turn_a)
        with col_mic_a:
            btn_mic_a = st.button("🎙️", key="btn_mic_a", help=f"Speak as Speaker A ({spkA_lang_active})", disabled=not is_turn_a)

        st.markdown("</div>", unsafe_allow_html=True)

    # ───────────────── 👩 SPEAKER B CONSOLE ─────────────────
    with c_spk_b:
        cls_card_b = "active-turn" if is_turn_b else ""
        badge_cls_b = "active" if is_turn_b else "waiting"
        badge_txt_b = "● YOUR TURN TO RESPOND" if is_turn_b else "⏳ WAITING FOR SPEAKER A"

        st.markdown(f"""
        <div class="gpt-console-card cyan {cls_card_b}">
            <div class="gpt-console-header">
                <div class="gpt-console-title cyan">
                    <span style="font-size: 22px;">👩</span>
                    <span>Speaker B Console ({flag_b} {spkB_lang_active})</span>
                </div>
                <span class="gpt-turn-badge {badge_cls_b}">{badge_txt_b}</span>
            </div>
        """, unsafe_allow_html=True)

        # Incoming message received from Speaker A
        last_for_b = st.session_state.get("conv_last_for_b")
        if last_for_b:
            st.markdown(_render_received_banner(last_for_b, "cyan"), unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align:center; padding: 26px 16px; color: #94a3b8; font-size: 13px;">
                <div style="font-size: 28px; margin-bottom: 6px;">📡</div>
                <div style="font-weight:600; color:#cbd5e1;">Waiting for Speaker A to send a message...</div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Incoming messages with audio playback will appear here.</div>
            </div>
            """, unsafe_allow_html=True)

        ph_b = f"Type your response in {spkB_lang_active} for Speaker A..." if is_turn_b else "⏳ Waiting for Speaker A to send a message..."
        txt_b = st.text_input(
            "Speaker B Input",
            placeholder=ph_b,
            key="input_spk_b",
            disabled=not is_turn_b,
            label_visibility="collapsed"
        )

        col_send_b, col_mic_b = st.columns([4, 1])
        with col_send_b:
            btn_send_b = st.button("🚀 Send Response to Speaker A ➔", key="btn_send_b", use_container_width=True,
                                   type="primary" if is_turn_b else "secondary", disabled=not is_turn_b)
        with col_mic_b:
            btn_mic_b = st.button("🎙️", key="btn_mic_b", help=f"Speak as Speaker B ({spkB_lang_active})", disabled=not is_turn_b)

        st.markdown("</div>", unsafe_allow_html=True)

    # Helper recording function
    def _record_and_transcribe(lang_name):
        if not HAS_AUDIO_INPUT:
            return ""
        try:
            duration = 5
            sample_rate = 16000
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            wav_io = io.BytesIO()
            sf.write(wav_io, audio_data, sample_rate, format='WAV')
            wav_io.seek(0)
            
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio_content = recognizer.record(source)
                speech_code = LANGUAGES.get(lang_name, {}).get("speech_code", "en-US")
                return recognizer.recognize_google(audio_content, language=speech_code)
        except Exception as e:
            st.toast(f"Speech recognition: {e}", icon="⚠️")
            return ""

    # Console Action Handlers
    if btn_send_a:
        val_a = st.session_state.get("input_spk_a", "").strip()
        if val_a:
            _send_from_speaker("A", val_a, LANGUAGES)
            st.session_state["_clear_input_a"] = True
            st.rerun()
        else:
            st.toast("⚠️ Speaker A message is empty", icon="⚠️")

    if btn_mic_a:
        if HAS_AUDIO_INPUT:
            with st.spinner(f"🎙️ Listening to Speaker A ({spkA_lang_active})... Speak now!"):
                rec_text_a = _record_and_transcribe(spkA_lang_active)
                if rec_text_a.strip():
                    _send_from_speaker("A", rec_text_a.strip(), LANGUAGES)
                    st.rerun()
                else:
                    st.warning("No speech detected. Try speaking closer to the mic.")
        else:
            st.toast("Microphone input packages not available.", icon="🎙️")

    if btn_send_b:
        val_b = st.session_state.get("input_spk_b", "").strip()
        if val_b:
            _send_from_speaker("B", val_b, LANGUAGES)
            st.session_state["_clear_input_b"] = True
            st.rerun()
        else:
            st.toast("⚠️ Speaker B message is empty", icon="⚠️")

    if btn_mic_b:
        if HAS_AUDIO_INPUT:
            with st.spinner(f"🎙️ Listening to Speaker B ({spkB_lang_active})... Speak now!"):
                rec_text_b = _record_and_transcribe(spkB_lang_active)
                if rec_text_b.strip():
                    _send_from_speaker("B", rec_text_b.strip(), LANGUAGES)
                    st.rerun()
                else:
                    st.warning("No speech detected. Try speaking closer to the mic.")
        else:
            st.toast("Microphone input packages not available.", icon="🎙️")

    # ════════════════════════════════════════════════════════
    # 4. CONVERSATION STREAM
    # ════════════════════════════════════════════════════════
    history = st.session_state.get("conversation_history", [])

    # Auto-repair any historical turns that had offline translation
    for turn in history:
        trans = turn.get("translated", "")
        if "[Translation Offline]" in trans:
            raw_orig = turn.get("original", "")
            src_c = LANGUAGES.get(turn.get("src_lang_name", "English"), {}).get("code", "en")
            tgt_c = LANGUAGES.get(turn.get("trans_lang_name", "Tamil"), {}).get("code", "ta")
            try:
                new_trans = safe_translate(raw_orig, source_lang=src_c, target_lang=tgt_c)
                if new_trans and "[Translation Offline]" not in new_trans:
                    turn["translated"] = new_trans
                    turn["audio_b64"] = _gen_audio_b64(new_trans, tgt_c, sender=turn.get("sender", "A"))
            except Exception:
                pass

    if not history:
        st.markdown("""
        <div style="text-align:center; margin: 24px 0 16px 0;">
            <span style="font-family:'Orbitron',sans-serif; font-size:11px; letter-spacing:2px; color:#94a3b8; background:rgba(255,255,255,0.06); padding:6px 18px; border-radius:20px; border:1px solid rgba(255,255,255,0.1);">
                📜 LIVE CONVERSATION (Speaker A ➔ Speaker B)
            </span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="gpt-empty-container">
            <div class="gpt-empty-orb">✨</div>
            <div class="gpt-empty-title">Conversation Ready</div>
            <div class="gpt-empty-subtitle">
                Speaker A sends a message ➔ Speaker B receives the translated speech with voice playback!
            </div>
        </div>
        """, unsafe_allow_html=True)

        sug1, sug2, sug3 = st.columns(3)
        with sug1:
            if st.button("👋 'Hello! How are you doing today?'", key="sug_btn_1", use_container_width=True):
                st.session_state["input_spk_a"] = "Hello! How are you doing today?"
                st.session_state["conv_active_speaker"] = "A"
                st.rerun()
        with sug2:
            if st.button("💼 'Can we schedule a quick sync meeting?'", key="sug_btn_2", use_container_width=True):
                st.session_state["input_spk_a"] = "Can we schedule a quick sync meeting?"
                st.session_state["conv_active_speaker"] = "A"
                st.rerun()
        with sug3:
            if st.button("🌍 'I am excited to collaborate across borders!'", key="sug_btn_3", use_container_width=True):
                st.session_state["input_spk_a"] = "I am excited to collaborate across borders!"
                st.session_state["conv_active_speaker"] = "A"
                st.rerun()

    else:
        col_hdr_l, col_hdr_r1, col_hdr_r2 = st.columns([3.5, 1.2, 1.6])
        with col_hdr_l:
            st.markdown(f"""
            <div style="margin: 18px 0 10px 0;">
                <span style="font-family:'Orbitron',sans-serif; font-size:11px; letter-spacing:2px; color:#94a3b8; background:rgba(255,255,255,0.06); padding:6px 18px; border-radius:20px; border:1px solid rgba(255,255,255,0.1);">
                    📜 LIVE CONVERSATION ({len(history)} Messages)
                </span>
            </div>
            """, unsafe_allow_html=True)
        with col_hdr_r1:
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            if st.button("↩️ Delete Last", key="btn_del_last_chat", use_container_width=True, help="Remove only the most recent message"):
                if st.session_state.get("conversation_history"):
                    st.session_state["conversation_history"].pop()
                    st.session_state["conversation_transcript"] = st.session_state["conversation_history"]
                    st.toast("Last message removed", icon="↩️")
                    st.rerun()
        with col_hdr_r2:
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Delete Chat History", key="btn_del_chat_history_stream", use_container_width=True, help="Clear all messages from this chat session"):
                st.session_state["conversation_history"] = []
                st.session_state["conversation_transcript"] = []
                st.session_state["conv_last_for_a"] = None
                st.session_state["conv_last_for_b"] = None
                st.toast("Chat history deleted", icon="🗑️")
                st.rerun()

        stream_html = ['<div class="gpt-chat-stream">']
        for turn in history:
            stream_html.append(_render_dual_message(turn))
        stream_html.append('</div>')
        st.markdown(_clean_html("".join(stream_html)), unsafe_allow_html=True)


def render_conversation_mode(LANGUAGES=None):
    if LANGUAGES is None:
        LANGUAGES = {
            "English": {"code": "en", "speech_code": "en-US"},
            "Tamil": {"code": "ta", "speech_code": "ta-IN"}
        }
    render_conversation_mode_module(LANGUAGES)


if __name__ == "__main__":
    render_conversation_mode()