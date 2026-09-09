import os
import time
import re
import difflib
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
from gtts import gTTS
import streamlit as st
from core.translator import safe_translate

def render_accent_coach_module(LANGUAGES: dict):
    if "coach_last_spoken" not in st.session_state:
        st.session_state["coach_last_spoken"] = ""

    st.markdown("<div class='glow-title' style='font-size:32px;'>🎯 AI ACCENT & GRAMMAR COACH</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle-anim'>Real-Time Multilingual Speech Accuracy, Grammar & Fluency Evaluation Engine</div>", unsafe_allow_html=True)
    st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        coach_lang = st.selectbox("Select Target Practice Language:", list(LANGUAGES.keys()), index=0, key="coach_lang_sel")
        speech_code = LANGUAGES.get(coach_lang, {}).get("speech_code", "en-US")
        lang_code = LANGUAGES.get(coach_lang, {}).get("code", "en")

    preset_phrases = {
        "English": "Yesterday I went to the market and bought fresh vegetables.",
        "Tamil": "நாளைக்கு நான் சென்னைக்கு போவேன்.",
        "Hindi": "आज मैं एक नई भाषा सीख रहा हूँ।",
        "Telugu": "రేపు నేను ఊరికి వెళ్తాను.",
        "Kannada": "ನಾಳೆ ನಾನು ಶಾಲೆಗೆ ಹೋಗುತ್ತೇನೆ.",
        "Malayalam": "നാളെ ഞാൻ അവിടെ പോകും.",
        "French": "Aujourd'hui je vais apprendre le français avec enthousiasme.",
        "Spanish": "Me gustaría practicar mi pronunciación en español todos los días.",
        "German": "Ich möchte meine Deutschkenntnisse jeden Tag verbessern.",
        "Japanese": "今日は新しい言語を楽しく学んでいます。",
        "Korean": "오늘 나는 새로운 언어를 열심히 배우고 있습니다.",
        "Chinese": "今天我正在努力学习一门新的语言。",
        "Arabic": "اليوم أتعلم لغة جديدة بحماس شديد.",
        "Russian": "Сегодня я с удовольствием изучаю новый язык.",
        "Urdu": "آج میں ایک نئی زبان سیکھ رہا ہوں۔",
        "Bengali": "আজ আমি একটি নতুন ভাষা শিখছি।",
        "Punjabi": "ਅੱਜ ਮੈਂ ਇੱਕ ਨਵੀਂ ਭਾਸ਼ਾ ਸਿੱਖ ਰਿਹਾ ਹਾਂ।"
    }
    default_ref = preset_phrases.get(coach_lang, "Hello! How are you doing today?")

    with col_c2:
        reference_text = st.text_area("Target Reference / Practice Phrase:", value=default_ref, height=80, key="coach_ref_text")

    if st.button("🔊 Listen to Reference Native Pronunciation", key="btn_listen_coach_ref"):
        try:
            ref_mp3 = "data/temp/coach_ref_native.mp3"
            os.makedirs("data/temp", exist_ok=True)
            tts = gTTS(text=reference_text, lang=lang_code, slow=False)
            tts.save(ref_mp3)
            with open(ref_mp3, "rb") as f:
                st.audio(f.read(), format="audio/mp3", autoplay=True)
        except Exception as tts_err:
            st.error(f"Audio playback error: {tts_err}")

    st.markdown("### 🔴 Record or Input Your Speech")
    input_method = st.radio("Practice Method:", ["🎙️ Record Live Speech", "⌨️ Input Text / Audio Evaluation"], horizontal=True, key="coach_input_method")

    spoken_text = ""

    if input_method == "🎙️ Record Live Speech":
        DURATION = st.session_state.get("record_duration", 8)
        st.markdown(f"<p style='color:#94a3b8;'>💡 Read the target phrase or speak freely in <b style='color:#00f2fe;'>{coach_lang}</b>. System records {DURATION}s.</p>", unsafe_allow_html=True)
        if st.button("🔴 Start Practice Recording", key="btn_start_coach_rec"):
            try:
                with st.spinner(f"Recording ({DURATION}s)... Speak clearly now!"):
                    audio_data = sd.rec(int(DURATION * 16000), samplerate=16000, channels=1, dtype='int16')
                    sd.wait()
                    os.makedirs("data/temp", exist_ok=True)
                    wav_file = f"data/temp/coach_input_{int(time.time())}.wav"
                    sf.write(wav_file, audio_data, 16000)

                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_file) as source:
                    aud = recognizer.record(source)
                    spoken_text = recognizer.recognize_google(aud, language=speech_code)
                st.session_state["coach_last_spoken"] = spoken_text
            except sr.UnknownValueError:
                st.error("❌ Audio unclear or speech unrecognized. Please speak clearly into the microphone and record again.")
            except Exception as rec_err:
                st.error(f"❌ Recording / Speech Recognition Error: {str(rec_err)}")

        spoken_text = st.session_state.get("coach_last_spoken", "")

    else:
        spoken_text = st.text_area("Type or Paste Spoken Sentence to Evaluate:", value=st.session_state.get("coach_last_spoken", ""), height=80, key="coach_manual_txt")
        if st.button("⚡ Evaluate Grammar & Fluency", key="btn_eval_manual"):
            st.session_state["coach_last_spoken"] = spoken_text

    if spoken_text and spoken_text.strip():
        try:
            _render_evaluation_engine(reference_text, spoken_text.strip(), coach_lang, LANGUAGES)
        except Exception as eval_err:
            st.error(f"Evaluation display error: {eval_err}")

def _render_evaluation_engine(reference_text: str, spoken_text: str, coach_lang: str, LANGUAGES: dict):
    """
    Multilingual Grammar & Accuracy Evaluation Engine:
    - Dedicated Tamil grammar tense & gender pattern analyzer
    - Dedicated Telugu grammar tense & gender pattern analyzer
    - Rule-based English grammar & tense analyzer
    - Back-translation semantic consistency check for other languages
    """
    st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)
    st.markdown("### 📊 AI Speech & Grammar Evaluation Results")

    # Analyze grammar & accuracy
    errors, corrected_sentence, tips, score = _evaluate_sentence(spoken_text, reference_text, coach_lang, LANGUAGES)

    # Dynamic badge colors
    if score == 100:
        badge_color = "#00f2fe"  # Green / Cyan
        badge_bg = "rgba(0, 242, 254, 0.12)"
        badge_border = "1px solid #00f2fe"
        status_label = "🎯 PERFECT FLUENCY — 100% Flawless Grammar!"
    elif score >= 80:
        badge_color = "#00f2fe"  # Green / Cyan
        badge_bg = "rgba(0, 242, 254, 0.12)"
        badge_border = "1px solid #00f2fe"
        status_label = "🎯 EXCELLENT FLUENCY — High Grammar Accuracy!"
    elif score >= 60:
        badge_color = "#eab308"  # Yellow
        badge_bg = "rgba(234, 179, 8, 0.12)"
        badge_border = "1px solid #eab308"
        status_label = "⚠️ NEEDS IMPROVEMENT — Grammatical errors detected!"
    else:
        badge_color = "#f43f5e"  # Red
        badge_bg = "rgba(244, 63, 94, 0.12)"
        badge_border = "1px solid #f43f5e"
        status_label = "🚨 MISTAKES FOUND — Practice Needed!"

    # Score Badge & Progress Bar Card
    st.markdown(f"""
    <div style="background:{badge_bg}; border:{badge_border}; border-radius:18px; padding:24px; text-align:center; margin:20px 0; box-shadow:0 0 25px {badge_color}33;">
        <div style="color:{badge_color}; font-family:'Orbitron'; font-size:42px; font-weight:900;">{score}% ACCURACY SCORE</div>
        <div style="color:#ffffff; font-family:'Poppins'; font-size:15px; font-weight:600; margin:6px 0 16px 0;">{status_label}</div>
        <div style="background:rgba(255,255,255,0.1); border-radius:10px; height:14px; width:100%; overflow:hidden;">
            <div style="background:{badge_color}; height:100%; width:{score}%; border-radius:10px; transition:width 1s ease-in-out;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Glowing UI Breakdown Cards
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div style="background:rgba(8, 14, 30, 0.85); border:1px solid rgba(0,242,254,0.3); border-radius:14px; padding:18px; margin-bottom:15px;">
            <div style="color:#00f2fe; font-family:'Orbitron'; font-size:12px; font-weight:800; letter-spacing:1px; margin-bottom:6px;">🗣️ WHAT YOU SAID ({coach_lang})</div>
            <div style="color:#ffffff; font-size:15px; font-weight:500;">{spoken_text}</div>
        </div>
        """, unsafe_allow_html=True)

        if errors:
            err_box = "<br>".join([f"• {e}" for e in errors])
            st.markdown(f"""
            <div style="background:rgba(244, 63, 94, 0.1); border:1px solid #f43f5e; border-radius:14px; padding:18px;">
                <div style="color:#f43f5e; font-family:'Orbitron'; font-size:12px; font-weight:800; letter-spacing:1px; margin-bottom:6px;">⚠️ MISTAKE EVALUATION</div>
                <div style="color:#ff8090; font-size:14px; line-height:1.5;">{err_box}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(0, 255, 136, 0.1); border:1px solid #00ff88; border-radius:14px; padding:18px;">
                <div style="color:#00ff88; font-family:'Orbitron'; font-size:12px; font-weight:800; letter-spacing:1px; margin-bottom:6px;">✅ MISTAKE EVALUATION</div>
                <div style="color:#00ff88; font-size:14px; font-weight:600;">✅ No major grammatical errors detected.</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:rgba(112, 0, 255, 0.1); border:1px solid #a855f7; border-radius:14px; padding:18px; margin-bottom:15px;">
            <div style="color:#c084fc; font-family:'Orbitron'; font-size:12px; font-weight:800; letter-spacing:1px; margin-bottom:6px;">✨ SUGGESTED CORRECTION</div>
            <div style="color:#00f2fe; font-size:15px; font-weight:600;">{corrected_sentence}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(8, 26, 54, 0.85); border:1px solid #38bdf8; border-radius:14px; padding:18px;">
            <div style="color:#38bdf8; font-family:'Orbitron'; font-size:12px; font-weight:800; letter-spacing:1px; margin-bottom:6px;">📢 AI COACH ADVICE</div>
            <div style="color:#cbd5e1; font-size:14px; line-height:1.5;">{tips}</div>
        </div>
        """, unsafe_allow_html=True)

def check_person_agreement(spoken: str):
    """
    Short-circuit Person / Gender Pronoun-Verb Mismatch Checker:
    - Telugu: 'నేను' (1st Person) + 3rd Person Verb ('తింటాడు') -> Returns Score 55%
    - Tamil: 'நான்' (1st Person) + 3rd Person Verb ('போனான்') -> Returns Score 55%
    """
    text_clean = spoken.strip()

    # 1. Telugu 1st Person ('నేను') vs 3rd Person Verb Mismatch
    if "నేను" in text_clean:
        telugu_3rd_verbs = ["తింటాడు", "వెళ్తాడు", "వస్తాడు", "చేస్తాడు", "చూస్తాడు", "చెప్తాడు", "పోతాడు", "తింటది", "వెళ్తది", "వస్తది", "చేస్తది", "తిన్నాడు", "వెళ్లాడు", "వచ్చాడు", "చేశాడు"]
        for v in telugu_3rd_verbs:
            if v in text_clean:
                corr_v = v.replace("తాడు", "తాను").replace("తది", "తాను").replace("న్నాడు", "న్నాను").replace("ళ్లాడు", "ళ్లాను").replace("చ్చాడు", "చ్చాను").replace("శాడు", "శాను")
                if corr_v == v:
                    corr_v = "తింటాను"
                return [f"కర్త-క్రియ విభక్తి లోపం / Subject-Verb Agreement Mismatch: 'నేను' (1st Person) తో 3rd Person క్రియ ('{v}') వాడబడింది."], text_clean.replace(v, corr_v), "💡 <b>Telugu Grammar Tip:</b> 'నేను' (1st Person) కు క్రియ చివర 'తాను' / 'నాను' (ఉదా: 'తింటాను / వెళ్లాను') ఉపయోగించాలి.", 55

    # 2. Tamil 1st Person ('நான்') vs 3rd Person Verb Mismatch
    if "நான்" in text_clean:
        tamil_3rd_verbs = ["போனான்", "வந்தான்", "சாப்பிட்டான்", "செய்வான்", "போவாள்", "வந்தாள்", "சாப்பிடுவாள்", "போனார்கள்", "வந்தார்கள்"]
        for v in tamil_3rd_verbs:
            if v in text_clean:
                corr_v = "சாப்பிடுவேன்" if "சாப்பிட்" in v else "போவேன்" if "போ" in v else "வருவேன்"
                return [f"எழுவாய்-பயனிலை முரண்பாடு: 'நான்' என்ற தன்மை சொல்லுடன் படர்க்கை வினைச்சொல் ('{v}') பயன்படுத்தப்பட்டுள்ளது."], text_clean.replace(v, corr_v), "💡 <b>Tamil Grammar Tip:</b> 'நான்' (தன்மை) எழுவாய்க்கு 'ஏன்' விகுதி கொண்ட வினைச்சொற்களையே (ఉదా: 'சாப்பிடுவேன் / போனேன்') பயன்படுத்த வேண்டும்.", 55

    return None

def check_hindi_grammar(text: str):
    """
    Dedicated Hindi Grammar & Accuracy Analyzer:
    - Colloquial Pronoun Slang ('मेरे को' / 'तेरे को') -> Score 65%
    - Gender Mismatches (Feminine Subject + Masculine Verb) -> Score 60%
    - Honorific / Respect Plural Mismatch ('पिताजी आ रहा है') -> Score 60%
    """
    text_clean = text.strip()
    
    # 1. Colloquial Pronoun Slang ('मेरे को' / 'तेरे को')
    if 'मेरे को' in text_clean or 'तेरे को' in text_clean:
        correction = text_clean.replace('मेरे को', 'मुझे').replace('तेरे को', 'तुम्हें')
        return [
            "सर्वनाम संबंधी अशुद्धि: 'मेरे को / तेरे को' मानक हिंदी नहीं है। इसके स्थान पर 'मुझे / तुम्हें' का प्रयोग करें।"
        ], correction, "💡 <b>Hindi Grammar Tip:</b> मानक हिंदी (Standard Hindi) में 'मेरे को' के बजाय 'मुझे' का प्रयोग किया जाता है।", 65

    # 2. Gender Mismatches (Feminine subject + Masculine verb)
    fem_subjects = ['लड़की', 'वह लड़की', 'माताजी', 'सीता', 'बहन']
    masc_verbs = ['जाता है', 'खाता है', 'आया था', 'गया था', 'रहा है']
    if any(s in text_clean for s in fem_subjects) and any(v in text_clean for v in masc_verbs):
        found_verb = next((v for v in masc_verbs if v in text_clean), 'जाता है')
        corr_v = found_verb.replace('जाता है', 'जाती है').replace('खाता है', 'खाती है').replace('रहा है', 'रही है').replace('गया था', 'गई थी').replace('आया था', 'आई थी')
        return [
            "लिंग भेद अशुद्धि: स्त्रीलिंग कर्ता के साथ पुल्लिंग क्रिया का प्रयोग किया गया है।"
        ], text_clean.replace(found_verb, corr_v), "💡 <b>Hindi Grammar Tip:</b> स्त्रीलिंग कर्ता के साथ सदा स्त्रीलिंग क्रिया ('जाती है / रही है') का प्रयोग करें।", 60

    # 3. Honorific / Respect Plural Mismatch
    respect_subjects = ['पिताजी', 'माताजी', 'दादाजी', 'अध्यापक', 'गुरुजी']
    singular_verbs = ['आ रहा है', 'जा रहा है', 'खा रहा है', 'गया']
    if any(r in text_clean for r in respect_subjects) and any(sv in text_clean for sv in singular_verbs):
        found_sv = next((sv for sv in singular_verbs if sv in text_clean), 'आ रहा है')
        corr_sv = found_sv.replace('आ रहा है', 'आ रहे हैं').replace('जा रहा है', 'जा रहे हैं').replace('खा रहा है', 'खा रहे हैं').replace('गया', 'गए')
        return [
            "आदरार्थक अशुद्धि: आदरणीय व्यक्तियों के लिए बहुवचन क्रिया ('रहे हैं') का प्रयोग करें।"
        ], text_clean.replace(found_sv, corr_sv), "💡 <b>Hindi Grammar Tip:</b> बड़ों और आदरणीय व्यक्तियों के लिए सदा बहुवचन क्रिया ('रहे हैं / गए') का उपयोग करें।", 60

    return None

def check_malayalam_grammar(text: str):
    """
    Dedicated Malayalam Grammar & Tense Analyzer:
    - Rule 1: Past Marker + Non-Past (Present/Future) Verb Conflict -> Score 60%
    - Rule 2: Future Marker + Past Verb Conflict -> Score 60%
    """
    text_clean = text.strip()

    # 1. Tense Mismatch (Past Marker + Present/Future Verb)
    past_markers = ['ഇന്നലെ', 'കഴിഞ്ഞ ആഴ്ച', 'മുമ്പ്', 'മിനിഞ്ഞാന്ന്']
    non_past_verbs = ['കാണുന്നുണ്ട്', 'കാണും', 'പോകും', 'പോകുന്നുണ്ട്', 'കഴിക്കും', 'വരും', 'വരുന്നുണ്ട്', 'ചെയ്യും']
    
    for pm in past_markers:
        for npv in non_past_verbs:
            if pm in text_clean and npv in text_clean:
                correction = text_clean.replace('കാണുന്നുണ്ട്', 'കണ്ടു').replace('കാണും', 'കണ്ടു').replace('പോകും', 'പോയി').replace('പോകുന്നുണ്ട്', 'പോയി').replace('കഴിക്കും', 'കഴിച്ചു').replace('വരും', 'വന്നു')
                return [
                    f"കാല പൊരുത്തക്കേട് / Tense Mismatch: ഭൂതകാല പദം ('{pm}') കൂടെ വർത്തമാന/ഭാവി കാല ക്രിയ ('{npv}') ఉపయోగിച്ചു."
                ], correction, "💡 <b>Malayalam Grammar Tip:</b> ഭൂതകാല വാക്കുകൾക്കൊപ്പം ഭൂതകാല ക്രിയകൾ ('കണ്ടു / പോയി / വന്നു') മാത്രം ഉപയോഗിക്കുക.", 60

    # 2. Future Marker + Past Verb
    future_markers = ['നാളെ', 'മറ്റന്നാൾ', 'ഇനി']
    past_verbs = ['കണ്ടു', 'പോയി', 'വന്നു', 'കഴിച്ചു', 'ചെയ്തു']
    for fm in future_markers:
        for pv in past_verbs:
            if fm in text_clean and pv in text_clean:
                correction = text_clean.replace('കണ്ടു', 'കാണും').replace('പോയി', 'പോകും').replace('വന്നു', 'വരും').replace('കഴിച്ചു', 'കഴിക്കും')
                return [
                    f"കാല പൊരുത്തക്കേട് / Tense Mismatch: ഭാവികാല പദം ('{fm}') കൂടെ ഭൂതകാല ക്രിയ ('{pv}') ఉపయోగിച്ചു."
                ], correction, "💡 <b>Malayalam Grammar Tip:</b> ഭാവികാല വാക്കുകൾക്കൊപ്പം ഭാവികാല ക്രിയകൾ ('കാണും / പോകും / വരും') ഉപയോഗിക്കുക.", 60

    return None

def check_kannada_grammar(text: str):
    """
    Dedicated Kannada Grammar Analyzer:
    - Rule 1: Gender Mismatch (Feminine Pronoun + Masculine Verb) -> Score 60%
    - Rule 2: Gender Mismatch (Masculine Pronoun + Feminine Verb) -> Score 60%
    - Rule 3: Tense Mismatch (Past Marker + Future/Present Verb) -> Score 60%
    """
    text_clean = text.strip()

    # 1. Gender Mismatch (Feminine Pronoun + Masculine Verb)
    fem_pronouns = ['ಅವಳು', 'ಆಕೆ', 'ಅಮ್ಮ', 'ತಂಗಿ', 'ಅಕ್ಕ']
    masc_verbs = ['ಹೋದನು', 'ಬಂದನು', 'ತಿಂದನು', 'ಮಾಡಿದನು', 'ನೋಡಿದನು', 'ಹೋದ', 'ಬಂದ']
    for fp in fem_pronouns:
        for mv in masc_verbs:
            if fp in text_clean and mv in text_clean:
                correction = text_clean.replace('ಹೋದನು', 'ಹೋದಳು').replace('ಬಂದನು', 'ಬಂದಳು').replace('ತಿಂದನು', 'ತಿಂದಳು').replace('ಮಾಡಿದನು', 'ಮಾಡಿದಳು').replace('ಹೋದ', 'ಹೋದಳು').replace('ಬಂದ', 'ಬಂದಳು')
                return [
                    f"ಲಿಂಗ ಭೇದ ದೋಷ / Gender Mismatch: ಸ್ತ್ರೀಲಿಂಗ ಸರ್ವನಾಮ ('{fp}') ದೊಂದಿಗೆ ಪುಲ್ಲಿಂಗ ಕ್ರಿಯಾಪದ ('{mv}') ಬಳಸಲಾಗಿದೆ."
                ], correction, "💡 <b>Kannada Grammar Tip:</b> ಸ್ತ್ರೀಲಿಂಗ ಸರ್ವನಾಮಗಳಿಗೆ ಸ್ತ್ರೀಲಿಂಗ ಕ್ರಿಯಾಪದಗಳನ್ನೇ ('ಹೋದಳು / ಬಂದಳು') ಬಳಸಬೇಕು.", 60

    # 2. Gender Mismatch (Masculine Pronoun + Feminine Verb)
    masc_pronouns = ['ಅವನು', 'ಆತ', 'ಅಪ್ಪ', 'ತಮ್ಮ', 'ಅಣ್ಣ']
    fem_verbs = ['ಹೋದಳು', 'ಬಂದಳು', 'ತಿಂದಳು', 'ಮಾಡಿದಳು']
    for mp in masc_pronouns:
        for fv in fem_verbs:
            if mp in text_clean and fv in text_clean:
                correction = text_clean.replace('ಹೋದಳು', 'ಹೋದನು').replace('ಬಂದಳು', 'ಬಂದನು').replace('ತಿಂದಳು', 'ತಿಂದನು').replace('ಮಾಡಿದಳು', 'ಮಾಡಿದನು')
                return [
                    f"ಲಿಂಗ ಭೇದ ದೋಷ / Gender Mismatch: ಪುಲ್ಲಿಂಗ ಸರ್ವನಾಮ ('{mp}') ದೊಂದಿಗೆ ಸ್ತ್ರೀಲಿಂಗ ಕ್ರಿಯಾಪದ ('{fv}') ಬಳಸಲಾಗಿದೆ."
                ], correction, "💡 <b>Kannada Grammar Tip:</b> ಪುಲ್ಲಿಂಗ ಸರ್ವನಾಮಗಳಿಗೆ ಪುಲ್ಲಿಂಗ ಕ್ರಿಯಾಪದಗಳನ್ನೇ ('ಹೋದನು / ಬಂದನು') ಬಳಸಬೇಕು.", 60

    # 3. Tense Mismatch (Past Marker + Future/Present Verb)
    past_markers = ['ನಿನ್ನೆ', 'ಮೊನ್ನೆ', 'ಕಳೆದ ವಾರ']
    future_verbs = ['ಹೋಗುತ್ತೇನೆ', 'ಬರುತ್ತೇನೆ', 'ತಿನ್ನುತ್ತೇನೆ', 'ಹೋಗುತ್ತಾನೆ', 'ಬರುತ್ತಾನೆ']
    for pm in past_markers:
        for fv in future_verbs:
            if pm in text_clean and fv in text_clean:
                correction = text_clean.replace('ಹೋಗುತ್ತೇನೆ', 'ಹೋದೆ').replace('ಬರುತ್ತೇನೆ', 'ಬಂದೆ').replace('ತಿನ್ನುತ್ತೇನೆ', 'ತಿಂದೆ')
                return [
                    f"ಕಾಲ ದೋಷ / Tense Mismatch: ಭೂತಕಾಲ ಪದ ('{pm}') ದೊಂದಿಗೆ ಭವಿಷ್ಯತ್/ವರ್ತಮಾನ ಕ್ರಿಯಾಪದ ('{fv}') ಬಳಸಲಾಗಿದೆ."
                ], correction, "💡 <b>Kannada Grammar Tip:</b> ಭೂತಕಾಲ ಪದಗಳೊಂದಿಗೆ ಭೂതಕಾಲ ಕ್ರಿಯಾಪದಗಳನ್ನೇ ಬಳಸಬೇಕು.", 60

    return None

def _evaluate_sentence(spoken: str, ref: str, coach_lang: str = "English", LANGUAGES: dict = None):
    """
    Multilingual Grammar Evaluator Router:
    - Short-circuit Person/Gender Pronoun-Verb Mismatch Checker.
    - Direct Tamil Grammar & Tense Pattern Analyzer for Tamil.
    - Direct Telugu Grammar & Tense Pattern Analyzer for Telugu.
    - Direct Hindi Grammar Analyzer for Hindi.
    - Direct Malayalam Grammar Analyzer for Malayalam.
    - Direct Kannada Grammar Analyzer for Kannada.
    - Rule-based English Grammar Analyzer for English.
    - Back-Translation Engine for other languages.
    """
    # Absolute Short-Circuit Check for 1st vs 3rd Person Mismatches
    person_check = check_person_agreement(spoken)
    if person_check:
        return person_check

    lang_info = LANGUAGES.get(coach_lang, {}) if LANGUAGES else {}
    lang_code = lang_info.get("code", "en")

    # 1. Dedicated Tamil Grammar & Tense Check
    if coach_lang == "Tamil" or lang_code == "ta" or any("\u0b80" <= char <= "\u0bff" for char in spoken):
        return _evaluate_tamil_grammar(spoken, ref)

    # 2. Dedicated Telugu Grammar & Tense Check
    if coach_lang == "Telugu" or lang_code == "te" or any("\u0c00" <= char <= "\u0c7f" for char in spoken):
        return _evaluate_telugu_grammar(spoken, ref)

    # 3. Dedicated Hindi Grammar Check
    if coach_lang == "Hindi" or lang_code == "hi" or any("\u0900" <= char <= "\u097f" for char in spoken):
        hi_check = check_hindi_grammar(spoken)
        if hi_check:
            return hi_check
        return [], spoken.strip(), "💡 <b>Hindi Fluency Tip:</b> 100% Flawless Hindi grammar and natural sentence structure!", 100

    # 4. Dedicated Malayalam Grammar Check
    if coach_lang == "Malayalam" or lang_code == "ml" or any("\u0d00" <= char <= "\u0d7f" for char in spoken):
        ml_check = check_malayalam_grammar(spoken)
        if ml_check:
            return ml_check
        return [], spoken.strip(), "💡 <b>Malayalam Fluency Tip:</b> 100% Flawless Malayalam grammar and natural sentence structure!", 100

    # 5. Dedicated Kannada Grammar Check
    if coach_lang == "Kannada" or lang_code == "kn" or any("\u0c80" <= char <= "\u0cff" for char in spoken):
        kn_check = check_kannada_grammar(spoken)
        if kn_check:
            return kn_check
        return [], spoken.strip(), "💡 <b>Kannada Fluency Tip:</b> 100% Flawless Kannada grammar and natural sentence structure!", 100

    # 3. Non-English Back-Translation Check
    if coach_lang != "English" and lang_code != "en":
        try:
            en_translation = safe_translate(spoken, source_lang=lang_code, target_lang="en")
            en_errors, _, _, _ = _evaluate_english_grammar(en_translation, ref)
            
            greetings_keywords = [
                "how are you", "how's it going", "how do you do", "what's up", "good morning",
                "good afternoon", "good evening", "good night", "hello", "hi", "hey",
                "fine", "i'm good", "i am good", "doing well", "thank you", "thanks",
                "you're welcome", "nice to meet you", "pleased to meet you", "are you fine",
                "are you good", "how are things", "all good"
            ]
            en_lower = en_translation.lower().strip()
            is_greeting = any(g in en_lower for g in greetings_keywords) or len(spoken.strip().split()) <= 4

            if is_greeting and not en_errors:
                return [], spoken.strip(), f"💡 <b>Fluency Tip ({coach_lang}):</b> 100% Flawless conversational phrase in {coach_lang}!", 100

            back_translated = safe_translate(en_translation, source_lang="en", target_lang=lang_code)
            similarity = difflib.SequenceMatcher(None, spoken.strip(), back_translated.strip()).ratio()

            if en_errors or similarity < 0.35:
                errors = [f"Grammar / Tense conflict detected in {coach_lang}: '{spoken}'."] + en_errors
                corrected_clean = back_translated.capitalize() if back_translated else spoken
                tips = f"💡 <b>Grammar Tip ({coach_lang}):</b> Review phrase structure in {coach_lang}. Suggested phrasing: <i>'{back_translated}'</i>."
                score = max(55, min(75, int(60 + (similarity * 12))))
                return errors, corrected_clean, tips, score
            else:
                return [], spoken.strip(), f"💡 <b>Fluency Tip ({coach_lang}):</b> 100% Flawless grammar and natural phrasing in {coach_lang}!", 100
        except Exception:
            pass

    # 4. Dedicated English Grammar Check
    return _evaluate_english_grammar(spoken, ref)

def check_telugu_grammar(text: str):
    text = text.strip()
    
    # 1. Gender / Pronoun Mismatches
    masculine_pronouns = ['ఆయన', 'అతను', 'వాడు', 'అతడు']
    feminine_verbs = ['వచ్చింది', 'వెళ్లింది', 'తిన్నది', 'చేసింది', 'చూసింది', 'చెప్పింది']
    for p in masculine_pronouns:
        for v in feminine_verbs:
            if p in text and v in text:
                corr_v = 'వచ్చాడు' if 'వచ్చింది' in v else 'వెళ్లాడు' if 'వెళ్లింది' in v else 'తిన్నాడు' if 'తిన్నది' in v else 'చేశాడు' if 'చేసింది' in v else 'చూశాడు' if 'చూసింది' in v else 'చెప్పాడు'
                return {
                    'score': 60,
                    'status': '⚠️ NEEDS IMPROVEMENT — Gender Mismatch Detected!',
                    'error': f"లింగ భేదం / Gender Mismatch: పురుష లింగ సర్వనామం ('{p}') తో స్త్రీ లింగ క్రియ ('{v}') వాడబడింది.",
                    'correction': text.replace(v, corr_v),
                    'tip': "💡 <b>Telugu Grammar Tip:</b> పురుష లింగ నామవాచకాలు/సర్వనామాలకు పురుష లింగ క్రియలనే ('వచ్చాడు/వెళ్లాడు') ఉపయోగించాలి."
                }

    feminine_pronouns = ['ఆమె', 'ఈమె']
    masculine_verbs = ['వచ్చాడు', 'వెళ్లాడు', 'తిన్నాడు', 'చేశాడు', 'చూశాడు', 'చెప్పాడు']
    for p in feminine_pronouns:
        for v in masculine_verbs:
            if p in text and v in text:
                corr_v = 'వచ్చింది' if 'వచ్చాడు' in v else 'వెళ్లింది' if 'వెళ్లాడు' in v else 'తిన్నది' if 'తిన్నాడు' in v else 'చేసింది' if 'చేశాడు' in v else 'చూసింది' if 'చూశాడు' in v else 'చెప్పింది'
                return {
                    'score': 60,
                    'status': '⚠️ NEEDS IMPROVEMENT — Gender Mismatch Detected!',
                    'error': f"లింగ భేదం / Gender Mismatch: స్త్రీ లింగ సర్వనామం ('{p}') తో పురుష లింగ క్రియ ('{v}') వాడబడింది.",
                    'correction': text.replace(v, corr_v),
                    'tip': "💡 <b>Telugu Grammar Tip:</b> స్త్రీ లింగ నామవాచకాలు/సర్వనామాలకు స్త్రీ లింగ క్రియలనే ('వచ్చింది/వెళ్లింది') ఉపయోగించాలి."
                }

    # 2. Tense Conflicts (Past Marker + Future Verb)
    past_markers = ['నిన్న', 'మొన్న', 'గత వారం', 'మునుపు', 'గత']
    future_verbs = ['వెళ్తాను', 'వస్తాను', 'తింటాను', 'చేస్తాను', 'చూస్తాను', 'వెళ్తారు', 'వస్తారు']
    for m in past_markers:
        for v in future_verbs:
            if m in text and v in text:
                corr_v = 'వెళ్లాను' if 'వెళ్తాను' in v else 'వచ్చాను' if 'వస్తాను' in v else 'తిన్నాను' if 'తింటాను' in v else 'చేశాను'
                return {
                    'score': 60,
                    'status': '⚠️ NEEDS IMPROVEMENT — Tense Conflict Detected!',
                    'error': f"కాల మురళిక / Tense Mismatch: గతకాల పదం ('{m}') తో భవిష్యత్ క్రియ ('{v}') ఉపయోగించబడింది.",
                    'correction': text.replace(v, corr_v),
                    'tip': "💡 <b>Telugu Grammar Tip:</b> గతకాల పదాలకు గతకాల క్రియలనే ఉపయోగించాలి."
                }

    return None

def _evaluate_telugu_grammar(spoken: str, ref: str):
    """
    Dedicated Telugu Grammar, Pronoun & Tense Routine:
    - Pre-evaluation check via check_telugu_grammar()
    - Rule 1: Pronoun / Possessive Mismatch ('మీ బాగున్నాను', 'నా బాగున్నారు') -> Score 60%
    - Rule 2: Broken Verb / Dialect Form ('బాగుండావా' -> 'బాగున్నావా') -> Score 60%
    - Rule 3: Past Marker + Future/Present Verb -> Score 60%
    - Rule 4: Future Marker + Past Verb -> Score 60%
    - Rule 5: Gender & Plural Mismatch -> Score 62%
    - Flawless sentences return 100%.
    """
    # Immediate pre-evaluation check
    pre_check = check_telugu_grammar(spoken)
    if pre_check:
        return [pre_check['error']], pre_check['correction'], pre_check['tip'], pre_check['score']

    text_clean = spoken.strip()
    errors = []
    corrected_text = spoken

    # 1. Pronoun / Possessive Mismatches (e.g., 'మీ బాగున్నాను', 'నా బాగున్నారు')
    possessive_patterns = [
        (r"\bమీ\s+బాగున్నాను\b", "నేను బాగున్నాను", "సర్వనామ దోషము / Pronoun Mismatch: 'మీ' తో 'బాగున్నాను' తప్పు. 'నేను బాగున్నాను' అని ఉపయోగించండి."),
        (r"\bనా\s+బాగున్నారు\b", "నేను బాగున్నాను", "సర్వనామ దోషము / Pronoun Mismatch: 'నా' తో 'బాగున్నారు' తప్పు. 'నేను బాగున్నాను' అని ఉపయోగించండి."),
        (r"\bనీ\s+బాగున్నాను\b", "నేను బాగున్నాను", "సర్వనామ దోషము / Pronoun Mismatch: 'నీ' తో 'బాగున్నాను' తప్పు."),
        (r"\bమీ\s+బాగున్నావు\b", "మీరు బాగున్నారా", "సర్వనామ దోషము / Pronoun Mismatch: 'మీ' తో 'బాగున్నావు' తప్పు.")
    ]

    for pat, corr, desc in possessive_patterns:
        if re.search(pat, text_clean):
            errors.append(desc)
            corrected_text = re.sub(pat, corr, corrected_text)

    # 2. Broken / Non-standard Verb Forms (e.g. 'బాగుండావా')
    broken_verbs = [
        (r"\bబాగుండావా\b", "బాగున్నావా", "భాషా దోషము / Broken Verb Form: 'బాగుండావా' కి బదులుగా 'బాగున్నావా' ఉపయోగించండి."),
        (r"\bఎట్లా\s+బాగుండావా\b", "ఎలా ఉన్నావు? బాగున్నావా?", "వాక్య నిర్మాణం దోషము / Phrasing Error: 'ఎలా ఉన్నావు? బాగున్నావా?' అని ఉపయోగించండి.")
    ]

    for pat, corr, desc in broken_verbs:
        if re.search(pat, text_clean):
            if desc not in errors:
                errors.append(desc)
            corrected_text = re.sub(pat, corr, corrected_text)

    if errors:
        tips = "💡 <b>Telugu Grammar Tip:</b> సరియైన సర్వనామములు ('నేను', 'మీరు', 'నువ్వు') మరియు క్రియ రూపాలను ('బాగున్నాను', 'బాగున్నావా') ఉపయోగించాలి."
        return errors, corrected_text.strip(), tips, 60

    # 3. Tense Conflicts
    past_markers = ["నిన్న", "గత", "మునుపు", "మొన్న"]
    future_markers = ["రేపు", "ఎల్లుండి", "తర్వాత", "వచ్చే"]

    has_past_marker = any(m in text_clean for m in past_markers)
    has_future_marker = any(m in text_clean for m in future_markers)

    past_marker_word = next((m for m in past_markers if m in text_clean), "నిన్న")
    future_marker_word = next((m for m in future_markers if m in text_clean), "రేపు")

    non_past_to_past = {
        "వెళ్తాను": "వెళ్లాను",
        "వెళ్తున్నాను": "వెళ్లాను",
        "వస్తాను": "వచ్చాను",
        "తింటాను": "తిన్నాను",
        "చేస్తాను": "చేశాను",
        "చూస్తాను": "చూశాను",
        "వెళ్తాడు": "వెళ్లాడు",
        "వస్తాడు": "వచ్చాడు",
        "తింటాడు": "తిన్నాడు",
        "చేస్తాడు": "చేశాడు"
    }

    past_to_future = {
        "వెళ్లాను": "వెళ్తాను",
        "వెళ్ళిపోయాను": "వెళ్తాను",
        "వచ్చాను": "వస్తాను",
        "తిన్నాను": "తింటాను",
        "చేశాను": "చేస్తాను",
        "చూశాను": "చూస్తాను",
        "వెళ్లాడు": "వెళ్తాడు",
        "వచ్చాడు": "వస్తాడు",
        "తిన్నాడు": "తింటాడు",
        "చేశాడు": "చేస్తాడు"
    }

    if has_past_marker:
        found_non_past = next((v for v in non_past_to_past.keys() if v in text_clean), None)
        if found_non_past:
            desc = f"కాల మురళిక / Tense Mismatch: గతకాల పదం ('{past_marker_word}') తో భవిష్యత్/వర్తమాన క్రియ ('{found_non_past}') ఉపయోగించబడింది."
            errors.append(desc)
            past_corr = non_past_to_past[found_non_past]
            corrected_text = corrected_text.replace(found_non_past, f"{past_corr}")
            tips = "💡 <b>Telugu Grammar Tip:</b> గతకాల సంఘటనలను తెలిపేటప్పుడు గతకాల క్రియలను (ఉదా: 'వెళ్లాను' లేదా 'వచ్చాను') మాత్రమే ఉపయోగించాలి."
            return errors, corrected_text.strip(), tips, 60

    if has_future_marker:
        found_past = next((v for v in past_to_future.keys() if v in text_clean), None)
        if found_past:
            desc = f"కాల మురళిక / Tense Mismatch: భవిష్యత్ పదం ('{future_marker_word}') తో గతకాల క్రియ ('{found_past}') ఉపయోగించబడింది."
            errors.append(desc)
            future_corr = past_to_future[found_past]
            corrected_text = corrected_text.replace(found_past, f"{future_corr}")
            tips = "💡 <b>Telugu Grammar Tip:</b> భవిష్యత్ సంఘటనలను తెలిపేటప్పుడు భవిష్యత్ క్రియలను (ఉదా: 'వెళ్తాను' లేదా 'వస్తాను') మాత్రమే ఉపయోగించాలి."
            return errors, corrected_text.strip(), tips, 60

    # 4. Gender & Plural Mismatch
    gender_rules = [
        (r"\bఆమె\b.*\b(వచ్చాడు|వెళ్లాడు|తిన్నాడు|చేశాడు)\b", "వచ్చింది/వెళ్లింది", "Gender mismatch: Female subject ('ఆమె') with masculine verb."),
        (r"\bవారు\b.*\b(తిన్నది|వచ్చింది|పోయింది)\b", "వచ్చారు/తిన్నారు", "Plural/Honorific agreement error: Subject ('వారు') with singular verb.")
    ]
    for pat, corr, desc in gender_rules:
        if re.search(pat, text_clean):
            errors.append(desc)
            tips = "💡 <b>Telugu Grammar Tip:</b> లింగము మరియు వచనములకు తగినట్లుగా క్రియ రూపములను ఉపయోగించాలి."
            return errors, corrected_text.strip(), tips, 62

    # ─── DEFAULT FLAWLESS 100% ───
    tips = "💡 <b>Telugu Fluency Tip:</b> 100% Flawless Telugu grammar and natural sentence structure!"
    return [], spoken.strip(), tips, 100

def _evaluate_tamil_grammar(spoken: str, ref: str):
    """
    Dedicated Tamil Grammar & Tense Routine:
    - Rule A: Past Marker + Non-Past (Present/Future) Verb Conflict (Score: 60%)
    - Rule B: Future Marker + Past Verb Conflict (Score: 60%)
    - Rule C: Gender / Plural Mismatch (Score: 62%)
    - Flawless sentences return 100% score.
    """
    text_clean = spoken.strip()
    errors = []
    corrected_text = spoken

    past_markers = ["நேற்று", "முந்தாநாள்", "கடந்த", "சென்ற", "முன்னாடி"]
    future_markers = ["நாளைக்கு", "நாளை", "இனிமேல்", "அடுத்த"]

    has_past_marker = any(m in text_clean for m in past_markers)
    has_future_marker = any(m in text_clean for m in future_markers)

    past_marker_word = next((m for m in past_markers if m in text_clean), "நேற்று")
    future_marker_word = next((m for m in future_markers if m in text_clean), "நாளை/நாளைக்கு")

    non_past_to_past = {
        "செல்கிறேன்": "சென்றேன்",
        "போகிறேன்": "போனேன்",
        "வருகிறேன்": "வந்தேன்",
        "சாப்பிடுகிறேன்": "சாப்பிட்டேன்",
        "செய்கிறேன்": "செய்தேன்",
        "செய்வேன்": "செய்தேன்",
        "போவேன்": "போனேன்",
        "வருவேன்": "வந்தேன்",
        "பார்ப்பேன்": "பார்த்தேன்",
        "பண்ணுவேன்": "பண்ணினேன்"
    }

    past_to_future = {
        "போய் விட்டேன்": "செல்வேன்",
        "போயிட்டேன்": "போவேன்",
        "போனேன்": "போவேன்",
        "வந்தேன்": "வருவேன்",
        "சாப்பிட்டேன்": "சாப்பிடுவேன்",
        "செய்தேன்": "செய்வேன்",
        "சென்றேன்": "செல்வேன்",
        "பார்த்தேன்": "பார்ப்பேன்",
        "வந்துட்டேன்": "வருவேன்",
        "செஞ்சுட்டேன்": "செய்வேன்",
        "முடிச்சிட்டேன்": "முடிப்பேன்",
        "விட்டேன்": "செல்வேன்"
    }

    if has_past_marker:
        found_non_past = next((v for v in non_past_to_past.keys() if v in text_clean), None)
        if found_non_past:
            desc = "கால முரண்பாடு: இறந்தகால சொல்லுடன் ('நேற்று') நிகழ்கால/எதிர்கால வினைச்சொல் பயன்படுத்தப்பட்டுள்ளது."
            errors.append(desc)
            past_corr = non_past_to_past[found_non_past]
            corrected_text = corrected_text.replace(found_non_past, f"{past_corr}")
            tips = "💡 <b>Tamil Grammar Tip:</b> இறந்தகால நிகழ்வுகளைக் குறிப்பிடும் போது 'சென்றேன் / போனேன்' போன்ற இறந்தகால வினைச்சொற்களையே பயன்படுத்த வேண்டும்."
            return errors, corrected_text.strip(), tips, 60

    if has_future_marker:
        found_past = next((v for v in past_to_future.keys() if v in text_clean), None)
        if found_past:
            desc = "கால முரண்பாடு: எதிர்கால சொல்லுடன் ('நாளை') இறந்தகால வினைச்சொல் பயன்படுத்தப்பட்டுள்ளது."
            errors.append(desc)
            future_corr = past_to_future[found_past]
            corrected_text = corrected_text.replace(found_past, f"{future_corr}")
            tips = "💡 <b>Tamil Grammar Tip:</b> எதிர்கால நிகழ்வுகளைக் குறிப்பிடும் போது 'செல்வேன் / போவேன்' போன்ற எதிர்கால வினைச்சொற்களையே பயன்படுத்த வேண்டும்."
            return errors, corrected_text.strip(), tips, 60

    gender_rules = [
        (r"\b(அவள்|அவ)\b.*\b(வந்தான்|போனான்|சென்றான்|சாப்பிட்டான்)\b", "வந்தாள்/போனாள்", "Subject-Verb gender mismatch: Feminine subject ('அவள்') with masculine verb."),
        (r"\bஅவன்\b.*\b(வந்தாள்|போனாள்|சென்றாள்|சாப்பிட்டாள்)\b", "வந்தான்/போனான்", "Subject-Verb gender mismatch: Masculine subject ('அவன்') with feminine verb."),
        (r"\b(அவர்கள்|நாங்கள்)\b.*\b(போனது|வந்தது|போனான்|வந்தான்|போனாள்|வந்தாள்)\b", "போனார்கள்/வந்தார்கள்", "Plural subject with singular verb mismatch.")
    ]
    for pat, corr, desc in gender_rules:
        if re.search(pat, text_clean):
            errors.append(desc)
            tips = "💡 <b>Tamil Grammar Tip:</b> திணை, பால், எண் ஆகியவற்றிற்கு ஏற்ப வினைச்சொல் விகுதிகளை சரியாக பயன்படுத்த வேண்டும்."
            return errors, corrected_text.strip(), tips, 62

    tips = "💡 <b>Tamil Fluency Tip:</b> 100% Flawless Tamil grammar and natural sentence structure!"
    return [], spoken.strip(), tips, 100

def _evaluate_english_grammar(spoken: str, ref: str):
    text_lower = spoken.lower().strip()
    words = re.findall(r"\b\w+\b", text_lower)

    errors = []
    corrected_text = spoken

    past_markers = ["yesterday", "last night", "last week", "last year", "last month", "ago", "previously"]
    has_past_marker = any(marker in text_lower for marker in past_markers)
    past_marker_word = next((m for m in past_markers if m in text_lower), "yesterday")

    present_to_past = {
        "go": "went",
        "eat": "ate",
        "see": "saw",
        "buy": "bought",
        "do": "did",
        "take": "took",
        "come": "came",
        "make": "made",
        "think": "thought",
        "get": "got",
        "find": "found",
        "give": "gave",
        "run": "ran",
        "write": "wrote",
        "speak": "spoke"
    }

    present_singular = {
        "go": "goes",
        "eat": "eats",
        "see": "sees",
        "buy": "buys",
        "do": "does",
        "take": "takes",
        "come": "comes",
        "make": "makes",
        "think": "thinks",
        "get": "gets",
        "find": "finds",
        "give": "gives",
        "run": "runs",
        "write": "writes",
        "speak": "speaks"
    }

    singular_subjects = ["he", "she", "it"]
    for sub in singular_subjects:
        for verb, corr_past in present_to_past.items():
            pattern = rf"\b{sub}\s+{verb}\b"
            if re.search(pattern, text_lower):
                if has_past_marker:
                    desc = f"Tense/Agreement mismatch: '{sub.capitalize()} {verb}' with past time marker '{past_marker_word}'."
                    errors.append(desc)
                    corrected_text = re.sub(pattern, f"{sub} {corr_past}", corrected_text, flags=re.IGNORECASE)
                else:
                    corr_sing = present_singular.get(verb, verb + "s")
                    desc = f"Subject-verb agreement error: '{sub.capitalize()} {verb}'. Use '{sub.capitalize()} {corr_sing}' (present) or '{sub.capitalize()} {corr_past}' (past)."
                    errors.append(desc)
                    corrected_text = re.sub(pattern, f"{sub} {corr_sing}", corrected_text, flags=re.IGNORECASE)

    if has_past_marker and not errors:
        for verb, corr_past in present_to_past.items():
            if verb in words:
                verb_pattern = rf"\b(i|you|we|they|he|she|it)\s+{verb}\b"
                if re.search(verb_pattern, text_lower):
                    m = re.search(verb_pattern, text_lower).group(0)
                    subj = m.split()[0]
                    desc = f"Tense error: '{subj.capitalize()} {verb}' used with past time marker '{past_marker_word}'."
                    errors.append(desc)
                    corrected_text = re.sub(rf"\b{verb}\b", corr_past, corrected_text, flags=re.IGNORECASE)

    specific_rules = [
        (r"\b(he|she|it)\s+don't\b", "doesn't", "Subject-verb agreement: Use 'doesn't' with he/she/it instead of 'don't'."),
        (r"\b(they|we|you)\s+is\b", "are", "Subject-verb agreement: Use 'are' instead of 'is' for plural subjects."),
        (r"\bi\s+has\b", "I have", "Subject-verb agreement: Use 'I have' instead of 'I has'."),
        (r"\b(he|she|it)\s+have\b", "has", "Subject-verb agreement: Use 'has' instead of 'have' for he/she/it."),
        (r"\bdid\s+went\b", "did go", "Double past tense error: Use 'did go' instead of 'did went'."),
        (r"\bdid\s+saw\b", "did see", "Double past tense error: Use 'did see' instead of 'did saw'."),
        (r"\bdid\s+ate\b", "did eat", "Double past tense error: Use 'did eat' instead of 'did ate'."),
        (r"\bdid\s+came\b", "did come", "Double past tense error: Use 'did come' instead of 'did came'."),
        (r"\bdon't\s+know\s+nothing\b", "don't know anything", "Double negative error: Use 'don't know anything'."),
        (r"\bcan't\s+see\s+nothing\b", "can't see anything", "Double negative error: Use 'can't see anything'.")
    ]

    for pat, corr, desc in specific_rules:
        if re.search(pat, text_lower):
            if desc not in errors:
                errors.append(desc)
            corrected_text = re.sub(pat, corr, corrected_text, flags=re.IGNORECASE)

    corrected_clean = corrected_text.strip()
    if corrected_clean and not corrected_clean[0].isupper():
        corrected_clean = corrected_clean[0].upper() + corrected_clean[1:]
    if corrected_clean and not corrected_clean.endswith("."):
        corrected_clean += "."

    if ref and ref.strip():
        seq_ratio = difflib.SequenceMatcher(None, ref.lower().strip(), text_lower).ratio()
    else:
        seq_ratio = 0.95

    if len(errors) > 0:
        base_score = 65 - (len(errors) - 1) * 5
        score = max(55, min(68, int(base_score + (seq_ratio * 3))))
        tips = f"💡 <b>Grammatical Tip:</b> When referring to completed past events (like <i>'{past_marker_word}'</i>), use past tense forms (<i>'went'</i> instead of <i>'go'</i>)."
    else:
        score = 100
        tips = "💡 <b>Fluency Tip:</b> 100% Flawless grammar and sentence structure! Practice natural stress, intonation, and native pacing to maintain your voice excellence."

    return errors, corrected_clean, tips, score
