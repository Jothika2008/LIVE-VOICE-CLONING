import io
import speech_recognition as sr
import soundfile as sf
import numpy as np

class STTEngine:
    """
    Speech-to-Text Engine Wrapper utilizing SpeechRecognition library
    with Google Web Speech API and offline WAV/PCM decoder.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()

    def transcribe_audio_bytes(self, audio_bytes: bytes, language: str = "en-US") -> str:
        """
        Transcribes audio binary data (WAV/FLAC) to text.
        """
        if not audio_bytes:
            return ""

        try:
            audio_file = io.BytesIO(audio_bytes)
            with sr.AudioFile(audio_file) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = self.recognizer.record(source)
                # Apply Speech Recognition
                text = self.recognizer.recognize_google(audio_data, language=language)
                return text
        except sr.UnknownValueError:
            return "[Voice recorded: Speech not clearly understood]"
        except sr.RequestError as e:
            if "504" in str(e) or "Gateway Timeout" in str(e):
                return "[Network Timeout (504): Google STT Server temporarily unavailable. Speech captured cleanly.]"
            return f"[Network Issue: Speech STT service connection timeout ({e})]"
        except Exception as e:
            return f"[Voice Recorded - Speech processing: {str(e)}]"

    def transcribe_numpy(self, audio_data: np.ndarray, sample_rate: int = 22050, language: str = "en-US") -> str:
        """
        Transcribes raw NumPy audio array by converting to WAV format in memory.
        """
        if audio_data is None or len(audio_data) == 0:
            return ""

        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_data, sample_rate, format='WAV', subtype='PCM_16')
        wav_buffer.seek(0)
        return self.transcribe_audio_bytes(wav_buffer.read(), language=language)
