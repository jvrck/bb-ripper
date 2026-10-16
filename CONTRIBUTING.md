# Contributing

BBRipper uses Python 3.12 and uv 0.12.24. Create the locked development
environment and run the checks with the pinned uv version:

```bash
uvx uv@0.12.24 sync --locked
uvx uv@0.12.24 run --locked python -m unittest discover -v
uvx uv@0.12.24 run --locked pylint src/bb_ripper bb-ripper scripts
uvx uv@0.12.24 run --locked pip-audit -r requirements.txt
uvx uv@0.12.24 build
```

`pyproject.toml` and `uv.lock` are the dependency sources of truth. After a
dependency change, update and verify both the lock and generated pip fallback:

```bash
uvx uv@0.12.24 lock
BBRIPPER_UV="uvx uv@0.12.24" scripts/export_requirements.sh
uvx uv@0.12.24 lock --check
BBRIPPER_UV="uvx uv@0.12.24" scripts/export_requirements.sh /tmp/requirements.txt
diff -u requirements.txt /tmp/requirements.txt
```

The export script rejects any uv version other than 0.12.24. Use the pinned uv
through uvx when invoking it:

```bash
BBRIPPER_UV="uvx uv@0.12.24" scripts/export_requirements.sh
```

Dependabot manages the uv project and updates `uv.lock`; its pull requests must
also regenerate `requirements.txt`. CI rejects export drift.

For pip compatibility checks, create and activate a clean Python 3.12 virtual
environment with the pinned uv, install `requirements.txt`, and run:

```bash
uvx uv@0.12.24 venv --seed --python 3.12 .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m unittest discover -v
python3 bb-ripper/
```

The last command is expected to fail closed with exit status 1 when the
required runtime environment variables are absent.
