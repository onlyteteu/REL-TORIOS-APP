from __future__ import annotations

import re


def _patch_parser_livestock_count() -> None:
    try:
        from relatorios_rurais import parser
    except Exception:
        return

    original = parser._count_heads_from_text

    def count_heads_from_text(value: str) -> int | None:
        count = original(value)
        if count is not None:
            return count
        normalized = parser.normalize_text(value)
        if "gado" not in normalized and "rebanho" not in normalized:
            return None
        matches = re.findall(r"\d{1,6}(?:\.\d{3})*", normalized)
        if not matches:
            return None
        return int(matches[-1].replace(".", ""))

    parser._count_heads_from_text = count_heads_from_text


_patch_parser_livestock_count()
