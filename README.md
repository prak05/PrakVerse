# PrakVerse

PrakVerse is a local-first personal AI operating environment. **Priyumvada** is
the assistant persona that will eventually operate through it.

The project is intentionally starting without paid APIs or cloud dependencies:

- local memory in SQLite and FTS5;
- local files and project indexes;
- full automatic execution for permitted actions, with a permanent deny-list;
- replaceable local model backends;
- no credentials required for the core.

The current execution mode is `full_auto`: permitted tools do not prompt for
confirmation. The deny-list remains mandatory and blocks dangerous operations
such as `sudo`, disk formatting, credential files, SSH files, and destructive
root paths.

## Phase 0: recon and scaffold

The first milestone is the durable local core. It stores and searches memories
without requiring Ollama, a hosted model, a vector database, or an account.

The Phase 0 doctor also detects local hardware and reports whether Ollama and
the configured models are available:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

prak doctor
prak status
prakverse remember "LinkedIn Indo is Priyumvada's first document skill." --source project
prakverse search "document skill"
```

On this machine the recommended initial model is `qwen2.5:3b`: available RAM is
about 7.5 GiB and the NVIDIA driver is unavailable, so CPU-safe inference is
preferred. Install Ollama separately from
[ollama.com/download/linux](https://ollama.com/download/linux), then run:

```bash
ollama serve
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
prak doctor
```

Run tests with:

```bash
python -m pytest
```

## Long-term direction

PrakVerse will add local model inference, trusted personal knowledge, voice,
browser and desktop tools, project skills, and scheduled missions in separate
layers. No layer should silently gain permission to delete files, publish,
send messages, spend money, or change system settings.
