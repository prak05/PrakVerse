from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import CHAT_MODEL, EMBED_MODEL, OLLAMA_URL


@dataclass(frozen=True)
class HardwareReport:
    os_name: str
    ram_gib: float
    gpus: tuple[str, ...]
    selected_model: str
    model_reason: str


def _read_ram_gib() -> float:
    with open("/proc/meminfo", encoding="utf-8") as meminfo:
        for line in meminfo:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    return 0.0


def detect_hardware() -> HardwareReport:
    os_name = "Linux"
    try:
        with open("/etc/os-release", encoding="utf-8") as release:
            values = dict(
                line.rstrip().split("=", 1)
                for line in release
                if "=" in line
            )
        os_name = values.get("PRETTY_NAME", os_name).strip('"')
    except OSError:
        pass

    gpus: list[str] = []
    lspci = shutil.which("lspci")
    if lspci:
        result = subprocess.run(
            [lspci],
            check=False,
            capture_output=True,
            text=True,
        )
        gpus = [
            line.split(": ", 1)[1]
            for line in result.stdout.splitlines()
            if ": " in line and any(
                marker in line.lower() for marker in ("vga", "3d controller", "display")
            )
        ]

    ram_gib = _read_ram_gib()
    if ram_gib >= 16:
        selected_model = "qwen2.5:7b"
        reason = "At least 16 GiB RAM is available for a stronger local model."
    else:
        selected_model = "qwen2.5:3b"
        reason = "Less than 16 GiB RAM is available; a 3B quantized model is safer."
    return HardwareReport(os_name, ram_gib, tuple(gpus), selected_model, reason)


def _ollama_models() -> tuple[bool, list[str], str]:
    binary = shutil.which("ollama")
    if not binary:
        return False, [], "ollama is not installed or is not on PATH"
    version = subprocess.run(
        [binary, "--version"], check=False, capture_output=True, text=True
    ).stdout.strip()
    try:
        response = urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2)
        payload = json.load(response)
        models = [item["name"] for item in payload.get("models", [])]
        return True, models, version or "installed"
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        return False, [], f"{version or 'installed'}, server unavailable: {error}"


def print_doctor_report() -> int:
    hardware = detect_hardware()
    installed, models, ollama_status = _ollama_models()
    print("PrakVerse Phase 0 doctor")
    print(f"OS: {hardware.os_name}")
    print(f"RAM: {hardware.ram_gib:.1f} GiB")
    print(f"GPU: {'; '.join(hardware.gpus) if hardware.gpus else 'not detected'}")
    print(f"Selected chat model: {hardware.selected_model}")
    print(f"Selection reason: {hardware.model_reason}")
    print(f"Ollama: {ollama_status}")
    print(f"Chat model configured: {CHAT_MODEL}")
    print(f"Embedding model configured: {EMBED_MODEL}")
    if installed:
        print(f"Chat model available: {'yes' if CHAT_MODEL in models else 'no'}")
        print(f"Embedding model available: {'yes' if EMBED_MODEL in models else 'no'}")
    else:
        print("Chat model available: no (install/start Ollama first)")
        print("Embedding model available: no (install/start Ollama first)")
        print("Install: https://ollama.com/download/linux")
        print("Then run: ollama serve && ollama pull qwen2.5:3b && ollama pull nomic-embed-text")
    return 0 if installed and CHAT_MODEL in models and EMBED_MODEL in models else 1
