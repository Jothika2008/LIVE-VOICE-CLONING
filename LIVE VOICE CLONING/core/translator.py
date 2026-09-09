import logging
from typing import Dict

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    HAS_DEEP_TRANSLATOR = True
except ImportError:
    HAS_DEEP_TRANSLATOR = False

def safe_translate(text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
    """
    Multi-Engine Safe Translation with Fallback Strategy:
    1. Primary: GoogleTranslator
    2. Fallback: MyMemoryTranslator (Free, no auth needed)
    3. Safety Return: [Translation Offline] text (Zero crashes / HTTP 500 errors)
    """
    if not text or not text.strip():
        return ""
    
    # Normalize language codes (preserve Chinese zh-CN / zh-TW)
    raw_target = target_lang.strip()
    if raw_target.lower() in ["zh-cn", "zh_cn", "zh"]:
        clean_target = "zh-CN"
    elif raw_target.lower() in ["zh-tw", "zh_tw"]:
        clean_target = "zh-TW"
    elif "-" in raw_target:
        clean_target = raw_target.split("-")[0].lower()
    else:
        clean_target = raw_target.lower()

    raw_source = source_lang.strip()
    if raw_source.lower() in ["zh-cn", "zh_cn", "zh"]:
        clean_source = "zh-CN"
    elif raw_source.lower() in ["zh-tw", "zh_tw"]:
        clean_source = "zh-TW"
    elif raw_source.lower() != "auto" and "-" in raw_source:
        clean_source = raw_source.split("-")[0].lower()
    else:
        clean_source = raw_source.lower()

    # Attempt 1: GoogleTranslator (deep_translator)
    try:
        translated = GoogleTranslator(source=clean_source if clean_source != "auto" else "auto", target=clean_target).translate(text)
        if translated and "500 (Server Error)" not in str(translated) and "That’s an error" not in str(translated):
            return translated
    except Exception as e:
        logging.warning(f"GoogleTranslator failed: {e}")

    # Attempt 2: Direct Google Translate GTX Engine (High-speed, resilient fallback)
    try:
        import urllib.request
        import urllib.parse
        import json
        q_enc = urllib.parse.quote(text)
        sl = clean_source if clean_source != "auto" else "auto"
        tl = clean_target
        gtx_url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t&q={q_enc}"
        req = urllib.request.Request(gtx_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                result_parts = [chunk[0] for chunk in data[0] if chunk and chunk[0]]
                translated_gtx = "".join(result_parts).strip()
                if translated_gtx:
                    return translated_gtx
    except Exception as e:
        logging.warning(f"Google GTX API failed: {e}")

    # Attempt 3: MyMemoryTranslator Fallback (Free, No Auth Needed)
    try:
        MYMEMORY_MAP = {
            "ta": "ta-IN", "en": "en-US", "hi": "hi-IN", "fr": "fr-FR",
            "es": "es-ES", "de": "de-DE", "te": "te-IN", "kn": "kn-IN",
            "ml": "ml-IN", "ko": "ko-KR", "zh": "zh-CN", "zh-cn": "zh-CN",
            "zh-CN": "zh-CN", "ur": "ur-PK", "bn": "bn-IN", "ar": "ar-SA",
            "pa": "pa-IN", "ja": "ja-JP", "ru": "ru-RU"
        }

        mymemory_target = MYMEMORY_MAP.get(clean_target, MYMEMORY_MAP.get(target_lang, clean_target))
        mymemory_source = MYMEMORY_MAP.get(clean_source, MYMEMORY_MAP.get(source_lang, "en-US" if clean_source == "auto" else clean_source))

        translated = MyMemoryTranslator(source=mymemory_source, target=mymemory_target).translate(text)
        if translated and "500 (Server Error)" not in str(translated) and "That’s an error" not in str(translated):
            return translated
    except Exception as e:
        logging.warning(f"MyMemoryTranslator failed: {e}")

    # Attempt 3: Direct safe return if all network calls fail
    return f"[Translation Offline] {text}"

class TranslationEngine:
    """
    Multi-engine Text Translation Wrapper
    """
    SUPPORTED_LANGUAGES: Dict[str, str] = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "zh-CN": "Chinese (Simplified)",
        "ja": "Japanese",
        "ko": "Korean",
        "hi": "Hindi",
        "ar": "Arabic",
        "tr": "Turkish",
        "nl": "Dutch",
        "pl": "Polish",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "ml": "Malayalam",
        "bn": "Bengali"
    }

    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        return cls.SUPPORTED_LANGUAGES

    @classmethod
    def translate_text(cls, text: str, target_lang: str = "es", source_lang: str = "auto") -> str:
        return safe_translate(text, source_lang=source_lang, target_lang=target_lang)
