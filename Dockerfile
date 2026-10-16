# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/

RUN --mount=from=ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a,source=/uv,target=/bin/uv \
    uv build --wheel --out-dir /dist

FROM python:3.12-slim-bookworm
ARG AWSCLI=FALSE
ARG TARGETARCH

WORKDIR /ripper

COPY requirements.txt ./
COPY bb-ripper/__main__.py ./__main__.py
COPY setup.sh ./

RUN chmod +x setup.sh && ./setup.sh && rm setup.sh
COPY --from=builder /dist/bb_ripper-1.3.0-py3-none-any.whl /tmp/
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a,source=/uv,target=/bin/uv \
    uv pip install --system --no-cache -r requirements.txt && \
    uv pip install --system --no-cache --no-deps /tmp/bb_ripper-1.3.0-py3-none-any.whl && \
    rm requirements.txt /tmp/bb_ripper-1.3.0-py3-none-any.whl

VOLUME /data

ENV BB_RIPPER_EXPORT_DIRECTORY=/data/

CMD ["python3", "."]
