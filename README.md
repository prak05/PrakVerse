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

Phase 2 adds a safety-gated local tool registry and an append-only audit log at
`data/audit.jsonl`. Dry-run mode is enabled by default in `config.yaml`; tool
integration will use the registry before execution.

## Phase 3: local knowledge

Index a folder and search it with source citations:

```bash
prak ingest ~/Documents
prak recall "project architecture"
prak fact remember "PrakVerse is local-first." --source confirmed
prak fact list
prak memory export /tmp/prakverse-memory.json
prak memory wipe
```

`.env`, SSH, cloud credential, token, password, API-key, and private-key
patterns are skipped. ChromaDB and Ollama embeddings are used when installed
and reachable; otherwise the local SQLite lexical index remains available.

## Phase 4: browser and desktop tools

Optional browser support:

```bash
pip install -e '.[browser]'
playwright install chromium
```

The browser tools support opening, privacy-friendly search, extraction, click,
fill, and screenshots. Optional GUI support uses PyAutoGUI and detects Wayland
or X11:

```bash
pip install -e '.[gui]'
```

Browser and GUI actions are registered through the same audit and deny-list
registry as the Phase 2 tools.

## Phase 5: local voice

Voice dependencies are optional:

```bash
pip install -e '.[voice]'
```

`prak listen --audio recording.wav` uses faster-whisper locally and can send
the response to Piper when a local Piper model is configured. The intended wake
word is **Hey Priyumvada**. Until microphone dependencies are installed, the
push-to-talk fallback is `prak chat`.

## Phase 6: bounded autonomy

Plans are visible and capped by an action budget:

```bash
prak plan system_info list_apps
prak skill list
prak skill run my-skill
prak schedule add morning-notes 86400 my-skill
prak schedule list
prak schedule run-due
```

Drop YAML or Python skills into `skills/` without editing the core. YAML skills
use a `name`, optional `description`, and `steps` containing tool names and
arguments. Local MCP servers can be configured in `mcp.json`; the stdio client
is available to integrations without requiring a hosted service.

## Phase 7: dashboard and packaging

Install the optional Textual dashboard and start it with:

```bash
pip install -e '.[ui]'
prak up
```

See `ARCHITECTURE.md` and `USER_GUIDE.md` for the system design and local
service setup. The systemd unit is user-scoped and does not require `sudo`.

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
