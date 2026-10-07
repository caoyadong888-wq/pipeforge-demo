"""Hand-written Prometheus text. No client library."""

from __future__ import annotations

from app import __version__


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def render_metrics(quotes_total: int, quote_cents_sum: int, version: str | None = None) -> str:
    shown = __version__ if version is None else version
    lines = [
        "# HELP ratecard_quotes_total Successful quotes since process start.",
        "# TYPE ratecard_quotes_total counter",
        f"ratecard_quotes_total {quotes_total}",
        "# HELP ratecard_quote_cents_sum Sum of quoted totals in integer cents.",
        "# TYPE ratecard_quote_cents_sum counter",
        f"ratecard_quote_cents_sum {quote_cents_sum}",
        "# HELP ratecard_info Build information for this process.",
        "# TYPE ratecard_info gauge",
        (
            "ratecard_info{"
            f'service="{_escape_label("ratecard-api")}",'
            f'version="{_escape_label(shown)}"'
            "} 1"
        ),
        "",
    ]
    return "\n".join(lines)
