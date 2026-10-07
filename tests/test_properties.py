"""Property tests: money stays non-negative and heavier parcels do not get cheaper."""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.quotes import QuoteRequest, build_quote, dimensional_weight_kg

zones = st.sampled_from(["metro", "regional", "crossdock", "frontier", "island"])
services = st.sampled_from(["ground", "priority", "overnight", "express"])
weights = st.decimals(
    min_value="0.001",
    max_value="70",
    places=3,
    allow_nan=False,
    allow_infinity=False,
)
dims = st.decimals(
    min_value="0.1",
    max_value="120",
    places=1,
    allow_nan=False,
    allow_infinity=False,
)


@settings(max_examples=40, deadline=None)
@given(weight=weights, length=dims, width=dims, height=dims, zone=zones, service=services)
def test_quote_is_non_negative_and_adds_up(
    weight: Decimal,
    length: Decimal,
    width: Decimal,
    height: Decimal,
    zone: str,
    service: str,
) -> None:
    request = QuoteRequest(
        weight_kg=weight,
        length_cm=length,
        width_cm=width,
        height_cm=height,
        zone=zone,
        service=service,
    )
    quote = build_quote(request)
    dim = dimensional_weight_kg(length, width, height)
    assert Decimal(quote.dimensional_weight_kg) == dim
    assert Decimal(quote.chargeable_weight_kg) == max(weight, dim)
    assert quote.linehaul_cents >= 0
    assert quote.fuel_cents >= 0
    assert quote.total_cents == quote.linehaul_cents + quote.fuel_cents


@settings(max_examples=25, deadline=None)
@given(
    weight=weights,
    extra=st.decimals(
        min_value="0.001",
        max_value="5",
        places=3,
        allow_nan=False,
        allow_infinity=False,
    ),
    length=dims,
    width=dims,
    height=dims,
    zone=zones,
    service=services,
)
def test_weight_is_monotonic(
    weight: Decimal,
    extra: Decimal,
    length: Decimal,
    width: Decimal,
    height: Decimal,
    zone: str,
    service: str,
) -> None:
    heavier = weight + extra
    if heavier > Decimal("100"):
        return
    light = build_quote(
        QuoteRequest(
            weight_kg=weight,
            length_cm=length,
            width_cm=width,
            height_cm=height,
            zone=zone,
            service=service,
        )
    )
    heavy = build_quote(
        QuoteRequest(
            weight_kg=heavier,
            length_cm=length,
            width_cm=width,
            height_cm=height,
            zone=zone,
            service=service,
        )
    )
    assert heavy.total_cents >= light.total_cents
    assert heavy.linehaul_cents >= light.linehaul_cents


@settings(max_examples=20, deadline=None)
@given(
    weight=weights,
    length=dims,
    width=dims,
    height=dims,
    extra=st.decimals(
        min_value="0.1",
        max_value="10",
        places=1,
        allow_nan=False,
        allow_infinity=False,
    ),
    zone=zones,
    service=services,
)
def test_one_dimension_is_monotonic(
    weight: Decimal,
    length: Decimal,
    width: Decimal,
    height: Decimal,
    extra: Decimal,
    zone: str,
    service: str,
) -> None:
    longer = length + extra
    if longer > Decimal("300"):
        return
    short = build_quote(
        QuoteRequest(
            weight_kg=weight,
            length_cm=length,
            width_cm=width,
            height_cm=height,
            zone=zone,
            service=service,
        )
    )
    long = build_quote(
        QuoteRequest(
            weight_kg=weight,
            length_cm=longer,
            width_cm=width,
            height_cm=height,
            zone=zone,
            service=service,
        )
    )
    assert long.total_cents >= short.total_cents
