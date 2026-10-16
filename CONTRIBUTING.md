# Contributing

BBRipper uses Python 3.12 and pins uv 0.12.24. Install that version, or, when
your default uv differs, replace `uv` with `uvx uv@0.12.24` in the commands
below. Create the locked development environment and run the checks with:

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

The export script rejects any uv version other than 0.12.24. If your default
uv differs, set its pinned command when invoking the script:

```bash
BBRIPPER_UV="uvx uv@0.12.24" scripts/export_requirements.sh
```

Dependabot manages the uv project and updates `uv.lock`; its pull requests must
also regenerate `requirements.txt`. CI rejects export drift.

For pip compatibility checks, create and activate a clean Python 3.12 virtual
environment with a CPython 3.12 interpreter (named `python3.12` below; adjust
for your system), install `requirements.txt`, and run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m unittest discover -v
python3 bb-ripper/
```

uv users can create the environment with `uv venv --seed -p 3.12 .venv`
instead of the first command; the remaining steps are unchanged.

The last command is expected to fail closed with exit status 1 when the
required runtime environment variables are absent.
