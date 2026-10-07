"""Known quote figures and the rounding rule."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.quotes import (
    FUEL_SURCHARGE_BP,
    SERVICE_MULTIPLIER_BP,
    QuoteRequest,
    build_quote,
    money_cents,
)


def test_money_cents_round_half_up() -> None:
    assert money_cents(Decimal("0.4")) == 0
    assert money_cents(Decimal("0.5")) == 1
    assert money_cents(Decimal("1.5")) == 2
    assert money_cents(Decimal("2.5")) == 3
    assert money_cents(Decimal("161.28")) == 161


def test_ground_metro_example_uses_dimensional_weight() -> None:
    # 40×30×20 / 5000 = 4.8 kg, which beats the 2.5 kg actual weight.
    # Linehaul 4.8 * 420 = 2016. Fuel 2016 * 800 / 10000 = 161.28 → 161.
    request = QuoteRequest(
        weight_kg=Decimal("2.5"),
        length_cm=Decimal("40"),
        width_cm=Decimal("30"),
        height_cm=Decimal("20"),
        zone="metro",
        service="ground",
    )
    quote = build_quote(request)
    assert quote.dimensional_weight_kg == "4.8"
    assert quote.chargeable_weight_kg == "4.8"
    assert quote.base_cents_per_kg == 420
    assert quote.service_multiplier_bp == 10_000
    assert quote.fuel_surcharge_bp == 800
    assert quote.linehaul_cents == 2016
    assert quote.fuel_cents == 161
    assert quote.total_cents == 2177
    assert quote.currency == "USD"
    assert quote.zone_name == "Metro Core"


def test_actual_weight_wins_when_it_is_heavier() -> None:
    request = QuoteRequest(
        weight_kg=Decimal("10"),
        length_cm=Decimal("10"),
        width_cm=Decimal("10"),
        height_cm=Decimal("10"),
        zone="metro",
        service="ground",
    )
    quote = build_quote(request)
    assert quote.dimensional_weight_kg == "0.2"
    assert quote.chargeable_weight_kg == "10"
    assert quote.linehaul_cents == 4200
    assert quote.fuel_cents == 336
    assert quote.total_cents == 4536


def test_priority_multiplier_and_fuel() -> None:
    request = QuoteRequest(
        weight_kg=Decimal("2.5"),
        length_cm=Decimal("40"),
        width_cm=Decimal("30"),
        height_cm=Decimal("20"),
        zone="metro",
        service="priority",
    )
    quote = build_quote(request)
    assert quote.service_multiplier_bp == SERVICE_MULTIPLIER_BP["priority"]
    assert quote.fuel_surcharge_bp == FUEL_SURCHARGE_BP["priority"]
    assert quote.linehaul_cents == 2822
    assert quote.fuel_cents == 296
    assert quote.total_cents == quote.linehaul_cents + quote.fuel_cents


@pytest.mark.parametrize("zone", ["metro", "regional", "crossdock", "frontier", "island"])
@pytest.mark.parametrize("service", ["ground", "priority", "overnight"])
def test_every_lane_is_non_negative(zone: str, service: str) -> None:
    request = QuoteRequest(
        weight_kg=Decimal("1"),
        length_cm=Decimal("10"),
        width_cm=Decimal("10"),
        height_cm=Decimal("10"),
        zone=zone,
        service=service,
    )
    quote = build_quote(request)
    assert quote.linehaul_cents >= 0
    assert quote.fuel_cents >= 0
    assert quote.total_cents == quote.linehaul_cents + quote.fuel_cents


def test_rejects_unknown_zone_and_bad_numbers() -> None:
    with pytest.raises(ValidationError):
        QuoteRequest(
            weight_kg=Decimal("1"),
            length_cm=Decimal("1"),
            width_cm=Decimal("1"),
            height_cm=Decimal("1"),
            zone="atlantis",
            service="ground",
        )
    with pytest.raises(ValidationError):
        QuoteRequest(
            weight_kg="nope",
            length_cm="1",
            width_cm="1",
            height_cm="1",
            zone="metro",
            service="ground",
        )
    with pytest.raises(ValidationError):
        QuoteRequest(
            weight_kg=True,
            length_cm="1",
            width_cm="1",
            height_cm="1",
            zone="metro",
            service="ground",
        )
    with pytest.raises(ValidationError):
        QuoteRequest(
            weight_kg=0,
            length_cm="1",
            width_cm="1",
            height_cm="1",
            zone="metro",
            service="ground",
        )
    with pytest.raises(ValidationError):
        QuoteRequest(
            weight_kg="NaN",
            length_cm="1",
            width_cm="1",
            height_cm="1",
            zone="metro",
            service="ground",
        )
    with pytest.raises(ValidationError):
        QuoteRequest(
            weight_kg={"kg": 1},
            length_cm="1",
            width_cm="1",
            height_cm="1",
            zone="metro",
            service="ground",
        )
