from __future__ import annotations

import queue
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .brain.history import ConversationHistory
from .brain.ollama import OllamaClient, OllamaError
from .brain.persona import load_system_prompt
from .brain.session import ChatSession
from .config import ASSISTANT_NAME, CHAT_MODEL, OLLAMA_URL


class NativePrakVerse:
    """Native Tk desktop interface with typed chat and local microphone capture."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PrakVerse — Priyumvada")
        self.root.geometry("1100x720")
        self.root.minsize(760, 520)
        self.session = ChatSession(
            OllamaClient(OLLAMA_URL, CHAT_MODEL),
            ConversationHistory(load_system_prompt(), 12),
        )
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.recording = False
        self._build()
        self._poll_events()

    def _build(self) -> None:
        self.root.configure(bg="#08090a")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#08090a")
        style.configure("Panel.TFrame", background="#111315")
        style.configure("TLabel", background="#08090a", foreground="#f4f4f5")
        style.configure("Muted.TLabel", background="#08090a", foreground="#9299a3")
        style.configure("Accent.TButton", background="#8b9cff", foreground="#08090a")
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="PRAKVERSE / LOCAL CONTROL", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(header, text="Priyumvada.", font=("TkDefaultFont", 32, "bold")).pack(anchor="w")
        self.health = ttk.Label(header, text=f"LOCAL / {CHAT_MODEL} / {OLLAMA_URL}", style="Muted.TLabel")
        self.health.pack(anchor="w")
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Panel.TFrame", padding=16)
        left.pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(left, text="AGENT DESK").pack(anchor="w", pady=(0, 12))
        for label, prompt in (
            ("Mission status", "Give me a concise status report."),
            ("Project map", "What projects are connected to Central Intel?"),
            ("Recent work", "Recall my latest AI and software work."),
        ):
            ttk.Button(left, text=label, command=lambda p=prompt: self.ask(p)).pack(fill="x", pady=4)
        ttk.Label(left, text="VOICE", style="Muted.TLabel").pack(anchor="w", pady=(28, 8))
        self.voice_button = ttk.Button(left, text="Speak", command=self.toggle_recording, style="Accent.TButton")
        self.voice_button.pack(fill="x")
        self.voice_status = ttk.Label(left, text="Push to talk", style="Muted.TLabel", wraplength=170)
        self.voice_status.pack(anchor="w", pady=8)
        center = ttk.Frame(body, style="Panel.TFrame", padding=16)
        center.pack(side="left", fill="both", expand=True)
        ttk.Label(center, text="PRIYU CHANNEL").pack(anchor="w")
        self.transcript = tk.Text(
            center, bg="#111315", fg="#f4f4f5", insertbackground="#f4f4f5",
            relief="flat", wrap="word", state="disabled", padx=12, pady=12,
        )
        self.transcript.pack(fill="both", expand=True, pady=(12, 12))
        self.transcript.tag_configure("user", foreground="#8b9cff")
        self.transcript.tag_configure("priyu", foreground="#8ee6a5")
        form = ttk.Frame(center)
        form.pack(fill="x")
        self.entry = ttk.Entry(form)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda _event: self.ask(self.entry.get()))
        ttk.Button(form, text="Send", command=lambda: self.ask(self.entry.get()), style="Accent.TButton").pack(side="right")
        self._append("Priyumvada", "Native desktop interface online. Speak or type a mission.", "priyu")

    def _append(self, speaker: str, text: str, tag: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}\n", tag)
        self.transcript.insert("end", f"{text}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def ask(self, message: str) -> None:
        message = message.strip()
        if not message:
            return
        self.entry.delete(0, "end")
        self._append("You", message, "user")
        threading.Thread(target=self._answer, args=(message,), daemon=True).start()

    def _answer(self, message: str) -> None:
        try:
            response = self.session.respond(message)
            self.events.put(("answer", response))
        except (OllamaError, ValueError) as error:
            self.events.put(("error", str(error)))

    def toggle_recording(self) -> None:
        if self.recording:
            return
        if not shutil.which("pw-record"):
            messagebox.showerror("Voice unavailable", "PipeWire pw-record is not installed.")
            return
        self.recording = True
        self.voice_button.configure(text="Listening...")
        self.voice_status.configure(text="Speak now. Recording for up to 8 seconds.")
        threading.Thread(target=self._record_and_transcribe, daemon=True).start()

    def _record_and_transcribe(self) -> None:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio:
                audio_path = Path(audio.name)
            subprocess.run(
                ["pw-record", "--target", "auto", "--rate", "16000", "--channels", "1", str(audio_path)],
                timeout=8,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                from faster_whisper import WhisperModel
            except ImportError as error:
                raise RuntimeError("Install local voice support with: python3 -m pip install faster-whisper") from error
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(str(audio_path))
            text = " ".join(segment.text.strip() for segment in segments).strip()
            if text:
                self.events.put(("voice", text))
            else:
                self.events.put(("error", "I did not hear speech."))
        except (OSError, subprocess.SubprocessError, RuntimeError) as error:
            self.events.put(("error", str(error)))
        finally:
            try:
                audio_path.unlink()
            except (UnboundLocalError, OSError):
                pass

    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                self.recording = False
                self.voice_button.configure(text="Speak")
                self.voice_status.configure(text="Push to talk")
                if kind == "answer":
                    self._append("Priyumvada", value, "priyu")
                elif kind == "voice":
                    self.ask(value)
                else:
                    self._append("System", value, "priyu")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)


def run() -> None:
    root = tk.Tk()
    NativePrakVerse(root)
    root.mainloop()


if __name__ == "__main__":
    run()
