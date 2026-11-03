from pathlib import Path

from prakverse.doctor import detect_hardware


def test_hardware_report_has_safe_model_choice(monkeypatch) -> None:
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: "")
    report = detect_hardware()
    assert report.selected_model in {"qwen2.5:3b", "qwen2.5:7b"}
    assert report.model_reason
