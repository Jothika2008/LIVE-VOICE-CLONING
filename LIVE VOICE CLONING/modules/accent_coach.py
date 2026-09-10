"""
modules/accent_coach.py
═══════════════════════════════════════════════════════════════
AI Accent, Translation & Grammar Coach Module
Features:
- Clean, intuitive tabbed UI (Translation + Accent Coach)
- ElevenLabs Multilingual Neural v2 Voice Synthesis
- Accurate Text-to-Text Neural Translation
- Intelligent Grammar, Agreement & Tense Evaluator (No false errors)
- High-Accuracy Target Phrase Pronunciation Evaluation
═══════════════════════════════════════════════════════════════
"""

import os
import io
import time
import re
import difflib
import json
import urllib.request
import urllib.parse
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
from gtts import gTTS
import streamlit as st
from core.translator import safe_translate
from core.elevenlabs_client import ElevenLabsClient


# ════════════════════════════════════════════════════════════
# 1. TEXT COMPARISON & SIMILARITY HELPERS
# ════════════════════════════════════════════════════════════
def _normalize_text(text: str) -> str:
    """Cleans text of punctuation and redundant spaces for accurate comparison."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r'[^\w\s\u0600-\u06FF\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def _compute_similarity(ref: str, hyp: str) -> float:
    """Calculates combined lexical and token overlap similarity (0.0 to 1.0)."""
    norm_r = _normalize_text(ref)
    norm_h = _normalize_text(hyp)
    if not norm_r or not norm_h:
        return 0.0
    seq_ratio = difflib.SequenceMatcher(None, norm_r, norm_h).ratio()
    r_tokens = set(norm_r.split())
    h_tokens = set(norm_h.split())
    overlap = len(r_tokens & h_tokens) / max(len(r_tokens), 1)
    return 0.6 * seq_ratio + 0.4 * overlap


# ════════════════════════════════════════════════════════════
# 2. ELEVENLABS NEURAL VOICE SYNTHESIS & DYNAMIC VOICES
# ════════════════════════════════════════════════════════════
def _synthesize_elevenlabs_voice(text: str, lang_code: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL") -> tuple:
    """
    Synthesizes speech using ElevenLabs Multilingual Neural API (model: eleven_multilingual_v2).
    Falls back gracefully to Google gTTS if offline, key missing, or quota exceeded.
    Returns: (audio_bytes, engine_label)
    """
    if not text or not text.strip():
        return b"", ""

    # Attempt 1: ElevenLabs API (Resolve key from session or env)
    key = st.session_state.get("elevenlabs_api_key") or os.getenv("ELEVENLABS_API_KEY")
    client = ElevenLabsClient(key)
    if client.is_configured():
        try:
            audio_bytes = client.text_to_speech(
                text=text.strip(),
                voice_id=voice_id,
                model_id="eleven_multilingual_v2"
            )
            if audio_bytes and len(audio_bytes) > 500:
                return audio_bytes, "ElevenLabs Neural API (eleven_multilingual_v2)"
        except Exception as e:
            print(f"[ElevenLabs API] Fallback triggered: {e}")

    # Attempt 2: gTTS fallback
    try:
        clean_code = lang_code.split("-")[0].lower() if "-" in lang_code else lang_code.lower()
        tts = gTTS(text=text.strip(), lang=clean_code, slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp.read(), "Standard Neural TTS (Fallback)"
    except Exception as e:
        print(f"[TTS Fallback Error]: {e}")
        return b"", ""


def _get_dynamic_elevenlabs_voices(client: ElevenLabsClient) -> dict:
    """
    Dynamically loads available voice personas directly from ElevenLabs API using the user's API key.
    Includes custom cloned voices, instant clones, and multilingual neural voices.
    Falls back gracefully to default voice presets if offline or unconfigured.
    """
    voices_dict = {}

    # Check for active custom cloned voice in session
    cloned_id = st.session_state.get("active_cloned_voice_id")
    if cloned_id:
        voices_dict["👤 Active Cloned Voice (Custom Session)"] = cloned_id

    # Fetch dynamic voices from ElevenLabs API
    if client and client.is_configured():
        try:
            live_voices = client.get_voices()
            if live_voices:
                for v in live_voices:
                    vid = v.get("voice_id")
                    if not vid:
                        continue
                    vname = v.get("name", "Voice")
                    cat = str(v.get("category", "")).lower()
                    labels = v.get("labels") or {}
                    gender = str(labels.get("gender", "")).lower()
                    accent = labels.get("accent", "")
                    use_case = labels.get("use_case", "") or labels.get("descriptive", "")

                    if cat in ["cloned", "generated"] or "custom" in cat:
                        icon = "✨"
                    elif "female" in gender:
                        icon = "👩"
                    elif "male" in gender:
                        icon = "👨"
                    else:
                        icon = "🎙️"

                    details = []
                    if cat in ["cloned", "generated"]:
                        details.append("Cloned")
                    if accent:
                        details.append(accent.title())
                    if use_case:
                        details.append(use_case.replace("_", " ").title())

                    detail_str = f" ({', '.join(details)})" if details else ""
                    label = f"{icon} {vname}{detail_str}"
                    # If duplicate label exists, append voice ID prefix
                    if label in voices_dict:
                        label = f"{label} [{vid[:4]}]"
                    voices_dict[label] = vid
                return voices_dict
        except Exception as e:
            print(f"[_get_dynamic_elevenlabs_voices] Warning: {e}")

    # Fallback to standard presets if API key not configured or offline
    fallback_defaults = {
        "👩 Sarah (American, Professional)": "EXAVITQu4vr4xnSDxMaL",
        "👨 Charlie (Australian, Deep & Energetic)": "IKne3meq5aSn9XLyUdCD",
        "🧔 George (British, Storyteller)": "JBFqnCBsd6RMkjVDRZzb",
        "👧 Laura (American, Quirky Attitude)": "FGY2WhTYpPnrIDTdsKH5",
        "👱 Roger (American, Casual Resonant)": "CwhRBWXzGAHq8TQ4Fs17"
    }
    for k, v in fallback_defaults.items():
        if k not in voices_dict:
            voices_dict[k] = v

    return voices_dict


# ════════════════════════════════════════════════════════════
# 3. MULTILINGUAL GRAMMAR & AGREEMENT ENGINE
# ════════════════════════════════════════════════════════════
def check_person_agreement(spoken: str):
    """Checks 1st vs 3rd person pronoun-verb agreement in Telugu & Tamil."""
    text_clean = spoken.strip()

    # Telugu: నేను (1st person) vs 3rd person verb
    if "నేను" in text_clean:
        telugu_3rd_verbs = ["తింటాడు", "వెళ్తాడు", "వస్తాడు", "చేస్తాడు", "చూస్తాడు", "చెప్తాడు", "పోతాడు", "తింటది", "వెళ్తది", "వస్తది", "చేస్తది", "తిన్నాడు", "వెళ్లాడు", "వచ్చాడు", "చేశాడు"]
        for v in telugu_3rd_verbs:
            if v in text_clean:
                corr_v = v.replace("తాడు", "తాను").replace("తది", "తాను").replace("న్నాడు", "న్నాను").replace("ళ్లాడు", "ళ్లాను").replace("చ్చాడు", "చ్చాను").replace("శాడు", "శాను")
                if corr_v == v:
                    corr_v = "తింటాను"
                return [f"కర్త-క్రియ విభక్తి లోపం / Subject-Verb Mismatch: 'నేను' (1st Person) తో 3rd Person క్రియ ('{v}') వాడబడింది."], text_clean.replace(v, corr_v), "💡 <b>Telugu Tip:</b> 'నేను' తో 'తాను / నాను' ముగిసే క్రియలను వాడాలి (ఉదా: 'తింటాను / వెళ్లాను').", 55

    # Tamil: நான் (1st person) vs 3rd person verb
    if "நான்" in text_clean:
        tamil_3rd_verbs = ["போனான்", "வந்தான்", "சாப்பிட்டான்", "செய்வான்", "போவாள்", "வந்தாள்", "சாப்பிடுவாள்", "போனார்கள்", "வந்தார்கள்", "சென்றான்", "சென்றாள்"]
        for v in tamil_3rd_verbs:
            if v in text_clean:
                corr_v = "சாப்பிடுவேன்" if "சாப்பிட்" in v else "போவேன்" if "போ" in v else "வருவேன்" if "வ" in v else "செல்வேன்"
                return [f"எழுவாய்-பயனிலை முரண்பாடு: 'நான்' எழுவாயுடன் படர்க்கை வினைச்சொல் ('{v}') பயன்படுத்தப்பட்டுள்ளது."], text_clean.replace(v, corr_v), "💡 <b>Tamil Tip:</b> 'நான்' எழுவாய்க்கு 'ஏன்' விகுதி கொண்ட வினைச்சொற்களையே ('சாப்பிடுவேன் / போனேன்') பயன்படுத்தவும்.", 55

    return None


def check_hindi_grammar(text: str):
    """Hindi Slang Pronoun, Gender & Honorific Check."""
    text_clean = text.strip()
    if 'मेरे को' in text_clean or 'तेरे को' in text_clean:
        correction = text_clean.replace('मेरे को', 'मुझे').replace('तेरे को', 'तुम्हें')
        return ["सर्वनाम अशुद्धि: 'मेरे को / तेरे को' के स्थान पर मानक हिंदी 'मुझे / तुम्हें' का प्रयोग करें।"], correction, "💡 <b>Hindi Tip:</b> मानक हिंदी में 'मुझे' का प्रयोग करें।", 65

    fem_subjects = ['लड़की', 'माताजी', 'सीता', 'बहन', 'महिला']
    masc_verbs = ['जाता है', 'खाता है', 'आया था', 'गया था', 'रहा है']
    if any(s in text_clean for s in fem_subjects) and any(v in text_clean for v in masc_verbs):
        found_verb = next((v for v in masc_verbs if v in text_clean), 'जाता है')
        corr_v = found_verb.replace('जाता है', 'जाती है').replace('खाता है', 'खाती है').replace('रहा है', 'रही है').replace('गया था', 'गई थी').replace('आया था', 'आई थी')
        return ["लिंग भेद अशुद्धि: स्त्रीलिंग कर्ता के साथ पुल्लिंग क्रिया का प्रयोग किया गया है।"], text_clean.replace(found_verb, corr_v), "💡 <b>Hindi Tip:</b> स्त्रीलिंग कर्ता के साथ सदा स्त्रीलिंग क्रिया का प्रयोग करें।", 60

    return None


def _check_word_validity(text: str) -> list:
    """Detects keyboard mashing, repeated characters, and unpronounceable non-words."""
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z]+\b", text)
    errors = []
    for w in words:
        # Check repeated characters (e.g., 'aaaaaa', 'zzzz')
        if re.search(r'(.)\1{3,}', w):
            errors.append(f"Unrecognized word / repeated characters: '{w}'.")
        # Words longer than 3 with no vowels
        elif len(w) >= 4 and not re.search(r'[aeiouyAEIOUY]', w):
            errors.append(f"Unrecognized word / missing vowels: '{w}'.")
        # 5+ consecutive consonants (e.g. 'asdfghjkl')
        elif re.search(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{5,}', w):
            errors.append(f"Possible spelling mistake / non-word: '{w}'.")
    return errors


def check_languagetool_api(text: str, lang_code: str = "en-US") -> tuple:
    """
    Queries LanguageTool's free public NLP grammar & spell check endpoint.
    Fast (timeout=3s) and zero API key needed.
    Returns: (errors_list, corrected_text)
    """
    if not text or not text.strip():
        return [], text

    prep_text = text.strip()
    if prep_text and not prep_text[0].isupper() and prep_text[0].isalpha():
        prep_text = prep_text[0].upper() + prep_text[1:]

    try:
        url = "https://api.languagetool.org/v2/check"
        data = urllib.parse.urlencode({"text": prep_text, "language": lang_code}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            matches = res.get("matches", [])
            errors = []
            corrected = prep_text

            # Sort descending by offset so substring replacements don't disrupt earlier offsets
            matches_sorted = sorted(
                [m for m in matches if m.get("offset") is not None and m.get("length")],
                key=lambda x: x["offset"],
                reverse=True
            )

            for m in matches:
                rule_id = m.get("rule", {}).get("id", "")
                if rule_id in ["UPPERCASE_SENTENCE_START"]:
                    continue

                raw_msg = m.get("message", "Grammar or spelling issue")
                msg = raw_msg.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
                replacements = [r["value"] for r in m.get("replacements", []) if r.get("value")]
                sug = f" (Suggestion: '{replacements[0]}')" if replacements else ""
                errors.append(f"{msg}{sug}")

            for m in matches_sorted:
                rule_id = m.get("rule", {}).get("id", "")
                if rule_id in ["UPPERCASE_SENTENCE_START"]:
                    continue
                replacements = [r["value"] for r in m.get("replacements", []) if r.get("value")]
                if replacements:
                    off = m["offset"]
                    length = m["length"]
                    corrected = corrected[:off] + replacements[0] + corrected[off + length:]

            return errors, corrected
    except Exception:
        # Graceful fallback to local rules if offline
        return [], text


def _add_error_if_not_duplicate(msg: str, errors: list):
    """Adds msg to errors list only if not semantically duplicate of an already reported error."""
    msg_lower = msg.lower()
    msg_words = set(re.findall(r"\b[a-zA-Z]{2,}\b", msg_lower))
    meta = {
        "subject", "verb", "agreement", "use", "instead", "of", "error", "suggestion",
        "with", "the", "pronoun", "form", "must", "used", "non", "third", "person",
        "plural", "singular", "sentence", "mismatch", "found", "did", "you", "mean"
    }
    sig_words = msg_words - meta

    for e in errors:
        e_lower = e.lower()
        e_words = set(re.findall(r"\b[a-zA-Z]{2,}\b", e_lower)) - meta
        # Significant word overlap
        if len(sig_words & e_words) >= 2:
            return
        # Key target pairings
        targets = [
            ("i", "go"), ("i", "am"), ("i", "have"),
            ("they", "go"), ("we", "go"), ("you", "go"),
            ("she", "goes"), ("he", "goes"), ("it", "goes"),
            ("she", "doesn't"), ("he", "doesn't"), ("it", "doesn't"),
            ("she", "don't"), ("he", "don't"), ("it", "don't"),
            ("he", "verb"), ("she", "verb"), ("it", "verb"),
            ("does", "have"), ("did", "have"),
            ("double", "negative"), ("anything", "nothing"),
            ("did", "go"), ("did", "see"), ("did", "eat")
        ]
        for t1, t2 in targets:
            if (t1 in msg_lower and t2 in msg_lower) and (t1 in e_lower and t2 in e_lower):
                return

    errors.append(msg)


def check_english_grammar(spoken: str):
    """
    Comprehensive English grammar and spelling analysis:
    1. Word validity & keyboard mashing / non-word detection
    2. Deep NLP grammar, agreement & spell check via LanguageTool API
    3. Robust local rules (subject-verb agreement, tense conflicts, double negatives)
    Never returns false 100% for invalid sentences, and prevents duplicate error bullets!
    """
    text_clean = spoken.strip()
    text_lower = text_clean.lower()
    errors = []
    corrected_text = text_clean

    # ─── 1. Word Validity & Non-Word Check ───
    word_errs = _check_word_validity(text_clean)
    errors.extend(word_errs)

    # ─── 2. LanguageTool NLP API Check ───
    lt_errs, lt_corr = check_languagetool_api(text_clean, lang_code="en-US")
    for le in lt_errs:
        prefix = le.split("(")[0].strip()
        if not any(prefix in e for e in errors):
            errors.append(le)
    if lt_corr and lt_corr != text_clean:
        corrected_text = lt_corr

    # ─── 3. Local Rule Backup Checks (With Deduplication) ───
    # Subject-Verb Agreement: I + is / are / has / goes
    if re.search(r"\bi\s+is\b", text_lower):
        _add_error_if_not_duplicate("Subject-verb agreement: Use 'I am' instead of 'I is'.", errors)
        corrected_text = re.sub(r"\bi\s+is\b", "I am", corrected_text, flags=re.IGNORECASE)
    if re.search(r"\bi\s+are\b", text_lower):
        _add_error_if_not_duplicate("Subject-verb agreement: Use 'I am' instead of 'I are'.", errors)
        corrected_text = re.sub(r"\bi\s+are\b", "I am", corrected_text, flags=re.IGNORECASE)
    if re.search(r"\bi\s+has\b", text_lower):
        _add_error_if_not_duplicate("Subject-verb agreement: Use 'I have' instead of 'I has'.", errors)
        corrected_text = re.sub(r"\bi\s+has\b", "I have", corrected_text, flags=re.IGNORECASE)
    if re.search(r"\bi\s+goes\b", text_lower):
        _add_error_if_not_duplicate("Subject-verb agreement: Use 'I go' instead of 'I goes'.", errors)
        corrected_text = re.sub(r"\bi\s+goes\b", "I go", corrected_text, flags=re.IGNORECASE)

    # Third-person singular: he/she/it + don't / have / are / were
    for sub in ["he", "she", "it"]:
        if re.search(rf"\b{sub}\s+don't\b", text_lower):
            _add_error_if_not_duplicate(f"Subject-verb agreement: Use '{sub.capitalize()} doesn't' instead of '{sub} don't'.", errors)
            corrected_text = re.sub(rf"\b{sub}\s+don't\b", f"{sub} doesn't", corrected_text, flags=re.IGNORECASE)
        if re.search(rf"\b{sub}\s+have\b", text_lower):
            _add_error_if_not_duplicate(f"Subject-verb agreement: Use '{sub.capitalize()} has' instead of '{sub} have'.", errors)
            corrected_text = re.sub(rf"\b{sub}\s+have\b", f"{sub} has", corrected_text, flags=re.IGNORECASE)
        if re.search(rf"\b{sub}\s+are\b", text_lower):
            _add_error_if_not_duplicate(f"Subject-verb agreement: Use '{sub.capitalize()} is' instead of '{sub} are'.", errors)
            corrected_text = re.sub(rf"\b{sub}\s+are\b", f"{sub} is", corrected_text, flags=re.IGNORECASE)
        # Missing 3rd person singular 's' (e.g. 'she go', 'he eat')
        base_3rd = [("go", "goes"), ("eat", "eats"), ("run", "runs"), ("see", "sees"), ("come", "comes"), ("take", "takes"), ("make", "makes"), ("think", "thinks")]
        for bv, sv in base_3rd:
            if re.search(rf"\b{sub}\s+{bv}\b", text_lower):
                _add_error_if_not_duplicate(f"Subject-verb agreement: Third-person singular '{sub}' requires '{sv}', not '{bv}'.", errors)
                corrected_text = re.sub(rf"\b{sub}\s+{bv}\b", f"{sub} {sv}", corrected_text, flags=re.IGNORECASE)

    # Plural subjects: they/we/you + is / was / has / goes
    for sub in ["they", "we", "you"]:
        if re.search(rf"\b{sub}\s+is\b", text_lower):
            _add_error_if_not_duplicate(f"Subject-verb agreement: Use '{sub.capitalize()} are' instead of '{sub} is'.", errors)
            corrected_text = re.sub(rf"\b{sub}\s+is\b", f"{sub} are", corrected_text, flags=re.IGNORECASE)
        if sub in ["they", "we"] and re.search(rf"\b{sub}\s+was\b", text_lower):
            _add_error_if_not_duplicate(f"Subject-verb agreement: Use '{sub.capitalize()} were' instead of '{sub} was'.", errors)
            corrected_text = re.sub(rf"\b{sub}\s+was\b", f"{sub} were", corrected_text, flags=re.IGNORECASE)
        if re.search(rf"\b{sub}\s+goes\b", text_lower):
            _add_error_if_not_duplicate(f"Subject-verb agreement: Use base verb 'go' with '{sub}' instead of 'goes'.", errors)
            corrected_text = re.sub(rf"\b{sub}\s+goes\b", f"{sub} go", corrected_text, flags=re.IGNORECASE)

    # Auxiliary verb error: does/did he has
    if re.search(r"\bdoes\s+(he|she|it)\s+has\b", text_lower):
        _add_error_if_not_duplicate("Auxiliary verb error: Use base verb 'have' with 'does' (e.g. 'Does he have').", errors)
        corrected_text = re.sub(r"\bdoes\s+(he|she|it)\s+has\b", r"does \1 have", corrected_text, flags=re.IGNORECASE)

    # Tense conflicts
    past_markers = ["yesterday", "last night", "last week", "last year", "last month", "ago", "previously"]
    has_past_marker = any(m in text_lower for m in past_markers)
    past_marker_word = next((m for m in past_markers if m in text_lower), "yesterday")
    present_to_past = {
        "go": "went", "goes": "went", "eat": "ate", "eats": "ate", "see": "saw", "sees": "saw",
        "buy": "bought", "buys": "bought", "do": "did", "does": "did", "take": "took", "takes": "took",
        "come": "came", "comes": "came", "make": "made", "makes": "made", "think": "thought", "thinks": "thought",
        "run": "ran", "runs": "ran", "write": "wrote", "writes": "wrote", "speak": "spoke", "speaks": "spoke"
    }
    if has_past_marker:
        for psub in ["i", "you", "we", "they", "he", "she", "it"]:
            for base_v, past_v in present_to_past.items():
                pat = rf"\b{psub}\s+{base_v}\b"
                if re.search(pat, text_lower):
                    desc = f"Tense conflict: '{psub.capitalize()} {base_v}' used with past time marker '{past_marker_word}'. Use '{psub.capitalize()} {past_v}'."
                    _add_error_if_not_duplicate(desc, errors)
                    corrected_text = re.sub(pat, f"{psub} {past_v}", corrected_text, flags=re.IGNORECASE)

    future_markers = ["tomorrow", "next week", "next month", "next year", "in the future", "soon"]
    if any(m in text_lower for m in future_markers):
        if re.search(r"\b(went|ate|saw|bought|did|came|took|made|ran)\b", text_lower):
            desc = "Tense conflict: Past tense verb used with future time marker. Use future tense ('will go / will eat')."
            _add_error_if_not_duplicate(desc, errors)

    # Double past tense
    double_pasts = [("went", "go"), ("saw", "see"), ("ate", "eat"), ("came", "come"), ("bought", "buy")]
    for dp_v, base_v in double_pasts:
        if re.search(rf"\bdid\s+{dp_v}\b", text_lower):
            desc = f"Double past tense error: Use 'did {base_v}' instead of 'did {dp_v}'."
            _add_error_if_not_duplicate(desc, errors)
            corrected_text = re.sub(rf"\bdid\s+{dp_v}\b", f"did {base_v}", corrected_text, flags=re.IGNORECASE)

    # Double negatives
    if re.search(r"\b(don't|doesn't|didn't)\s+know\s+nothing\b", text_lower):
        desc = "Double negative: Use 'anything' instead of 'nothing' (e.g. 'doesn't know anything')."
        _add_error_if_not_duplicate(desc, errors)
        corrected_text = re.sub(r"\b(don't|doesn't|didn't)\s+know\s+nothing\b", r"\1 know anything", corrected_text, flags=re.IGNORECASE)

    # Pronoun case error
    if re.search(r"\bme\s+(want|like|am|is|have|go|went)\b", text_lower):
        desc = "Pronoun case error: Use subject pronoun 'I' instead of object pronoun 'me'."
        _add_error_if_not_duplicate(desc, errors)
        corrected_text = re.sub(r"\bme\s+(want|like|am|is|have|go|went)\b", r"I \1", corrected_text, flags=re.IGNORECASE)

    # Article errors
    if re.search(r"\ba\s+([aeio]\w+)\b", text_lower):
        m = re.search(r"\ba\s+([aeio]\w+)\b", text_lower)
        if m and m.group(1) not in ["one", "once"]:
            desc = f"Article error: Use 'an' before vowel sound ('an {m.group(1)}')."
            _add_error_if_not_duplicate(desc, errors)
            corrected_text = re.sub(r"\ba\s+([aeio]\w+)\b", r"an \1", corrected_text, flags=re.IGNORECASE)

    clean_corr = corrected_text.strip()
    if clean_corr and not clean_corr[0].isupper():
        clean_corr = clean_corr[0].upper() + clean_corr[1:]
    if clean_corr and not clean_corr.endswith((".", "!", "?")):
        clean_corr += "."

    if errors:
        score = max(20, min(80, 100 - (len(errors) * 18)))
        tips = "💡 <b>Grammar Tip:</b> Review the flagged grammatical corrections above and practice the suggested phrasing."
    else:
        score = 100
        tips = "💡 <b>Fluency Tip:</b> 100% Flawless grammar and natural sentence structure! Keep up the great work."

    return errors, clean_corr, tips, score


def evaluate_grammar_with_ai(text: str, coach_lang: str, api_key: str, provider: str = "Google Gemini", ref: str = "") -> tuple:
    """
    Evaluates grammar, agreement, tense, and pronunciation accuracy dynamically via AI API.
    Supports Google Gemini, Groq Cloud (Llama 3.3), and OpenAI REST endpoints without requiring external SDKs.
    Returns: (errors: list, clean_corr: str, tips: str, score: int) or None on fallback.
    """
    if not api_key or not api_key.strip():
        return None

    clean_key = api_key.strip()
    ref_clause = f"\nTarget reference phrase to match: '{ref}'\nPlease verify whether the user's sentence matches this target reference and check for pronunciation/word accuracy." if ref else ""

    prompt = (
        f"You are an expert multilingual linguist, grammar checker, and pronunciation coach.\n"
        f"Analyze this input sentence in {coach_lang}: '{text}'.{ref_clause}\n"
        f"Evaluate the input for:\n"
        f"1. Grammatical accuracy (subject-verb agreement, verb tenses, word order, prepositions).\n"
        f"2. Spelling, punctuation, and natural phrasing.\n"
        f"3. Alignment with the target reference phrase (if provided above).\n\n"
        f"Respond ONLY with a valid JSON object with these exact keys:\n"
        f"{{\n"
        f'  "score": <integer from 0 to 100 representing accuracy and grammatical correctness>,\n'
        f'  "errors": [<array of string bullet points describing specific mistakes found, or empty array [] if 100% correct>],\n'
        f'  "clean_corr": "<the complete grammatically correct sentence in {coach_lang}, or the original input if already correct>",\n'
        f'  "tips": "<concise coaching advice explaining how to improve or praising native fluency>"\n'
        f"}}\n"
        f"Do not output markdown code fences or any text outside the JSON."
    )

    try:
        # 1. Google Gemini REST API
        if "gemini" in provider.lower():
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(text_out)
                score = int(parsed.get("score", 85))
                errors = list(parsed.get("errors", []))
                clean_corr = str(parsed.get("clean_corr", text)).strip()
                tips = str(parsed.get("tips", ""))
                return errors, clean_corr, tips, score

        # 2. Groq Cloud or OpenAI Compatible Chat API
        elif "groq" in provider.lower() or "openai" in provider.lower():
            if "groq" in provider.lower():
                url = "https://api.groq.com/openai/v1/chat/completions"
                model_name = "llama-3.3-70b-versatile"
            else:
                url = "https://api.openai.com/v1/chat/completions"
                model_name = "gpt-4o-mini"

            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are an expert multilingual linguist and speech coach. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {clean_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_out = data["choices"][0]["message"]["content"].strip()
                parsed = json.loads(text_out)
                score = int(parsed.get("score", 85))
                errors = list(parsed.get("errors", []))
                clean_corr = str(parsed.get("clean_corr", text)).strip()
                tips = str(parsed.get("tips", ""))
                return errors, clean_corr, tips, score

    except Exception as e:
        print(f"[evaluate_grammar_with_ai] API Notice ({provider}): {e}")
        return None

    return None


def evaluate_grammar_only(text: str, coach_lang: str, LANGUAGES: dict):
    """
    Evaluates pure grammar, agreement, and fluency of a sentence.
    Uses AI API (Gemini / Groq / OpenAI) if configured, with zero-downtime fallback to LanguageTool & native engines.
    """
    if not text or not text.strip():
        return ["Empty input. Please enter a valid sentence."], "", "💡 Please enter or speak a sentence.", 0

    clean_text = text.strip()
    lang_info = LANGUAGES.get(coach_lang, {}) if LANGUAGES else {}
    lang_code = lang_info.get("code", "en")

    # 1. AI API Evaluation (Dynamic LLM Linguistic Evaluation)
    ai_key = st.session_state.get("ai_coach_api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    ai_provider = st.session_state.get("coach_ai_provider_sel", "Google Gemini")
    if ai_key:
        ai_res = evaluate_grammar_with_ai(clean_text, coach_lang, ai_key, provider=ai_provider)
        if ai_res is not None:
            return ai_res

    # 2. Indian language person-agreement checks (Telugu, Tamil)
    p_check = check_person_agreement(clean_text)
    if p_check:
        return p_check

    # 3. Hindi check
    if coach_lang == "Hindi" or lang_code == "hi" or any("\u0900" <= c <= "\u097f" for c in clean_text):
        hi_check = check_hindi_grammar(clean_text)
        if hi_check:
            return hi_check
        w_errs = _check_word_validity(clean_text)
        if w_errs:
            return w_errs, clean_text, "💡 <b>Hindi Tip:</b> कृपया सही वर्तनी और शब्दों का उपयोग करें।", 40
        return [], clean_text, "💡 <b>Hindi Fluency:</b> 100% Flawless Hindi grammar and natural structure!", 100

    # 4. English check
    if coach_lang == "English" or lang_code == "en":
        return check_english_grammar(clean_text)

    # 5. Multilingual check for languages natively supported by LanguageTool
    lt_supported_codes = {
        "es": "es", "fr": "fr", "de": "de-DE", "it": "it", "pt": "pt-PT",
        "ru": "ru-RU", "zh": "zh-CN", "ja": "ja-JP", "ar": "ar", "pl": "pl-PL",
        "nl": "nl", "el": "el-GR", "sv": "sv"
    }
    lt_code = lt_supported_codes.get(lang_code)
    if lt_code:
        w_errs = _check_word_validity(clean_text)
        lt_errs, lt_corr = check_languagetool_api(clean_text, lt_code)
        all_errs = list(w_errs)
        for le in lt_errs:
            if not any(le.split("(")[0].strip() in e for e in all_errs):
                all_errs.append(le)
        if all_errs:
            score = max(30, min(80, 100 - (len(all_errs) * 18)))
            return all_errs, lt_corr, f"💡 <b>Grammar Tip ({coach_lang}):</b> Review grammatical agreement and suggestions in {coach_lang}.", score
        else:
            return [], clean_text, f"💡 <b>Fluency Tip ({coach_lang}):</b> 100% Flawless grammar and phrasing in {coach_lang}!", 100

    # 6. General multilingual check via English pivot
    w_errs = _check_word_validity(clean_text)
    if w_errs:
        return w_errs, clean_text, f"💡 <b>Spelling Tip:</b> Check spelling of input words in {coach_lang}.", 40

    try:
        en_trans = safe_translate(clean_text, source_lang=lang_code, target_lang="en")
        en_errors, _, _, _ = check_english_grammar(en_trans)
        if en_errors:
            score = max(40, min(80, 100 - len(en_errors) * 15))
            errors = [f"Grammatical/Structural issue in {coach_lang}: '{clean_text}'."] + en_errors[:2]
            tips = f"💡 <b>Grammar Tip ({coach_lang}):</b> Review grammatical agreement and phrasing in {coach_lang}."
            return errors, clean_text, tips, score
        else:
            return [], clean_text, f"💡 <b>Fluency Tip ({coach_lang}):</b> 100% Flawless grammar and phrasing in {coach_lang}!", 100
    except Exception:
        return [], clean_text, f"💡 <b>Fluency Tip ({coach_lang}):</b> Natural phrasing in {coach_lang}!", 100


def evaluate_accent_match(spoken: str, ref: str, coach_lang: str, LANGUAGES: dict):
    """
    Compares spoken/typed text against a Target Reference Phrase for Pronunciation & Word Accuracy.
    Uses AI API if configured, with intelligent lexical similarity fallback.
    Only called when the user explicitly practices a target phrase in Tab 2.
    """
    if not ref or not ref.strip():
        return evaluate_grammar_only(spoken, coach_lang, LANGUAGES)

    clean_spoken = spoken.strip()
    clean_ref = ref.strip()

    # 1. AI API Evaluation with reference comparison
    ai_key = st.session_state.get("ai_coach_api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    ai_provider = st.session_state.get("coach_ai_provider_sel", "Google Gemini")
    if ai_key:
        ai_res = evaluate_grammar_with_ai(clean_spoken, coach_lang, ai_key, provider=ai_provider, ref=clean_ref)
        if ai_res is not None:
            return ai_res

    # 2. Lexical similarity matching fallback
    sim = _compute_similarity(clean_ref, clean_spoken)
    errors, clean_corr, tips, grammar_score = evaluate_grammar_only(clean_spoken, coach_lang, LANGUAGES)

    # High match (>= 85%)
    if sim >= 0.85:
        if errors:
            score = min(75, grammar_score)
            return errors, clean_ref, tips, score
        return [], clean_ref, "🎯 <b>Perfect Accuracy:</b> 100% Flawless pronunciation, wording, and native accuracy!", 100

    # Partial match (50% - 84%)
    elif sim >= 0.50:
        norm_r = _normalize_text(clean_ref)
        norm_s = _normalize_text(clean_spoken)
        missing = set(norm_r.split()) - set(norm_s.split())
        score = max(35, min(70, min(int(sim * 100), grammar_score)))
        err_list = list(errors)
        if missing:
            err_list.insert(0, f"⚠️ Missing words from target phrase: {', '.join(list(missing)[:4])}")
        return err_list, clean_ref, "💡 <b>Accent Tip:</b> Practice reading the full target phrase slowly to capture every word.", score

    # Low match / Wrong answer (< 50%)
    else:
        score = max(15, min(40, int(sim * 100)))
        err_list = [
            f"❌ Content Mismatch: What you entered does not match the target reference phrase.",
            f"• Expected Phrase: '{clean_ref}'",
            f"• Received Input: '{clean_spoken}'"
        ]
        return err_list, clean_ref, f"💡 <b>Target Practice Tip:</b> Listen to the native pronunciation and repeat: <b>'{clean_ref}'</b>.", score


# ════════════════════════════════════════════════════════════
# 4. STREAMLINED, UNDERSTANDABLE UI
# ════════════════════════════════════════════════════════════
def render_accent_coach_module(LANGUAGES: dict):
    """
    Clean, Understandable AI Accent & Translation Coach:
    - Tab 1: 🌐 Text-to-Text Translation & ElevenLabs Neural Voice Synthesis
    - Tab 2: 🎯 Pronunciation & Native Accent Coach
    """
    st.markdown("<div class='glow-title' style='font-size:28px;'>🎯 AI ACCENT & TRANSLATION COACH</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle-anim' style='font-size:13px;'>Fast Neural Translation · ElevenLabs High-Fidelity Voice Synthesis · Real-Time Accent & Grammar Scoring</div>", unsafe_allow_html=True)
    st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)

    # ─── Top ElevenLabs Voice Persona Bar ───
    api_key_override = st.session_state.get("elevenlabs_api_key") or os.getenv("ELEVENLABS_API_KEY")
    client = ElevenLabsClient(api_key_override)
    is_eleven_ready = client.is_configured()

    ai_key = st.session_state.get("ai_coach_api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    ai_provider = st.session_state.get("coach_ai_provider_sel", "Google Gemini")

    # Dynamically fetch voices from ElevenLabs API using user's API key
    voice_personas = _get_dynamic_elevenlabs_voices(client)

    col_bar1, col_bar2 = st.columns([1.5, 1.2])
    with col_bar1:
        if is_eleven_ready:
            ai_tag = f" · <span style='color:#a855f7;'>🧠 AI: {ai_provider}</span>" if ai_key else " · <span style='color:#00f2fe;'>⚡ Hybrid: Active</span>"
            bar_html = (
                f"<div style='background:rgba(0,255,136,0.08); border:1px solid #00ff88; border-radius:10px; padding:8px 14px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between;'>"
                f"<span style='color:#00ff88; font-size:12px; font-weight:800; font-family:Orbitron,sans-serif;'>⚡ ELEVENLABS API: ONLINE ({len(voice_personas)} Voices)</span>"
                f"<span style='color:#94a3b8; font-size:11px;'>Model: <code style='color:#00f2fe;'>eleven_multilingual_v2</code>{ai_tag}</span>"
                f"</div>"
            )
            st.markdown(bar_html, unsafe_allow_html=True)
        else:
            bar_html = (
                "<div style='background:rgba(234,179,8,0.08); border:1px solid #eab308; border-radius:10px; padding:8px 14px; margin-bottom:10px;'>"
                "<span style='color:#eab308; font-size:11px; font-weight:600;'>⚪ ElevenLabs API Offline · Configure your API key below or in .env</span>"
                "</div>"
            )
            st.markdown(bar_html, unsafe_allow_html=True)

    with col_bar2:
        selected_persona_label = st.selectbox(
            "🎙️ Select ElevenLabs Voice Persona:",
            list(voice_personas.keys()),
            index=0,
            key="coach_v_persona"
        )
        current_voice_id = voice_personas.get(selected_persona_label, "EXAVITQu4vr4xnSDxMaL")

    # ─── API KEY CONFIGURATION DRAWER ───
    with st.expander("🔑 API Key & Engine Settings (ElevenLabs & AI Linguistic Coach)", expanded=False):
        col_k1, col_k2, col_k3 = st.columns([1.2, 1.2, 0.8])
        with col_k1:
            cur_eleven_key = st.session_state.get("elevenlabs_api_key") or os.getenv("ELEVENLABS_API_KEY", "")
            new_eleven_key = st.text_input(
                "⚡ ElevenLabs API Key:",
                value=cur_eleven_key,
                type="password",
                placeholder="sk_...",
                help="Powers dynamic voice fetching from your ElevenLabs account and high-fidelity neural speech."
            )
            if new_eleven_key != cur_eleven_key:
                st.session_state["elevenlabs_api_key"] = new_eleven_key.strip()
                os.environ["ELEVENLABS_API_KEY"] = new_eleven_key.strip()

        with col_k2:
            provider_list = ["Google Gemini", "Groq Cloud (Llama 3.3)", "OpenAI (GPT-4o)"]
            cur_p_idx = provider_list.index(ai_provider) if ai_provider in provider_list else 0
            sel_provider = st.selectbox(
                "🧠 AI Linguistic Provider:",
                provider_list,
                index=cur_p_idx,
                key="coach_ai_provider_sel"
            )
            cur_ai_key = st.session_state.get("ai_coach_api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY", "")
            new_ai_key = st.text_input(
                f"🔑 {sel_provider} API Key:",
                value=cur_ai_key,
                type="password",
                placeholder="AI API Key (Optional)...",
                help="Dynamically evaluates grammatical structures, mistakes, corrections, and pronunciation across any language."
            )
            if new_ai_key != cur_ai_key:
                st.session_state["ai_coach_api_key"] = new_ai_key.strip()

        with col_k3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("💾 Apply & Refresh", key="btn_apply_coach_keys", use_container_width=True):
                st.rerun()

        st.caption("🔒 *API keys are securely used in memory for direct API requests. When no AI key is entered, the system automatically uses LanguageTool and local linguistic engines.*")

    # ─── TWO CLEAN, UNDERSTANDABLE TABS ───
    tab_trans, tab_accent = st.tabs([
        "🌐 1. Text-to-Text Translation & ElevenLabs Voice",
        "🎯 2. Accent & Pronunciation Coach"
    ])

    # ════════════════════════════════════════════════════════
    # TAB 1: TEXT-TO-TEXT TRANSLATION + ELEVENLABS AUDIO
    # ════════════════════════════════════════════════════════
    with tab_trans:
        st.markdown("#### 🌐 Fast Neural Text Translation & ElevenLabs Voice")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            in_lang = st.selectbox("1️⃣ Input Language:", list(LANGUAGES.keys()), index=0, key="tt_in_lang_tab1")
            in_code = LANGUAGES[in_lang]["code"]
        with col_t2:
            out_lang = st.selectbox("2️⃣ Output Target Language:", list(LANGUAGES.keys()), index=1, key="tt_out_lang_tab1")
            out_code = LANGUAGES[out_lang]["code"]

        input_text = st.text_area(
            "Enter text to translate & evaluate:",
            value=st.session_state.get("last_coach_tt_input", "Yesterday I went to the market and bought fresh vegetables."),
            height=100,
            key="coach_tt_text_area",
            placeholder="Type any sentence here to translate into target language and evaluate grammar..."
        )

        if st.button("🚀 Translate & Speak (ElevenLabs Neural Voice)", type="primary", key="btn_run_tt_trans"):
            if not input_text.strip():
                st.warning("Please enter text to translate.")
            else:
                with st.spinner("Translating text & synthesizing ElevenLabs speech..."):
                    # 1. Translate
                    if in_lang == out_lang:
                        translated = input_text.strip()
                    else:
                        translated = safe_translate(input_text.strip(), source_lang=in_code, target_lang=out_code)

                    # 2. Synthesize ElevenLabs Audio
                    audio_bytes, engine_name = _synthesize_elevenlabs_voice(translated, out_code, current_voice_id)

                    # 3. Evaluate Grammar of input text (Never compares to arbitrary preset)
                    errors, clean_corr, tips, score = evaluate_grammar_only(input_text.strip(), in_lang, LANGUAGES)

                    # Save to session state
                    st.session_state["coach_tt_result"] = {
                        "input_text": input_text.strip(),
                        "translated": translated,
                        "in_lang": in_lang,
                        "out_lang": out_lang,
                        "audio_bytes": audio_bytes,
                        "engine_name": engine_name,
                        "score": score,
                        "errors": errors,
                        "clean_corr": clean_corr,
                        "tips": tips
                    }

        # Render Tab 1 Results if ready
        if "coach_tt_result" in st.session_state and st.session_state["coach_tt_result"]:
            res = st.session_state["coach_tt_result"]

            st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)
            col_res_a, col_res_b = st.columns(2)

            with col_res_a:
                card_orig = (
                    f"<div style='background:rgba(8, 14, 30, 0.85); border:1px solid rgba(0,242,254,0.3); border-radius:14px; padding:18px; margin-bottom:12px;'>"
                    f"<div style='color:#00f2fe; font-family:Orbitron,sans-serif; font-size:12px; font-weight:800; margin-bottom:6px;'>📝 ORIGINAL ({res['in_lang']})</div>"
                    f"<div style='color:#ffffff; font-size:15px; font-weight:500;'>{res['input_text']}</div>"
                    f"</div>"
                )
                st.markdown(card_orig, unsafe_allow_html=True)

            with col_res_b:
                card_trans = (
                    f"<div style='background:rgba(112, 0, 255, 0.12); border:1px solid #a855f7; border-radius:14px; padding:18px; margin-bottom:12px;'>"
                    f"<div style='color:#c084fc; font-family:Orbitron,sans-serif; font-size:12px; font-weight:800; margin-bottom:6px;'>✨ TRANSLATED ({res['out_lang']})</div>"
                    f"<div style='color:#00f2fe; font-size:16px; font-weight:600;'>{res['translated']}</div>"
                    f"</div>"
                )
                st.markdown(card_trans, unsafe_allow_html=True)

            # Audio Player
            if res["audio_bytes"]:
                st.markdown(f"**🔊 Native ElevenLabs Audio Preview:** `{res['engine_name']}`")
                st.audio(res["audio_bytes"], format="audio/mp3", autoplay=True)

            # Accuracy & Grammar Breakdown Card
            _render_score_card(res["score"], res["errors"], res["clean_corr"], res["tips"], res["in_lang"])

    # ════════════════════════════════════════════════════════
    # TAB 2: ACCENT & PRONUNCIATION COACH (REPEAT & MATCH)
    # ════════════════════════════════════════════════════════
    with tab_accent:
        st.markdown("#### 🎯 Practice Native Pronunciation & Speech Accuracy")

        preset_phrases = {
            "English": "Yesterday I went to the market and bought fresh vegetables.",
            "Tamil": "நாளைக்கு நான் சென்னைக்கு போவேன்.",
            "Hindi": "आज मैं एक नई भाषा सीख रहा हूँ।",
            "Telugu": "రేపు నేను ఊరికి వెళ్తాను.",
            "Kannada": "ನಾಳೆ ನಾನು ಶಾಲೆಗೆ ಹೋಗುತ್ತೇನೆ.",
            "Malayalam": "ನಾಳೆ ഞാൻ അവിടെ പോകും.",
            "French": "Aujourd'hui je vais apprendre le français avec enthousiasme.",
            "Spanish": "Me gustaría practicar mi pronunciación en español todos los días.",
            "German": "Ich möchte meine Deutschkenntnisse jeden Tag verbessern.",
            "Japanese": "今日は新しい言語を楽しく学んでいます。",
            "Korean": "오늘 나는 새로운 언어를 열심히 배우고 있습니다.",
            "Chinese": "今天我正在努力学习一门新的语言。",
            "Arabic": "اليوم أتعلم لغة جديدة بحماس شديد.",
            "Russian": "Сегодня я с удовольствием изучаю новый язык.",
            "Urdu": "آज میں ایک نئی زبان سیکھ رہا ہوں۔",
            "Bengali": "আজ আমি একটি নতুন ভাষা শিখছি।",
            "Punjabi": "ਅੱਜ ਮੈਂ ਇੱਕ ਨਵੀਂ ਭਾਸ਼ਾ ਸਿੱਖ ਰਿਹਾ ਹਾਂ।"
        }

        col_acc1, col_acc2 = st.columns([1, 2])
        with col_acc1:
            accent_lang = st.selectbox("Select Target Language to Practice:", list(LANGUAGES.keys()), index=0, key="accent_lang_sel")
            accent_code = LANGUAGES[accent_lang]["code"]
            speech_code = LANGUAGES[accent_lang]["speech_code"]

        default_phrase = preset_phrases.get(accent_lang, "Hello! How are you doing today?")

        with col_acc2:
            target_phrase = st.text_area(
                f"Target Practice Phrase ({accent_lang}):",
                value=st.session_state.get(f"target_ref_{accent_lang}", default_phrase),
                height=75,
                key=f"target_ref_input_{accent_lang}"
            )

        # Listen to Reference Native Speech
        if st.button("🔊 Listen to Reference Native Pronunciation (ElevenLabs API)", key="btn_listen_ref_accent"):
            with st.spinner("Synthesizing native reference audio via ElevenLabs..."):
                audio_bytes, engine_label = _synthesize_elevenlabs_voice(target_phrase, accent_code, current_voice_id)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                    st.caption(f"✨ Native Audio Engine: **{engine_label}**")

        st.markdown("---")
        st.markdown("##### 🎙️ Step 2: Speak or Type Your Practice Sentence")
        method = st.radio("Input Method:", ["🎙️ Record Live Speech", "⌨️ Type Spoken Phrase"], horizontal=True, key="acc_input_method")

        user_input_spoken = ""
        if method == "🎙️ Record Live Speech":
            rec_dur = st.slider("Recording Duration (seconds):", min_value=3, max_value=12, value=6, key="coach_rec_dur")
            if st.button("🔴 Start Live Practice Recording", key="btn_start_acc_rec", type="primary"):
                try:
                    with st.spinner(f"Recording ({rec_dur}s)... Read the target phrase clearly now!"):
                        audio_data = sd.rec(int(rec_dur * 16000), samplerate=16000, channels=1, dtype='int16')
                        sd.wait()
                        os.makedirs("data/temp", exist_ok=True)
                        wav_path = f"data/temp/acc_rec_{int(time.time())}.wav"
                        sf.write(wav_path, audio_data, 16000)

                    recognizer = sr.Recognizer()
                    with sr.AudioFile(wav_path) as source:
                        aud = recognizer.record(source)
                        user_input_spoken = recognizer.recognize_google(aud, language=speech_code)
                    st.session_state["coach_accent_spoken"] = user_input_spoken
                except sr.UnknownValueError:
                    st.error("❌ Audio unclear or speech unrecognized. Speak clearly and record again.")
                except Exception as rec_err:
                    st.error(f"❌ Recording / STT Error: {rec_err}")

            user_input_spoken = st.session_state.get("coach_accent_spoken", "")
            if user_input_spoken:
                st.info(f"🗣️ **Recognized Speech:** `{user_input_spoken}`")

        else:
            user_input_spoken = st.text_area(
                "Type what you spoke or want to evaluate:",
                value=st.session_state.get("coach_accent_spoken", ""),
                placeholder=f"Type your answer in {accent_lang}...",
                height=80,
                key="manual_acc_input"
            )

        if st.button("⚡ Evaluate Pronunciation & Accuracy", type="primary", key="btn_eval_accent_now"):
            if not user_input_spoken.strip():
                st.warning("Please record speech or enter text first.")
            else:
                errors, clean_corr, tips, score = evaluate_accent_match(user_input_spoken.strip(), target_phrase.strip(), accent_lang, LANGUAGES)
                st.session_state["coach_accent_result"] = {
                    "spoken": user_input_spoken.strip(),
                    "ref": target_phrase.strip(),
                    "lang": accent_lang,
                    "score": score,
                    "errors": errors,
                    "clean_corr": clean_corr,
                    "tips": tips
                }

        # Render Tab 2 Results
        if "coach_accent_result" in st.session_state and st.session_state["coach_accent_result"]:
            res = st.session_state["coach_accent_result"]
            st.markdown("<hr class='neon-divider'>", unsafe_allow_html=True)
            col_acc_a, col_acc_b = st.columns(2)
            with col_acc_a:
                card_spoken = (
                    f"<div style='background:rgba(8, 14, 30, 0.85); border:1px solid rgba(0,242,254,0.3); border-radius:14px; padding:18px; margin-bottom:12px;'>"
                    f"<div style='color:#00f2fe; font-family:Orbitron,sans-serif; font-size:12px; font-weight:800; margin-bottom:6px;'>🗣️ WHAT YOU SAID ({res['lang']})</div>"
                    f"<div style='color:#ffffff; font-size:15px; font-weight:500;'>{res['spoken']}</div>"
                    f"</div>"
                )
                st.markdown(card_spoken, unsafe_allow_html=True)

            with col_acc_b:
                card_ref = (
                    f"<div style='background:rgba(112, 0, 255, 0.12); border:1px solid #a855f7; border-radius:14px; padding:18px; margin-bottom:12px;'>"
                    f"<div style='color:#c084fc; font-family:Orbitron,sans-serif; font-size:12px; font-weight:800; margin-bottom:6px;'>🎯 TARGET REFERENCE PHRASE</div>"
                    f"<div style='color:#00f2fe; font-size:15px; font-weight:600;'>{res['ref']}</div>"
                    f"</div>"
                )
                st.markdown(card_ref, unsafe_allow_html=True)

            _render_score_card(res["score"], res["errors"], res["clean_corr"], res["tips"], res["lang"])


# ════════════════════════════════════════════════════════
# 5. REUSABLE CLEAN SCORE CARD
# ════════════════════════════════════════════════════════
def _render_score_card(score: int, errors: list, clean_corr: str, tips: str, lang_name: str):
    """Renders sleek, understandable score card with dynamic glowing badges and corrections."""
    if score == 100:
        badge_color = "#00f2fe"  # Cyan
        badge_bg = "rgba(0, 242, 254, 0.12)"
        status_label = "🎯 PERFECT FLUENCY — 100% Flawless Grammar!"
    elif score >= 80:
        badge_color = "#00ff88"  # Green
        badge_bg = "rgba(0, 255, 136, 0.12)"
        status_label = "🎯 EXCELLENT ACCURACY — High Grammar Quality!"
    elif score >= 55:
        badge_color = "#eab308"  # Yellow
        badge_bg = "rgba(234, 179, 8, 0.12)"
        status_label = "⚠️ NEEDS IMPROVEMENT — Grammatical Corrections Detected!"
    else:
        badge_color = "#f43f5e"  # Red
        badge_bg = "rgba(244, 63, 94, 0.12)"
        status_label = "🚨 LOW ACCURACY / MISTAKE DETECTED — Correction Recommended!"

    # Header Score Bar
    score_html = (
        f"<div style='background:{badge_bg}; border:1px solid {badge_color}; border-radius:16px; padding:20px; text-align:center; margin:16px 0; box-shadow:0 0 20px {badge_color}33;'>"
        f"<div style='color:{badge_color}; font-family:Orbitron,sans-serif; font-size:36px; font-weight:900;'>{score}% ACCURACY SCORE</div>"
        f"<div style='color:#ffffff; font-family:Poppins,sans-serif; font-size:14px; font-weight:600; margin:4px 0 12px 0;'>{status_label}</div>"
        f"<div style='background:rgba(255,255,255,0.1); border-radius:8px; height:12px; width:100%; overflow:hidden;'>"
        f"<div style='background:{badge_color}; height:100%; width:{score}%; border-radius:8px; transition:width 0.8s ease;'></div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(score_html, unsafe_allow_html=True)

    col_err, col_tip = st.columns(2)
    with col_err:
        if errors:
            err_items = "".join([f"<div style='margin-bottom:6px;'>• {e}</div>" for e in errors])
            mistake_card = (
                f"<div style='background:rgba(244, 63, 94, 0.1); border:1px solid #f43f5e; border-radius:14px; padding:16px; margin-bottom:12px; min-height:100px;'>"
                f"<div style='color:#f43f5e; font-family:Orbitron,sans-serif; font-size:12px; font-weight:800; margin-bottom:8px;'>⚠️ MISTAKE EVALUATION</div>"
                f"<div style='color:#ff8090; font-size:13px; line-height:1.5;'>{err_items}</div>"
                f"</div>"
            )
            st.markdown(mistake_card, unsafe_allow_html=True)

            if clean_corr and clean_corr.strip():
                corr_card = (
                    f"<div style='padding:12px 14px; background:rgba(0,242,254,0.08); border:1px solid rgba(0,242,254,0.3); border-left:4px solid #00f2fe; border-radius:10px; margin-bottom:12px;'>"
                    f"<div style='color:#00f2fe; font-size:11px; font-weight:800; font-family:Orbitron,sans-serif; margin-bottom:4px;'>✨ SUGGESTED CORRECTION:</div>"
                    f"<div style='color:#ffffff; font-size:14px; font-weight:600;'>{clean_corr}</div>"
                    f"</div>"
                )
                st.markdown(corr_card, unsafe_allow_html=True)
        else:
            success_html = (
                f"<div style='background:rgba(0, 255, 136, 0.1); border:1px solid #00ff88; border-radius:14px; padding:16px; min-height:110px;'>"
                f"<div style='color:#00ff88; font-family:Orbitron,sans-serif; font-size:12px; font-weight:800; margin-bottom:8px;'>✅ MISTAKE EVALUATION</div>"
                f"<div style='color:#00ff88; font-size:13px; font-weight:600;'>✅ No grammatical or spelling errors detected. Sentence is natural and fluent!</div>"
                f"</div>"
            )
            st.markdown(success_html, unsafe_allow_html=True)

    with col_tip:
        advice_html = (
            f"<div style='background:rgba(8, 26, 54, 0.85); border:1px solid #38bdf8; border-radius:14px; padding:16px; min-height:110px;'>"
            f"<div style='color:#38bdf8; font-family:Orbitron,sans-serif; font-size:12px; font-weight:800; margin-bottom:8px;'>📢 AI COACH ADVICE</div>"
            f"<div style='color:#cbd5e1; font-size:13px; line-height:1.5;'>{tips}</div>"
            f"</div>"
        )
        st.markdown(advice_html, unsafe_allow_html=True)
