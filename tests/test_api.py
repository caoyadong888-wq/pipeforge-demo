"""Endpoint tests through httpx ASGITransport."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from app.main import create_app
from app.zones import ZONES

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def test_healthz(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ratecard-api"
    assert body["version"]


async def test_zones_lists_five_fictional_codes(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/zones")
    assert response.status_code == 200
    zones = response.json()["zones"]
    assert [zone["code"] for zone in zones] == [zone.code for zone in ZONES]
    assert len(zones) == 5
    assert zones[0]["base_cents_per_kg"] == 420


async def test_quote_and_metrics(client: httpx.AsyncClient) -> None:
    before = await client.get("/metrics")
    assert before.status_code == 200
    assert before.headers["content-type"].startswith("text/plain")
    assert before.text.endswith("\n")
    assert "ratecard_quotes_total 0\n" in before.text

    response = await client.post(
        "/v1/quotes",
        json={
            "weight_kg": "2.5",
            "length_cm": "40",
            "width_cm": "30",
            "height_cm": "20",
            "zone": "metro",
            "service": "ground",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_cents"] == 2177
    assert body["fuel_surcharge_bp"] == 800

    after = await client.get("/metrics")
    assert "ratecard_quotes_total 1\n" in after.text
    assert "ratecard_quote_cents_sum 2177\n" in after.text
    assert 'service="ratecard-api"' in after.text

    second = await client.post(
        "/v1/quotes",
        json={
            "weight_kg": 1,
            "length_cm": 10,
            "width_cm": 10,
            "height_cm": 10,
            "zone": "island",
            "service": "overnight",
        },
    )
    assert second.status_code == 200
    summed = await client.get("/metrics")
    assert "ratecard_quotes_total 2\n" in summed.text
    assert f"ratecard_quote_cents_sum {2177 + second.json()['total_cents']}\n" in summed.text


async def test_quote_validation_errors(client: httpx.AsyncClient) -> None:
    missing = await client.post("/v1/quotes", json={"zone": "metro"})
    assert missing.status_code == 422
    extra = await client.post(
        "/v1/quotes",
        json={
            "weight_kg": "1",
            "length_cm": "1",
            "width_cm": "1",
            "height_cm": "1",
            "zone": "metro",
            "service": "ground",
            "customer": "nope",
        },
    )
    assert extra.status_code == 422
    unknown = await client.post(
        "/v1/quotes",
        json={
            "weight_kg": "1",
            "length_cm": "1",
            "width_cm": "1",
            "height_cm": "1",
            "zone": "atlantis",
            "service": "ground",
        },
    )
    assert unknown.status_code == 422
    metrics = await client.get("/metrics")
    assert "ratecard_quotes_total 0\n" in metrics.text


async def test_oversize_dimension_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/v1/quotes",
        json={
            "weight_kg": "1",
            "length_cm": "301",
            "width_cm": "1",
            "height_cm": "1",
            "zone": "metro",
            "service": "ground",
        },
    )
    assert response.status_code == 422
