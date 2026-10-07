# Multi-stage image for the fictional ratecard-api.
# The base image is pinned by digest. This file is built on GitHub-hosted
# runners. The authoring environment does not claim a local image build.
# IMAGE_SOURCE points at the public demo repository on caoyadong888-wq.

FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src
RUN pip install --no-cache-dir build
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN python -m build --wheel --outdir /dist

FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 ratecard \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin ratecard

WORKDIR /app
COPY --from=build /dist /dist
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /dist/*.whl \
    && pip uninstall -y pip \
    && rm -rf /dist

USER 10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).read()"]

ARG IMAGE_SOURCE=https://github.com/caoyadong888-wq/pipeforge-demo
LABEL org.opencontainers.image.source="${IMAGE_SOURCE}" \
      org.opencontainers.image.title="ratecard-api" \
      org.opencontainers.image.description="Fictional Kestrel Parcel Co. rate card API" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Kestrel Parcel Co. (fictional)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
