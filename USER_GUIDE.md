# PrakVerse user guide

```bash
prak doctor
prak chat
prak up
prak ingest ~/Documents
prak recall "my project architecture"
prak plan system_info list_apps
prak skill list
prak schedule list
```

Install optional layers only when needed:

```bash
pip install -e '.[ui]'
pip install -e '.[browser]' && playwright install chromium
pip install -e '.[voice]'
```

The service helper installs a user-level systemd unit without root access:

```bash
./scripts/install-user-service.sh
systemctl --user enable --now prakverse.service
```

Keep `config.yaml` and the audit log local. Never place secrets in indexed
folders; secret-like paths are excluded by the ingestion layer.
