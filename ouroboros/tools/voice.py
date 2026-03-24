"""
Ouroboros — Voice tools.

Send and receive voice notes on Telegram.
Uses edge-tts for text-to-speech (free, human-quality voices).
"""

from __future__ import annotations
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict

log = logging.getLogger(__name__)


def text_to_voice(text: str, voice: str = "en-US-GuyNeural",
                  chat_id: int = 0) -> Dict[str, Any]:
    """Convert text to a voice note and send it on Telegram.

    Uses edge-tts (Microsoft Edge TTS, free, human-quality).
    Voices: en-US-GuyNeural (male), en-US-JennyNeural (female),
            en-GB-RyanNeural (British male), en-US-AriaNeural (female).
    """
    try:
        # Generate speech with edge-tts
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
            mp3_path = tmp_mp3.name

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_ogg:
            ogg_path = tmp_ogg.name

        # Generate MP3
        result = subprocess.run(
            ["edge-tts", "--voice", voice, "--text", text, "--write-media", mp3_path],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            # Try installing edge-tts
            subprocess.run(["pip", "install", "edge-tts"], capture_output=True, timeout=30)
            result = subprocess.run(
                ["edge-tts", "--voice", voice, "--text", text, "--write-media", mp3_path],
                capture_output=True, text=True, timeout=60
            )

        if result.returncode != 0:
            return {"error": f"TTS failed: {result.stderr}", "status": "failed"}

        # Convert to OGG/Opus for Telegram voice note
        ffmpeg_result = subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "48k", ogg_path],
            capture_output=True, text=True, timeout=30
        )

        if ffmpeg_result.returncode != 0:
            # If ffmpeg not available, send mp3 directly
            voice_path = mp3_path
        else:
            voice_path = ogg_path

        # Send via Telegram if chat_id provided
        if chat_id:
            try:
                from supervisor.telegram import get_tg
                tg = get_tg()
                with open(voice_path, "rb") as f:
                    voice_bytes = f.read()
                ok, err = tg.send_voice(chat_id, voice_bytes)
                if ok:
                    return {"status": "sent", "chat_id": chat_id, "voice": voice, "length": len(text)}
                else:
                    return {"status": "send_failed", "error": err}
            except Exception as e:
                return {"status": "tts_ok_send_failed", "error": str(e), "file": voice_path}

        return {"status": "generated", "file": voice_path, "voice": voice}

    except Exception as e:
        return {"error": str(e), "status": "failed"}
    finally:
        # Cleanup
        for p in [mp3_path, ogg_path]:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass


def transcribe_voice(file_id: str = "", file_path: str = "") -> Dict[str, Any]:
    """Transcribe a voice note to text.

    Uses whisper.cpp or falls back to basic speech recognition.
    Provide either file_id (Telegram) or file_path (local).
    """
    try:
        audio_path = file_path

        # Download from Telegram if file_id provided
        if file_id and not file_path:
            from supervisor.telegram import get_tg
            tg = get_tg()
            audio_bytes = tg.get_file(file_id)
            if not audio_bytes:
                return {"error": "Failed to download voice note", "status": "failed"}

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp.write(audio_bytes)
                audio_path = tmp.name

        if not audio_path:
            return {"error": "No file_id or file_path provided", "status": "failed"}

        # Convert to WAV for processing
        wav_path = audio_path + ".wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, timeout=30
        )

        # Try whisper if available
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(wav_path)
            return {"text": result["text"], "status": "ok", "method": "whisper"}
        except ImportError:
            pass

        # Fallback: SpeechRecognition library
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            return {"text": text, "status": "ok", "method": "google_speech"}
        except ImportError:
            pass

        return {"error": "No speech recognition library available. Install whisper or SpeechRecognition.", "status": "failed"}

    except Exception as e:
        return {"error": str(e), "status": "failed"}


def get_tools() -> list:
    return [
        {
            "name": "text_to_voice",
            "description": "Convert text to a human-quality voice note and send via Telegram. Voices: en-US-GuyNeural (male), en-US-JennyNeural (female), en-GB-RyanNeural (British).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to speak"},
                    "voice": {"type": "string", "default": "en-US-GuyNeural",
                              "description": "Voice: en-US-GuyNeural, en-US-JennyNeural, en-GB-RyanNeural, en-US-AriaNeural"},
                    "chat_id": {"type": "integer", "description": "Telegram chat ID to send to (0 = just generate file)"},
                },
                "required": ["text"],
            },
            "function": text_to_voice,
        },
        {
            "name": "transcribe_voice",
            "description": "Transcribe a voice note to text. Provide file_id (from Telegram) or file_path (local).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "Telegram file_id of the voice note"},
                    "file_path": {"type": "string", "description": "Local path to audio file"},
                },
            },
            "function": transcribe_voice,
        },
    ]
