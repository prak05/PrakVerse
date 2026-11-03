from pathlib import Path

import pytest

from prakverse.voice.pipeline import VoicePipeline
from prakverse.voice.speech import VoiceUnavailable
from prakverse.voice.wake import WakeWordDetector


class FakeSTT:
    def transcribe(self, _path):
        return "What is PrakVerse?"


class FakeTTS:
    def __init__(self):
        self.spoken = []
        self.stopped = False

    def speak(self, text):
        self.spoken.append(text)

    def stop(self):
        self.stopped = True


def test_voice_pipeline_transcribes_responds_and_speaks(tmp_path: Path) -> None:
    tts = FakeTTS()
    pipeline = VoicePipeline(FakeSTT(), tts)

    result = pipeline.process_audio(tmp_path / "input.wav", lambda text: f"Answering: {text}")

    assert result == "Answering: What is PrakVerse?"
    assert tts.spoken == [result]
    pipeline.stop_speaking()
    assert tts.stopped


def test_wake_detector_uses_threshold() -> None:
    class Detector:
        def predict(self, _frame):
            return {"hey_priyumvada": 0.8}

    assert WakeWordDetector(detector=Detector()).detected([b"frame"])


def test_wake_detector_rejects_low_score() -> None:
    class Detector:
        def predict(self, _frame):
            return {"hey_priyumvada": 0.2}

    assert not WakeWordDetector(detector=Detector()).detected([b"frame"])
