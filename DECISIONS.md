# Decisions

## Phase 0

- **Local-only by default:** `cloud_apis_enabled` is false and no provider
  credentials are required by the core.
- **Model selection:** this machine has approximately 7.5 GiB RAM and an Intel
  Iris Xe plus NVIDIA MX350 GPU. The NVIDIA driver is not currently usable, so
  the initial target is `qwen2.5:3b`, which is more appropriate for CPU
  inference than a 7B model.
- **Embedding model:** `nomic-embed-text` is the configured Ollama embedding
  model.
- **Memory foundation:** the existing SQLite FTS5 store remains the Phase 0
  foundation. ChromaDB is deferred to Phase 3, when ingestion and embeddings
  are implemented together.
- **Ollama installation:** Ollama was not present during Phase 0. The doctor
  reports the official install instructions instead of downloading or
  executing an installer implicitly.
- **Execution mode:** the user selected `full_auto`. Permitted actions run
  without confirmation; the deny-list remains mandatory and is not bypassed.
