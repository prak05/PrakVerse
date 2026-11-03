from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class VoiceUnavailable(RuntimeError):
    """Raised when an optional local voice component is not installed."""


class FasterWhisperSTT:
    """Speech-to-text adapter using faster-whisper when installed."""

    def __init__(self, model_size: str = "base", device: str = "cpu"):
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise VoiceUnavailable(
                "Install voice dependencies with: pip install -e '.[voice]'"
            ) from error
        self._model: Any = WhisperModel(model_size, device=device, compute_type="int8")

    def transcribe(self, audio_path: str | Path) -> str:
        segments, _ = self._model.transcribe(str(audio_path))
        return " ".join(segment.text.strip() for segment in segments).strip()


class PiperTTS:
    """Piper command-line adapter with an interruptible process handle."""

    def __init__(self, model_path: str | Path | None = None):
        self.model_path = Path(model_path).expanduser() if model_path else None
        self._process: subprocess.Popen[bytes] | None = None

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        piper = shutil.which("piper")
        if not piper:
            raise VoiceUnavailable(
                "Piper is not installed. Install Piper and place a voice model locally."
            )
        if not self.model_path or not self.model_path.exists():
            raise VoiceUnavailable("Configure a local Piper model path first.")
        with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
            self._process = subprocess.Popen(
                [piper, "--model", str(self.model_path), "--output_file", wav.name],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self._process.communicate(text.encode("utf-8"))
            if self._process.returncode != 0:
                raise VoiceUnavailable("Piper failed to synthesize speech.")
            player = shutil.which("paplay") or shutil.which("ffplay")
            if not player:
                raise VoiceUnavailable("Install paplay or ffplay to play Piper audio.")
            command = [player, wav.name] if player == "paplay" else [player, "-nodisp", "-autoexit", wav.name]
            self._process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._process.wait()
            self._process = None

    def stop(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
        self._process = None
