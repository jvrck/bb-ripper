# Contributing

BBRipper uses Python 3.12 and uv 0.12.24. Create the locked development
environment and run the checks with:

```bash
uv sync --locked
uv run --locked python -m unittest discover -v
uv run --locked pylint src/bb_ripper bb-ripper scripts
uv run --locked pip-audit -r requirements.txt
uv build
```

`pyproject.toml` and `uv.lock` are the dependency sources of truth. After a
dependency change, update and verify both the lock and generated pip fallback:

```bash
uv lock
scripts/export_requirements.sh
uv lock --check
scripts/export_requirements.sh /tmp/requirements.txt
diff -u requirements.txt /tmp/requirements.txt
```

Dependabot manages the uv project and updates `uv.lock`; its pull requests must
also regenerate `requirements.txt`. CI rejects export drift.

For pip compatibility checks, create a clean Python 3.12 virtual environment,
install `requirements.txt`, and run:

```bash
PYTHONPATH=src python -m unittest discover -v
python3 bb-ripper/
```

The last command is expected to fail closed with exit status 1 when the
required runtime environment variables are absent.
