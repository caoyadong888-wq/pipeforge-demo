"""Five fictional parcel zones. Rates are sample numbers, not a real tariff."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    code: str
    name: str
    base_cents_per_kg: int


ZONES: tuple[Zone, ...] = (
    Zone("metro", "Metro Core", 420),
    Zone("regional", "Regional Belt", 560),
    Zone("crossdock", "Crossdock Corridor", 710),
    Zone("frontier", "Frontier Reach", 890),
    Zone("island", "Island Hop", 1120),
)

ZONE_BY_CODE: dict[str, Zone] = {zone.code: zone for zone in ZONES}
