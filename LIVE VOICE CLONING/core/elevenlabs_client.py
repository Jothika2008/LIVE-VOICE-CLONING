import os
import json
import time
import requests
from typing import Optional, Dict, Any, List, Tuple

class ElevenLabsClient:
    """
    Production-grade ElevenLabs API Client.
    Supports:
    - Instant Voice Cloning (IVC)
    - Multilingual Text-to-Speech (TTS)
    - Speech-to-Speech (STS) Voice Morphing
    - Voice Library & Slot Management
    - Quota & Subscription Telemetry
    """

    BASE_URL = "https://api.elevenlabs.io/v1"
    DEFAULT_MODEL = "eleven_multilingual_v2"
    TURBO_MODEL = "eleven_turbo_v2_5"
    STS_MODEL = "eleven_multilingual_sts_v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = self._resolve_api_key(api_key)

    @staticmethod
    def _resolve_api_key(api_key: Optional[str] = None) -> str:
        """Resolves API key from parameter, environment, or .env file."""
        key = (api_key or os.getenv("ELEVENLABS_API_KEY", "")).strip()
        if not key:
            # Check current directory and parent directory for .env
            env_paths = [
                os.path.join(os.getcwd(), ".env"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
                ".env"
            ]
            for p in env_paths:
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith("ELEVENLABS_API_KEY="):
                                    key = line.split("=", 1)[1].strip()
                                    if key:
                                        os.environ["ELEVENLABS_API_KEY"] = key
                                        return key
                    except Exception:
                        pass
        return key

    def _headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        headers = {"xi-api-key": self.api_key}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def is_configured(self) -> bool:
        """Returns True if an API key looks syntactically valid."""
        return bool(self.api_key and self.api_key.startswith("sk_"))

    # ─────────────────────────────────────────────────────────────────
    # USER & SUBSCRIPTION TELEMETRY
    # ─────────────────────────────────────────────────────────────────
    def get_subscription_info(self) -> Dict[str, Any]:
        """
        Retrieves user subscription tier, character usage, voice slot counts,
        and cloning permissions.
        """
        if not self.is_configured():
            return {
                "valid": False,
                "tier": "None",
                "can_clone": False,
                "char_used": 0,
                "char_limit": 0,
                "voice_slots_used": 0,
                "voice_limit": 0,
                "message": "No ElevenLabs API key configured."
            }

        try:
            url = f"{self.BASE_URL}/user/subscription"
            res = requests.get(url, headers=self._headers(None), timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                tier = data.get("tier", "starter")
                can_clone = data.get("can_use_instant_voice_cloning", False) or tier.lower() not in ["free", "free_tier", ""]
                char_used = data.get("character_count", 0)
                char_limit = data.get("character_limit", 40000)
                voice_slots_used = data.get("voice_slots_used", 0)
                voice_limit = data.get("voice_limit", 10)
                
                return {
                    "valid": True,
                    "tier": tier.title(),
                    "can_clone": can_clone,
                    "char_used": char_used,
                    "char_limit": char_limit,
                    "voice_slots_used": voice_slots_used,
                    "voice_limit": voice_limit,
                    "status": data.get("status", "active"),
                    "currency": data.get("currency", "usd"),
                    "message": f"Active {tier.title()} Plan · {char_limit - char_used:,} chars left"
                }
            elif res.status_code == 401:
                return {"valid": False, "tier": "Unauthorized", "can_clone": False, "message": "Invalid ElevenLabs API key."}
            else:
                return {"valid": False, "tier": "Error", "can_clone": False, "message": f"API check failed ({res.status_code}): {res.text[:100]}"}
        except Exception as e:
            return {"valid": False, "tier": "Offline", "can_clone": False, "message": f"Network error: {str(e)}"}

    def get_user_info(self) -> Dict[str, Any]:
        """Retrieves user profile information."""
        try:
            url = f"{self.BASE_URL}/user"
            res = requests.get(url, headers=self._headers(None), timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
        return {}

    # ─────────────────────────────────────────────────────────────────
    # VOICE MANAGEMENT (IVC & LIBRARY)
    # ─────────────────────────────────────────────────────────────────
    def get_voices(self) -> List[Dict[str, Any]]:
        """
        Retrieves all available voices (premade and custom cloned).
        Returns enriched dicts with category, preview_url, and labels.
        """
        if not self.is_configured():
            return []

        try:
            url = f"{self.BASE_URL}/voices"
            res = requests.get(url, headers=self._headers(None), timeout=10)
            if res.status_code == 200:
                return res.json().get("voices", [])
        except Exception as e:
            print(f"[ElevenLabsClient] get_voices error: {e}")
        return []

    def get_cloned_voices(self) -> List[Dict[str, Any]]:
        """Filters down to user-created custom cloned voices."""
        voices = self.get_voices()
        return [v for v in voices if v.get("category") in ["cloned", "generated"] or "custom" in v.get("category", "")]

    def add_instant_voice_clone(
        self,
        name: str,
        audio_file_path: str,
        description: str = "Authentic Live Voice Clone"
    ) -> Dict[str, Any]:
        """
        Instant Voice Cloning (IVC):
        Uploads speaker audio sample and creates a permanent custom voice in ElevenLabs.
        """
        if not self.is_configured():
            raise RuntimeError("ElevenLabs API Key is not configured. Add it in Settings or .env.")

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Reference audio file not found: {audio_file_path}")

        url = f"{self.BASE_URL}/voices/add"
        filename = os.path.basename(audio_file_path)
        
        mime = "audio/wav"
        if filename.endswith(".mp3"):
            mime = "audio/mpeg"
        elif filename.endswith(".m4a"):
            mime = "audio/mp4"

        with open(audio_file_path, "rb") as f_audio:
            files = [("files", (filename, f_audio, mime))]
            data = {
                "name": name.strip(),
                "description": description.strip()
            }
            res = requests.post(url, headers=self._headers(None), files=files, data=data, timeout=30)

        if res.status_code == 200:
            result = res.json()
            voice_id = result.get("voice_id")
            if not voice_id:
                raise RuntimeError("ElevenLabs added voice but returned no voice_id.")
            return {"success": True, "voice_id": voice_id, "name": name}
        else:
            error_msg = res.text
            try:
                err_data = res.json()
                detail = err_data.get("detail", {})
                if isinstance(detail, dict):
                    error_msg = detail.get("message", res.text)
                    code = detail.get("code", "")
                    if "voice_limit" in code or "slots" in error_msg.lower():
                        error_msg = "Voice slot limit reached (10/10). Please delete an existing cloned voice in the Voice Library to add a new one."
                    elif "subscription" in code or "paid_plan" in code:
                        error_msg = "Instant Voice Cloning requires a Starter (or higher) plan. Check your subscription."
                elif isinstance(detail, str):
                    error_msg = detail
            except Exception:
                pass
            raise RuntimeError(f"ElevenLabs IVC Error ({res.status_code}): {error_msg}")

    def delete_voice(self, voice_id: str) -> bool:
        """Deletes a custom cloned voice to reclaim a voice slot."""
        if not self.is_configured() or not voice_id:
            return False

        try:
            url = f"{self.BASE_URL}/voices/{voice_id}"
            res = requests.delete(url, headers=self._headers(None), timeout=10)
            return res.status_code == 200
        except Exception as e:
            print(f"[ElevenLabsClient] delete_voice error: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    # TEXT-TO-SPEECH (TTS)
    # ─────────────────────────────────────────────────────────────────
    def text_to_speech(
        self,
        text: str,
        voice_id: str,
        model_id: str = DEFAULT_MODEL,
        stability: float = 0.50,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> bytes:
        """
        Synthesizes text using ElevenLabs neural voice model.
        Returns raw audio/mpeg bytes.
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")

        if not self.is_configured():
            raise RuntimeError("ElevenLabs API Key is missing. Please set it in Settings.")

        if not voice_id:
            # Fallback to premade Sarah if no voice_id provided
            voice_id = "EXAVITQu4vr4xnSDxMaL"

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        payload = {
            "text": text.strip(),
            "model_id": model_id or self.DEFAULT_MODEL,
            "voice_settings": {
                "stability": float(np_clip(stability, 0.0, 1.0)),
                "similarity_boost": float(np_clip(similarity_boost, 0.0, 1.0)),
                "style": float(np_clip(style, 0.0, 1.0)),
                "use_speaker_boost": bool(use_speaker_boost)
            }
        }

        res = requests.post(url, headers=self._headers("application/json"), json=payload, timeout=30)
        
        if res.status_code == 200:
            return res.content
        else:
            err_msg = res.text
            try:
                detail = res.json().get("detail", {})
                if isinstance(detail, dict):
                    err_msg = detail.get("message", res.text)
                elif isinstance(detail, str):
                    err_msg = detail
            except Exception:
                pass
            raise RuntimeError(f"ElevenLabs TTS failed ({res.status_code}): {err_msg}")

    # ─────────────────────────────────────────────────────────────────
    # SPEECH-TO-SPEECH (STS) VOICE MORPHING
    # ─────────────────────────────────────────────────────────────────
    def speech_to_speech(
        self,
        audio_file_path: str,
        voice_id: str,
        model_id: str = STS_MODEL,
        stability: float = 0.50,
        similarity_boost: float = 0.80
    ) -> bytes:
        """
        Speech-to-Speech (STS) Voice Morphing:
        Converts a spoken audio file directly into the target voice identity,
        preserving original emotions, timing, and inflection.
        """
        if not self.is_configured():
            raise RuntimeError("ElevenLabs API Key is missing.")

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file for STS not found: {audio_file_path}")

        url = f"{self.BASE_URL}/speech-to-speech/{voice_id}"
        filename = os.path.basename(audio_file_path)

        mime = "audio/wav"
        if filename.endswith(".mp3"):
            mime = "audio/mpeg"

        with open(audio_file_path, "rb") as f_audio:
            files = [("audio", (filename, f_audio, mime))]
            data = {
                "model_id": model_id or self.STS_MODEL,
                "voice_settings": json.dumps({
                    "stability": float(np_clip(stability, 0.0, 1.0)),
                    "similarity_boost": float(np_clip(similarity_boost, 0.0, 1.0))
                })
            }
            res = requests.post(url, headers=self._headers(None), files=files, data=data, timeout=40)

        if res.status_code == 200:
            return res.content
        else:
            err_msg = res.text
            try:
                detail = res.json().get("detail", {})
                if isinstance(detail, dict):
                    err_msg = detail.get("message", res.text)
            except Exception:
                pass
            raise RuntimeError(f"ElevenLabs STS failed ({res.status_code}): {err_msg}")

def np_clip(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(val, max_val))
