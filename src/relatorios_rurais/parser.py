from __future__ import annotations

from decimal import Decimal
import re

from .formatters import format_decimal_br, format_integer_br, normalize_text, parse_decimal_br, quantize_2
from .models import (
    AreaInfo,
    FishFarmingInfo,
    FishTankInfo,
    HectareAreaInfo,
    LivestockInfo,
    MachineInfo,
    MissingText,
    RuralVisitReport,
)


LOCATION_RE = re.compile(r"^(?P<municipio>.+?)\s*[-/]\s*(?P<uf>[A-Za-z]{2})$")
AREA_RE = re.compile(r"(?P<value>\d{1,9}(?:\.\d{3})*(?:[.,]\d+)?)\s*(?P<unit>alqueir(?:e|es)|ha|hectares?)", re.I)
PROPERTY_RE = re.compile(r"^(?P<name>(?:fazenda|sitio|sítio|chacara|chácara|estancia|estância|propriedade)\b.*?)(?:\s*[-–]\s*(?P<area>\d+(?:[.,]\d+)?)\s*(?P<unit>alqueir(?:e|es)|ha|hectares?))?$", re.I)
LEASED_RE = re.compile(r"\b(?:aluguel|arrendamento|arrendada|arrendado|alugada|alugado)\b.*?(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>alqueir(?:e|es)|ha|hectares?)", re.I)
DIMENSION_RE = re.compile(r"\((?P<dim>\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?)\)", re.I)

FORAGE_TERMS = {
    "brachiaria": "Brachiaria",
    "brachiara": "Brachiaria",
    "braquiaria": "Brachiaria",
    "mombaca": "Mombaça",
    "massai": "Massai",
    "andropogon": "Andropogon",
    "tifton": "Tifton",
    "capim": "Capim",
}
MACHINE_KEYWORDS = ["trator", "colheitadeira", "plantadeira", "pulverizador", "grade", "arado", "roçadeira", "rocadeira", "ensiladeira", "caminhão", "caminhao", "caminhonete", "implemento", "irrigação", "irrigacao", "pivô", "pivo", "bomba"]
MACHINE_BRANDS = ["John Deere", "Massey Ferguson", "New Holland", "Valtra", "Case IH", "Case", "Ford", "Yanmar", "Tatu", "Baldan", "Jacto", "Kuhn", "Stara"]

LABEL_TO_FIELD = {
    "cliente": "owner",
    "produtor": "owner",
    "dono": "owner",
    "proprietario": "owner",
    "propriet?rio": "owner",
    "proprietario / contato": "owner",
    "propriet?rio / contato": "owner",
    "proprietario contato": "owner",
    "propriet?rio contato": "owner",
    "proprietario/contato": "owner",
    "propriet?rio/contato": "owner",
    "contato": "owner",
    "localizacao": "location",
    "localização": "location",
    "localiza??o": "location",
    "nome da propriedade": "property_name",
    "propriedade": "property_name",
    "imovel": "property_name",
    "imovel rural": "property_name",
    "area total": "total_area",
    "rea total": "total_area",
    "area consolidada": "total_area",
    "area da propriedade": "total_area",
    "area de pastagem": "pasture_area",
    "rea de pastagem": "pasture_area",
    "areas de pastagens": "pasture_area",
    "area pastagem": "pasture_area",
    "pastagens": "pasture_area",
    "tipo de exploracao": "exploitation_type",
    "tipo de exploração": "exploitation_type",
    "tipo de explora??o": "exploitation_type",
    "foco de producao": "production_focus",
    "foco de produção": "production_focus",
    "foco de produ??o": "production_focus",
    "atividade principal": "production_focus",
    "atividade": "production_focus",
    "situacao produtiva": "productive_situation",
    "situação produtiva": "productive_situation",
    "situa??o produtiva": "productive_situation",
    "fase": "productive_situation",
    "finalidade": "productive_situation",
    "rebanho ativo": "active_herd",
    "rebanho": "active_herd",
    "plantel": "active_herd",
    "quantidade de rebanho": "active_herd",
    "movimentacao atual": "herd_movement",
    "movimentação atual": "herd_movement",
    "movimenta??o atual": "herd_movement",
    "movimentacao": "herd_movement",
    "movimentação": "herd_movement",
    "movimenta??o": "herd_movement",
    "principais culturas": "cultures",
    "culturas": "cultures",
    "cultura": "cultures",
}
LABELS_BY_LENGTH = sorted(LABEL_TO_FIELD, key=len, reverse=True)


def parse_notes(notes: str, *, client_name: str | None = None, municipality: str | None = None, uf: str | None = None) -> RuralVisitReport:
    lines = [line.strip() for line in notes.splitlines() if line.strip()]
    fields = _extract_fields(lines)

    parsed_client = client_name.strip() if client_name else fields.get("owner", MissingText)
    if parsed_client == MissingText:
        for line in lines:
            if _split_label(line) is None and not LOCATION_RE.match(line):
                parsed_client = line
                break

    parsed_municipality = municipality
    parsed_uf = uf
    location = fields.get("location")
    if location:
        parsed_municipality, parsed_uf = _apply_location(location, parsed_municipality, parsed_uf)
    if not parsed_municipality and not parsed_uf:
        for line in lines:
            if _split_label(line) is None and LOCATION_RE.match(line):
                parsed_municipality, parsed_uf = _apply_location(line, parsed_municipality, parsed_uf)
                break

    property_name = _clean_property_name(fields.get("property_name", "")) or MissingText
    property_area = None
    leased_area = None
    total_area_hectares = _hectare_info("total", fields.get("total_area"), "Área Total")
    pasture_area_hectares = _hectare_info("pasture", fields.get("pasture_area"), "Área de Pastagens")
    livestock: list[LivestockInfo] = []
    fish_farming: FishFarmingInfo | None = None
    forage_species: list[str] = []
    crops: list[str] = []
    pasture_conditions: list[str] = []
    paddocks: list[str] = []
    troughs: list[str] = []
    fences: list[str] = []
    corrals: list[str] = []
    support_structures: list[str] = []
    water_resources: list[str] = []
    herd_movements: list[str] = []
    machines: list[MachineInfo] = []
    explicit_own = False
    explicit_leased = False

    if fields.get("production_focus"):
        focus = _parse_production_focus(fields["production_focus"], f"Foco de Produção: {fields['production_focus']}")
        if focus:
            livestock.append(focus)
        else:
            crops.extend(_split_list_value(fields["production_focus"]))
    if fields.get("productive_situation") and livestock:
        livestock[-1] = livestock[-1].model_copy(update={"purpose": fields["productive_situation"].strip()})
    if fields.get("active_herd"):
        herd = _parse_livestock(fields["active_herd"]) or _parse_livestock(f"Rebanho Ativo {fields['active_herd']}")
        if herd:
            livestock = _merge_livestock_focus(livestock, herd)
    if fields.get("herd_movement"):
        herd_movements.append(fields["herd_movement"].strip())
    if fields.get("cultures"):
        crops.extend(_split_list_value(fields["cultures"]))
    if fields.get("exploitation_type"):
        normalized_type = normalize_text(fields["exploitation_type"])
        explicit_leased = "arrend" in normalized_type or "alug" in normalized_type
        explicit_own = "proprio" in normalized_type or "propria" in normalized_type

    for line in lines:
        labeled = _split_label(line)
        if labeled:
            field, value = labeled
            if field in {"owner", "location", "property_name", "total_area", "pasture_area", "production_focus", "productive_situation", "active_herd", "herd_movement", "cultures", "exploitation_type"}:
                continue
        normalized = normalize_text(line)

        prop_match = PROPERTY_RE.match(line)
        if prop_match and property_name == MissingText:
            property_name = prop_match.group("name").strip(" -–")
            if prop_match.group("area"):
                property_area = AreaInfo(kind="own", value_alqueires=_to_alqueires(prop_match.group("area"), prop_match.group("unit")), source_text=line)
            continue

        if total_area_hectares is None and any(label in normalized for label in ["area total", "rea total", "area consolidada", "area da propriedade"]):
            total_area_hectares = _hectare_info("total", line, line)
            continue
        if pasture_area_hectares is None and any(label in normalized for label in ["area de pastagem", "rea de pastagem", "area pastagem", "pastagens"]):
            pasture_area_hectares = _hectare_info("pasture", line, line)
            continue

        leased_match = LEASED_RE.search(line)
        if leased_match:
            leased_area = AreaInfo(kind="leased", value_alqueires=_to_alqueires(leased_match.group("value"), leased_match.group("unit")), source_text=line)
            explicit_leased = True
            continue

        if normalized.startswith("peixe") or "piscicultura" in normalized:
            fish_farming = FishFarmingInfo(species=_extract_parenthetical_list(line), source_text=line)
            continue
        if "tanque" in normalized:
            tank = FishTankInfo(quantity=_extract_first_int(line), dimensions=[m.group("dim").replace(" ", "") for m in DIMENSION_RE.finditer(line)], source_text=line)
            if fish_farming:
                fish_farming.tanks.append(tank)
            else:
                fish_farming = FishFarmingInfo(tanks=[tank], source_text=line)
            water_resources.append(_render_tank_improvement(tank))
            continue

        livestock_item = _parse_livestock(line)
        if livestock_item:
            livestock.append(livestock_item.model_copy(update={"purpose": livestock_item.purpose or _purpose_from_neighbor(lines, line)}))
            continue
        machine = _parse_machine(line)
        if machine:
            machines.append(machine)
            continue

        for detected in _extract_forage_species(line):
            if detected not in forage_species:
                forage_species.append(detected)
        if _mentions_any(normalized, ["piquete", "piquetes"]):
            paddocks.append(line)
        if _mentions_any(normalized, ["cocho", "cochos", "bebedouro", "bebedouros"]):
            troughs.append(line)
        if _mentions_any(normalized, ["cerca", "cercas"]):
            fences.append(line)
        if _mentions_any(normalized, ["curral", "currais"]):
            corrals.append(line)
        if _mentions_any(normalized, ["sede", "galpao", "galpão", "casa", "deposito", "depósito", "energia"]):
            support_structures.append(line)
        if _mentions_any(normalized, ["rio", "nascente", "represa", "poco", "poço", "corrego", "córrego", "barragem"]):
            water_resources.append(line)
        if _mentions_any(normalized, ["pastagem degradada", "reforma de pastagem", "pastagem formada", "pastagem nativa"]):
            pasture_conditions.append(line)
        if normalized.startswith("cultura") or normalized.startswith("cultivo") or _mentions_any(normalized, ["milho", "soja", "sorgo", "mandioca"]):
            crops.append(line)

    total_area = _sum_areas(property_area, leased_area)
    if total_area_hectares is None and total_area:
        total_area_hectares = HectareAreaInfo(kind="total", hectares=total_area.hectares, source_text=total_area.source_text)
    crop_area_hectares = _calculate_crop_area(total_area_hectares, pasture_area_hectares)
    activities = _build_activities(livestock, fish_farming, crops)
    productive_situation = _build_productive_situation(livestock)
    exploitation_type = _build_exploitation_type(explicit_own, explicit_leased)
    if not machines:
        machines = [MachineInfo()]

    report = RuralVisitReport(
        client_name=parsed_client,
        municipality=parsed_municipality,
        uf=parsed_uf,
        property_name=property_name,
        exploitation_type=exploitation_type,
        productive_situation=productive_situation,
        own_area=property_area,
        leased_area=leased_area,
        total_area=total_area,
        total_area_hectares=total_area_hectares,
        pasture_area_hectares=pasture_area_hectares,
        crop_area_hectares=crop_area_hectares,
        activities=activities,
        main_activity=activities[0] if activities else MissingText,
        main_cultures=_unique([*forage_species, *crops]),
        livestock=livestock,
        fish_farming=fish_farming,
        forage_species=forage_species,
        pasture_conditions=pasture_conditions,
        crops=crops,
        paddocks=paddocks,
        troughs=troughs,
        fences=fences,
        corrals=corrals,
        support_structures=support_structures,
        water_resources=water_resources,
        herd_movements=herd_movements,
        machines=machines,
        technical_comments=_build_technical_comments(activities, total_area_hectares, pasture_area_hectares),
        conclusion=_build_conclusion(activities),
        source_lines=lines,
    )
    return report.model_copy(update={"missing_warnings": build_missing_warnings(report)})


def _extract_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    while index < len(lines):
        split = _split_label(lines[index])
        if not split:
            index += 1
            continue
        field, value = split
        if value:
            fields.setdefault(field, value)
            index += 1
            continue
        value_lines = []
        index += 1
        while index < len(lines) and _split_label(lines[index]) is None:
            value_lines.append(lines[index])
            index += 1
        value = " ".join(value_lines).strip()
        if value:
            fields.setdefault(field, value)
    return fields


def _split_label(line: str) -> tuple[str, str] | None:
    normalized_line = normalize_text(line).lstrip("?¿�").strip()
    for label in LABELS_BY_LENGTH:
        if normalized_line == label:
            return LABEL_TO_FIELD[label], ""
        if normalized_line.startswith(label):
            remainder = normalized_line[len(label):].strip(" ,:-–")
            if remainder and not remainder.startswith("/"):
                return LABEL_TO_FIELD[label], line[_prefix_end(line, label):].strip(" ,:-–")
    return None


def _prefix_end(original: str, normalized_prefix: str) -> int:
    for index in range(1, len(original) + 1):
        if normalize_text(original[:index]).lstrip("?¿�").strip() == normalized_prefix:
            return index
    return len(normalized_prefix)


def _apply_location(value: str, municipality: str | None, uf: str | None) -> tuple[str | None, str | None]:
    match = LOCATION_RE.match(value)
    if match:
        return municipality or match.group("municipio").strip(), uf or match.group("uf").upper()
    return municipality or value.strip(), uf


def _clean_property_name(value: str) -> str:
    value = value.strip(" -–")
    for prefix in ("nome da propriedade", "propriedade"):
        if normalize_text(value).startswith(prefix):
            return value[len(prefix):].strip(" ,:-–")
    return value


def _hectare_info(kind: str, value: str | None, source: str) -> HectareAreaInfo | None:
    if not value:
        return None
    match = AREA_RE.search(value)
    if not match:
        return None
    return HectareAreaInfo(kind=kind, hectares=_to_hectares(match.group("value"), match.group("unit")), source_text=source)


def _to_hectares(value: str, unit: str) -> Decimal:
    number = parse_decimal_br(value)
    return quantize_2(number * Decimal("4.84")) if "alqueir" in normalize_text(unit) else quantize_2(number)


def _to_alqueires(value: str, unit: str) -> Decimal:
    number = parse_decimal_br(value)
    return quantize_2(number / Decimal("4.84")) if "ha" in normalize_text(unit) or "hectare" in normalize_text(unit) else quantize_2(number)


def _calculate_crop_area(total: HectareAreaInfo | None, pasture: HectareAreaInfo | None) -> HectareAreaInfo | None:
    if total is None or pasture is None:
        return None
    hectares = quantize_2(total.hectares - pasture.hectares)
    if hectares < 0:
        return None
    return HectareAreaInfo(kind="crop", hectares=hectares, source_text="Área Total - Área de Pastagens")


def _parse_livestock(line: str) -> LivestockInfo | None:
    normalized = normalize_text(line)
    if "gado" not in normalized and "cabeca" not in normalized and "cabe" not in normalized:
        return None
    count = _count_heads_from_text(line)
    breed = _breed_from_text(line)
    purpose = _purpose_from_text(line)
    if count is None and "gado" not in normalized:
        return None
    return LivestockInfo(species="Gado de corte" if "corte" in normalized else "Gado", breed=breed, count_heads=count, purpose=purpose, source_text=line)


def _parse_production_focus(value: str, source_text: str) -> LivestockInfo | None:
    normalized = normalize_text(value)
    if "gado" not in normalized and "bovino" not in normalized and "pecuaria" not in normalized:
        return None
    return LivestockInfo(species="Gado de corte" if "corte" in normalized else "Gado", breed=_breed_from_text(value), count_heads=None, purpose=_purpose_from_text(value), source_text=source_text)


def _merge_livestock_focus(existing: list[LivestockInfo], herd_item: LivestockInfo) -> list[LivestockInfo]:
    if existing and existing[-1].count_heads is None:
        last = existing[-1]
        existing[-1] = last.model_copy(update={"count_heads": herd_item.count_heads, "breed": last.breed or herd_item.breed, "purpose": last.purpose or herd_item.purpose, "source_text": f"{last.source_text}; {herd_item.source_text}"})
    else:
        existing.append(herd_item)
    return existing


def _count_heads_from_text(value: str) -> int | None:
    match = re.search(r"(?P<count>\d{1,6}(?:\.\d{3})*)\s*cabe", normalize_text(value))
    return int(match.group("count").replace(".", "")) if match else None


def _breed_from_text(value: str) -> str | None:
    normalized = normalize_text(value)
    for breed in ("nelore", "girolando", "angus"):
        if breed in normalized:
            return breed
    return None


def _purpose_from_text(value: str) -> str | None:
    normalized = normalize_text(value)
    if "engorda" in normalized:
        return "Engorda"
    if "recria" in normalized:
        return "Recria"
    if "cria" in normalized:
        return "Cria"
    if "leite" in normalized:
        return "Leite"
    return None


def _purpose_from_neighbor(lines: list[str], current_line: str) -> str | None:
    try:
        index = lines.index(current_line)
    except ValueError:
        return None
    if index + 1 < len(lines) and len(lines[index + 1].split()) <= 3:
        return _purpose_from_text(lines[index + 1])
    return None


def _extract_parenthetical_list(line: str) -> list[str]:
    match = re.search(r"\((.*?)\)", line)
    return [part.strip() for part in match.group(1).split(",") if part.strip()] if match else []


def _extract_first_int(line: str) -> int | None:
    match = re.search(r"\d+", line)
    return int(match.group(0)) if match else None


def _parse_machine(line: str) -> MachineInfo | None:
    normalized = normalize_text(line)
    if not _mentions_any(normalized, MACHINE_KEYWORDS):
        return None
    manufacturer = "-"
    for brand in MACHINE_BRANDS:
        if normalize_text(brand) in normalized:
            manufacturer = brand
            break
    model = "-"
    match = re.search(r"\bmodelo\s+([A-Za-z0-9./-]+)", line, re.I)
    if match:
        model = match.group(1)
    return MachineInfo(description=line, manufacturer=manufacturer, model=model, source_text=line)


def _extract_forage_species(line: str) -> list[str]:
    normalized = normalize_text(line)
    return _unique([label for token, label in FORAGE_TERMS.items() if token in normalized])


def _split_list_value(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;/]", value) if part.strip()]


def _mentions_any(normalized_line: str, tokens: list[str]) -> bool:
    return any(normalize_text(token) in normalized_line for token in tokens)


def _sum_areas(*areas: AreaInfo | None) -> AreaInfo | None:
    valid = [area for area in areas if area is not None]
    if not valid:
        return None
    return AreaInfo(kind="total", value_alqueires=sum((area.value_alqueires for area in valid), Decimal("0")), source_text=" + ".join(area.source_text for area in valid))


def _build_activities(livestock: list[LivestockInfo], fish_farming: FishFarmingInfo | None, crops: list[str]) -> list[str]:
    activities = []
    if livestock:
        activities.append("Pecuária de corte" if any("corte" in normalize_text(item.source_text) or "corte" in normalize_text(item.species) for item in livestock) else "Pecuária")
    if fish_farming:
        activities.append("Piscicultura")
    if crops:
        activities.append("Agricultura")
    return activities


def _build_productive_situation(livestock: list[LivestockInfo]) -> str:
    purposes = _unique([item.purpose for item in livestock if item.purpose])
    return ", ".join(purposes) if purposes else MissingText


def _build_exploitation_type(explicit_own: bool, explicit_leased: bool) -> str:
    if explicit_leased:
        return "Arrendado"
    if explicit_own:
        return "Próprio"
    return MissingText


def _build_technical_comments(activities: list[str], total_area: HectareAreaInfo | None, pasture_area: HectareAreaInfo | None) -> str:
    comments = []
    if activities:
        comments.append(f"Atividades informadas: {', '.join(activities)}.")
    if total_area:
        comments.append(f"Área total informada: {format_decimal_br(total_area.hectares)} ha.")
    if pasture_area:
        comments.append(f"Área de pastagens informada: {format_decimal_br(pasture_area.hectares)} ha.")
    return " ".join(comments) if comments else MissingText


def _build_conclusion(activities: list[str]) -> str:
    if not activities:
        return MissingText
    return "Registro elaborado com base exclusivamente nas informações fornecidas, com indicação de " + ", ".join(activities) + "."


def _render_tank_improvement(tank: FishTankInfo) -> str:
    quantity = f"{tank.quantity} tanques" if tank.quantity is not None else "Tanques"
    dimensions = ", ".join(tank.dimensions)
    return f"{quantity} informados, com dimensões {dimensions}." if dimensions else f"{quantity} informados."


def _unique(items):
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def build_missing_warnings(report: RuralVisitReport) -> list[str]:
    warnings = []
    checks = [
        ("Nome da propriedade", report.property_name),
        ("Tipo de exploração", report.exploitation_type),
        ("Situação produtiva", report.productive_situation),
        ("Área Total", report.total_area_hectares),
        ("Área de Pastagens", report.pasture_area_hectares),
        ("Área de Cultivo", report.crop_area_hectares),
        ("Atividade principal", report.main_activity),
        ("Principais culturas", report.main_cultures),
    ]
    for label, value in checks:
        if value is None or value == MissingText or value == []:
            warnings.append(f"{label}: Não informado.")
    if report.pasture_area_hectares is None:
        warnings.append("Área de Pastagens não foi inferida a partir de espécie forrageira.")
    if report.crop_area_hectares is None:
        warnings.append("Área de Cultivo não foi calculada porque falta Área Total ou Área de Pastagens.")
    if not report.machines or report.machines[0].description == MissingText:
        warnings.append("Máquinas e equipamentos: Não informado; fabricante e modelo preenchidos com '-'.")
    return warnings


def render_livestock(items: list[LivestockInfo]) -> str:
    if not items:
        return MissingText
    parts = []
    for item in items:
        details = [item.species]
        if item.breed:
            details.append(item.breed)
        if item.count_heads is not None:
            details.append(f"{format_integer_br(item.count_heads)} cabeças")
        if item.purpose:
            details.append(item.purpose)
        parts.append(" - ".join(details) + ".")
    return "\n".join(parts)


def render_fish_farming(info: FishFarmingInfo | None) -> str:
    if not info:
        return MissingText
    parts = []
    if info.species:
        parts.append(f"Espécies informadas: {', '.join(info.species)}.")
    for tank in info.tanks:
        parts.append(_render_tank_improvement(tank))
    return " ".join(parts) if parts else MissingText
