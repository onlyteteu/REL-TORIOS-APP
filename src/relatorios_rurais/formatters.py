from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import re
import unicodedata


ALQUEIRE_GOIANO_HECTARES = Decimal("4.84")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip().casefold()


def parse_decimal_br(value: str) -> Decimal:
    cleaned = value.strip().replace(".", "").replace(",", ".")
    return Decimal(cleaned)


def quantize_2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_decimal_br(value: Decimal, decimals: int = 2) -> str:
    quant = Decimal("1") if decimals == 0 else Decimal("0." + "0" * (decimals - 1) + "1")
    number = value.quantize(quant, rounding=ROUND_HALF_UP)
    text = f"{number:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_integer_br(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def pluralize_alqueire(value: Decimal) -> str:
    return "alqueire" if quantize_2(value) == Decimal("1.00") else "alqueires"


def format_area_alqueire(value: Decimal) -> str:
    hectares = quantize_2(value * ALQUEIRE_GOIANO_HECTARES)
    return (
        f"{format_decimal_br(value)} {pluralize_alqueire(value)} "
        f"({format_decimal_br(hectares)} ha)"
    )
