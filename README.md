# ratecard-api

Fictional rate card for **Kestrel Parcel Co.** The company, zones, and prices are invented. This repository is a small FastAPI service used to show a real multi-stage GitHub Actions pipeline: lint, a Python test matrix, package and image build, SBOM, vulnerability scan, and a tag-only publish to GHCR plus GitHub Releases.

The workflows do not deploy to any server. They do not open a shell on a remote host, and they do not add repository secrets. The only token is the automatic `GITHUB_TOKEN`.

Badge URLs and the image source label use `caoyadong888-wq/pipeforge-demo`. This README does not link back to a portfolio site.

## Overview

`ratecard-api` quotes a parcel.

| Endpoint | Behavior |
| --- | --- |
| `GET /healthz` | Liveness. |
| `GET /v1/zones` | Five fictional zones and their base cents-per-kilogram. |
| `POST /v1/quotes` | Weight, dimensions, zone, and service level in. Quote in integer cents out. |
| `GET /metrics` | Prometheus text written by hand. No metrics client library. |

Quote rules:

- Dimensional weight (kg) = length × width × height ÷ 5000, with centimetres.
- Chargeable weight is the greater of actual weight and dimensional weight.
- Linehaul is chargeable weight × zone base cents × service multiplier. The multiplier is in basis points (10000 = ×1).
- Fuel is a second basis-point surcharge on the rounded linehaul.
- Each money step uses `ROUND_HALF_UP`, then the API returns integers.
- Currency is the fictional rate card's `USD` denomination. It is not a live tariff.

Service levels are `ground`, `priority`, `overnight`, and `express`. There is no database and no outbound call.

## Pipeline

| Workflow | When it runs | What it does |
| --- | --- | --- |
| `ci.yml` | Push to `main`, every pull request, manual dispatch, and `workflow_call` | lint → test (3.10–3.13) → build → SBOM and scan in parallel → summary |
| `release.yml` | Push of a `v*.*.*` tag | Reuses `ci.yml`, then publishes the already scanned image and the Python distributions |
| `codeql.yml` | Push to `main`, pull requests, and a weekly schedule | Python CodeQL |

`release.yml` calls `ci.yml` with `workflow_call` instead of copying the jobs. Pull requests use `pull_request`, so the run is not given repository secrets.

## Stages

**lint.** `ruff check`, `ruff format --check`, and `mypy app`. Then a pinned `actionlint` binary, checked against its published sha256, with `shellcheck` on the same path so `run:` scripts are checked too.

**test.** Python 3.10, 3.11, 3.12, and 3.13 on `ubuntu-latest`, `fail-fast: false`. Pytest must stay at or above 90% coverage and uploads a JUnit file plus a coverage XML file for each version.

**build.** `python -m build` writes a wheel and an sdist. `docker/build-push-action` builds the image with `push: false` and `load: true`, then `docker save` stores `image.tar` for the later jobs. Provenance is left off at this step because the local load exporter does not carry it.

**sbom.** Syft, through `anchore/sbom-action`, writes SPDX JSON and CycloneDX JSON for the image, and SPDX JSON for the source tree.

**scan.** Trivy reads the image archive. Severity is `CRITICAL,HIGH`, unfixed issues are ignored, and `exit-code` is `1`, so a blocking finding fails the job. The SARIF file is uploaded to code scanning.

**summary.** Writes the job results, the local image id, and the CycloneDX component count to the run summary.

**publish** (tag only). Logs in to GHCR with `GITHUB_TOKEN`, pushes `ghcr.io/<owner>/<repo>:<version>` and `:sha-<short>`, and does not push a floating `latest` tag. `actions/attest-build-provenance` attests the image, the wheel, and the sdist. `softprops/action-gh-release` attaches the wheel, the sdist, the three SBOM files, and `SHA256SUMS`.

## Badges

Live badge URLs for this public repository:

[![CI](https://github.com/caoyadong888-wq/pipeforge-demo/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/caoyadong888-wq/pipeforge-demo/actions/workflows/ci.yml)

[![Release](https://github.com/caoyadong888-wq/pipeforge-demo/actions/workflows/release.yml/badge.svg)](https://github.com/caoyadong888-wq/pipeforge-demo/actions/workflows/release.yml)

## Release

Tag `v0.1.0` (matching `__version__` and `pyproject.toml`) to run `release.yml`.

The GHCR package should be switched to public on the package settings page after the first publish. A workflow cannot do that by itself. The image label `org.opencontainers.image.source` is `https://github.com/caoyadong888-wq/pipeforge-demo` so the package links to this repository.

Attached to the GitHub Release:

- wheel and sdist
- `sbom-image.spdx.json`, `sbom-image.cdx.json`, `sbom-source.spdx.json`
- `SHA256SUMS`

Build provenance attestations are published for the image and both Python artifacts.

This repository stops at publish. A rollout, if you add one later, belongs in a system you operate: pull the image by digest from GHCR and apply it in that environment. Do not add that step to these workflows.

## Security notes

- Third-party and `actions/*` steps are pinned to a full commit SHA, with the version in a trailing comment.
- The workflow token starts at `contents: read`. Jobs raise it only for code scanning, packages, release contents, the OIDC token, and attestations.
- Pull requests do not use `pull_request_target` and do not receive secrets.
- Checkout sets `persist-credentials: false`.
- Untrusted event fields are not interpolated into `run:` scripts.
- Dependabot checks `github-actions`, `pip`, and `docker` every week.
- No new repository secret is required.

## Local run

Python 3.10 or newer. These commands run the API and the tests. They do not build the container image. Image build and scan run on GitHub-hosted runners; this checkout does not claim a local image build.

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080
```

```bash
curl -s localhost:8080/healthz
curl -s localhost:8080/v1/zones
curl -s -X POST localhost:8080/v1/quotes \
  -H 'content-type: application/json' \
  -d '{"weight_kg":"2.5","length_cm":"40","width_cm":"30","height_cm":"20","zone":"metro","service":"ground"}'
curl -s localhost:8080/metrics
```

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy app
.venv/bin/pytest
```

The ground metro example above is 2177 cents: dimensional weight 4.8 kg, linehaul 2016, fuel 161.
