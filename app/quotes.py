"""Quote math for the fictional rate card.

Dimensional weight is length × width × height ÷ 5000, with centimetres and
kilograms. Money is integer cents. Each money step uses ROUND_HALF_UP.
Fuel is a surcharge in basis points applied to the rounded linehaul.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.zones import ZONE_BY_CODE, Zone

DIMENSIONAL_DIVISOR = Decimal("5000")
BASIS_POINTS = Decimal("10000")
MAX_WEIGHT_KG = Decimal("100")
MAX_DIMENSION_CM = Decimal("300")

ServiceLevel = Literal["ground", "priority", "overnight"]

SERVICE_MULTIPLIER_BP: dict[str, int] = {
    "ground": 10_000,
    "priority": 14_000,
    "overnight": 20_500,
}

FUEL_SURCHARGE_BP: dict[str, int] = {
    "ground": 800,
    "priority": 1_050,
    "overnight": 1_300,
}


def money_cents(value: Decimal) -> int:
    """Round a decimal number of cents to an integer with ROUND_HALF_UP."""
    rounded = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(rounded)


def dimensional_weight_kg(length_cm: Decimal, width_cm: Decimal, height_cm: Decimal) -> Decimal:
    return (length_cm * width_cm * height_cm) / DIMENSIONAL_DIVISOR


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight_kg: Decimal = Field(description="Actual weight in kilograms.")
    length_cm: Decimal = Field(description="Length in centimetres.")
    width_cm: Decimal = Field(description="Width in centimetres.")
    height_cm: Decimal = Field(description="Height in centimetres.")
    zone: str = Field(description="Fictional zone code.")
    service: ServiceLevel = Field(description="ground, priority, or overnight.")

    @field_validator("weight_kg", "length_cm", "width_cm", "height_cm", mode="before")
    @classmethod
    def _parse_decimal(cls, value: object) -> Decimal:
        if isinstance(value, bool) or value is None:
            raise ValueError("expected a decimal number")
        if isinstance(value, Decimal):
            parsed = value
        elif isinstance(value, int):
            parsed = Decimal(value)
        elif isinstance(value, float):
            parsed = Decimal(str(value))
        elif isinstance(value, str):
            try:
                parsed = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError("expected a decimal number") from exc
        else:
            raise ValueError("expected a decimal number")
        if not parsed.is_finite():
            raise ValueError("expected a finite number")
        return parsed

    @field_validator("weight_kg", "length_cm", "width_cm", "height_cm")
    @classmethod
    def _check_range(cls, value: Decimal, info: ValidationInfo) -> Decimal:
        limit = MAX_WEIGHT_KG if info.field_name == "weight_kg" else MAX_DIMENSION_CM
        if value <= 0 or value > limit:
            raise ValueError("value is outside the accepted range")
        return value

    @field_validator("zone")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        if value not in ZONE_BY_CODE:
            raise ValueError("unknown zone")
        return value


class QuoteBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone: str
    zone_name: str
    service: str
    weight_kg: str
    dimensional_weight_kg: str
    chargeable_weight_kg: str
    base_cents_per_kg: int
    service_multiplier_bp: int
    fuel_surcharge_bp: int
    linehaul_cents: int
    fuel_cents: int
    total_cents: int
    currency: str


def _kg(value: Decimal) -> str:
    return format(value, "f")


def build_quote(request: QuoteRequest) -> QuoteBreakdown:
    zone: Zone = ZONE_BY_CODE[request.zone]
    dim_kg = dimensional_weight_kg(request.length_cm, request.width_cm, request.height_cm)
    chargeable = request.weight_kg if request.weight_kg >= dim_kg else dim_kg
    multiplier = SERVICE_MULTIPLIER_BP[request.service]
    fuel_bp = FUEL_SURCHARGE_BP[request.service]
    linehaul_raw = chargeable * Decimal(zone.base_cents_per_kg) * Decimal(multiplier) / BASIS_POINTS
    linehaul = money_cents(linehaul_raw)
    fuel = money_cents(Decimal(linehaul) * Decimal(fuel_bp) / BASIS_POINTS)
    return QuoteBreakdown(
        zone=zone.code,
        zone_name=zone.name,
        service=request.service,
        weight_kg=_kg(request.weight_kg),
        dimensional_weight_kg=_kg(dim_kg),
        chargeable_weight_kg=_kg(chargeable),
        base_cents_per_kg=zone.base_cents_per_kg,
        service_multiplier_bp=multiplier,
        fuel_surcharge_bp=fuel_bp,
        linehaul_cents=linehaul,
        fuel_cents=fuel,
        total_cents=linehaul + fuel,
        currency="USD",
    )
