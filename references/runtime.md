# Runtime and credentials

Install the latest public PandaData SDK:

```bash
pip install "panda_data>=0.0.9,<0.1"
```

This skill is validated with public releases 0.0.9 and 0.0.12. The PandaAI `panda-data` repository mentions an internal/local 0.1.0 wheel, but that version is not currently published on public PyPI.

Set credentials outside the skill:

```text
PANDA_DATA_USERNAME
PANDA_DATA_PASSWORD
PANDA_DATA_BASE_URL  # optional
```

Legacy `PANDA_USERNAME`, `PANDA_PASSWORD`, and `PANDA_BASE_URL` variables remain accepted for compatibility. Never put credentials, JWT tokens, or `.env` files in a delivery archive.
