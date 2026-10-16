# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm
ARG AWSCLI=FALSE
ARG TARGETARCH

WORKDIR /ripper

COPY requirements.txt /ripper
COPY bb-ripper/ /ripper/
COPY setup.sh /ripper

RUN chmod +x setup.sh && ./setup.sh && rm setup.sh
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.24@sha256:3af4716e991d6956a41e573eab705d0ee08500cd829ed30293eb8472f372c65a,source=/uv,target=/bin/uv \
    uv pip install --system --no-cache -r requirements.txt

VOLUME /data

ENV BB_RIPPER_EXPORT_DIRECTORY=/data/

CMD ["python3", "."]
