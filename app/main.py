"""HTTP surface for the fictional rate card."""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, ConfigDict
from starlette.applications import Starlette

from app import __version__
from app.metrics import render_metrics
from app.quotes import QuoteBreakdown, QuoteRequest, build_quote
from app.zones import ZONES


class Counters:
    def __init__(self) -> None:
        self.quotes_total = 0
        self.quote_cents_sum = 0


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str


class ZoneOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    name: str
    base_cents_per_kg: int


class ZoneList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zones: list[ZoneOut]


def counters_of(app: Starlette) -> Counters:
    value = app.state.counters
    if not isinstance(value, Counters):
        raise RuntimeError("quote counters are not initialized")
    return value


def create_app() -> FastAPI:
    app = FastAPI(
        title="ratecard-api",
        version=__version__,
        summary="Fictional Kestrel Parcel Co. rate card.",
    )
    app.state.counters = Counters()

    @app.get("/healthz", response_model=Health)
    def healthz() -> Health:
        return Health(status="ok", service="ratecard-api", version=__version__)

    @app.get("/v1/zones", response_model=ZoneList)
    def list_zones() -> ZoneList:
        return ZoneList(
            zones=[
                ZoneOut(code=zone.code, name=zone.name, base_cents_per_kg=zone.base_cents_per_kg)
                for zone in ZONES
            ]
        )

    @app.post("/v1/quotes", response_model=QuoteBreakdown)
    def create_quote(body: QuoteRequest, request: Request) -> QuoteBreakdown:
        breakdown = build_quote(body)
        counters = counters_of(request.app)
        counters.quotes_total += 1
        counters.quote_cents_sum += breakdown.total_cents
        return breakdown

    @app.get("/metrics")
    def metrics(request: Request) -> Response:
        counters = counters_of(request.app)
        body = render_metrics(counters.quotes_total, counters.quote_cents_sum)
        return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")

    return app


app = create_app()
