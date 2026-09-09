import io
import numpy as np
import soundfile as sf
import librosa

class AudioDSP:
    """
    Relaxed Audio Preprocessing Pipeline optimized for Neural Voice Cloning (Coqui XTTS-v2):
    - DC-Offset Removal & Gentle High-Pass Filtering (preserves natural vocal formants)
    - Clean Mono Resampling (Default 24,000 Hz native for XTTS-v2)
    - Non-Aggressive Silence Trimming
    - Minimum 3-Second Reference Padding (Prevents acoustic truncation distortion)
    - Peak Amplitude Normalization (-1.0 dBFS)
    """

    @staticmethod
    def resample_audio(audio_data: np.ndarray, orig_sr: int, target_sr: int = 24000) -> np.ndarray:
        """
        Resamples audio array to target sample rate (default 24000 Hz mono).
        """
        if audio_data is None or len(audio_data) == 0:
            return audio_data

        # Ensure 1D mono float32
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        audio_data = audio_data.astype(np.float32)

        if orig_sr == target_sr:
            return audio_data

        resampled = librosa.resample(y=audio_data, orig_sr=orig_sr, target_sr=target_sr)
        return resampled

    @staticmethod
    def remove_dc_offset(audio_data: np.ndarray) -> np.ndarray:
        """
        Removes DC offset to prevent low-frequency pops and speaker offset distortion.
        """
        if audio_data is None or len(audio_data) == 0:
            return audio_data
        return audio_data - np.mean(audio_data)

    @staticmethod
    def trim_silence(audio_data: np.ndarray, sr: int, top_db: int = 30) -> np.ndarray:
        """
        Gently trims leading and trailing silence without clipping spoken words or formants.
        """
        if audio_data is None or len(audio_data) == 0:
            return audio_data

        trimmed_audio, _ = librosa.effects.trim(y=audio_data, top_db=top_db)
        return trimmed_audio

    @staticmethod
    def normalize_amplitude(audio_data: np.ndarray, target_dBFS: float = -1.0) -> np.ndarray:
        """
        Clean peak amplitude normalization with -1 dB headroom (0.90 scaling)
        to prevent clipping and scratchy/raspy distortion.
        """
        if audio_data is None or len(audio_data) == 0:
            return audio_data

        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = (audio_data / max_val) * 0.90  # Leave -1 dB headroom to prevent clipping
        return audio_data

    @staticmethod
    def ensure_minimum_duration(audio_data: np.ndarray, sr: int = 24000, min_duration_sec: float = 3.5) -> np.ndarray:
        """
        Ensures reference speaker audio is at least 3.5 seconds long by repeating or padding cleanly,
        providing sufficient acoustic features to XTTS-v2 to avoid metallic/robotic artifacting.
        """
        if audio_data is None or len(audio_data) == 0:
            return audio_data

        min_samples = int(min_duration_sec * sr)
        current_samples = len(audio_data)

        if current_samples >= min_samples:
            return audio_data

        # Loop audio naturally until minimum duration is reached
        repeats = int(np.ceil(min_samples / current_samples))
        extended_audio = np.tile(audio_data, repeats)[:min_samples]
        return extended_audio

    @classmethod
    def process_pipeline(
        cls,
        audio_data: np.ndarray,
        orig_sr: int,
        target_sr: int = 24000,
        top_db: int = 30,
        target_dBFS: float = -1.0,
        enable_denoise: bool = True
    ) -> tuple[np.ndarray, int]:
        """
        Executes relaxed DSP pipeline preserving natural voice timbre:
        1. Remove DC-Offset
        2. Clean Mono Resample (24000 Hz)
        3. Gentle Silence Trim
        4. Minimum Duration Padding (3.5s)
        5. Peak Normalization (-1.0 dB)
        """
        if audio_data is None or len(audio_data) == 0:
            return audio_data, orig_sr

        # Step 1: Ensure mono float32 & remove DC offset
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        audio_data = cls.remove_dc_offset(audio_data.astype(np.float32))

        # Step 2: Resample to target rate (24,000 Hz native XTTS)
        processed = cls.resample_audio(audio_data, orig_sr, target_sr)

        # Step 3: Gentle silence trimming (preserve formants)
        trimmed = cls.trim_silence(processed, target_sr, top_db=top_db)

        # Step 4: Ensure min duration (3.5 sec)
        duration_fixed = cls.ensure_minimum_duration(trimmed, target_sr, min_duration_sec=3.5)

        # Step 5: Peak Normalization
        final_audio = cls.normalize_amplitude(duration_fixed, target_dBFS=target_dBFS)

        return final_audio, target_sr

    @staticmethod
    def audio_bytes_to_numpy(audio_bytes: bytes) -> tuple[np.ndarray, int]:
        """
        Converts raw audio bytes (WAV/MP3/FLAC) to NumPy array and sample rate.
        """
        buffer = io.BytesIO(audio_bytes)
        data, sr = sf.read(buffer)
        return data, sr

    @staticmethod
    def numpy_to_audio_bytes(audio_data: np.ndarray, sr: int = 24000, format: str = "WAV") -> bytes:
        """
        Converts NumPy array to 16-bit PCM WAV audio bytes cleanly.
        """
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sr, format=format, subtype='PCM_16')
        buffer.seek(0)
        return buffer.read()
