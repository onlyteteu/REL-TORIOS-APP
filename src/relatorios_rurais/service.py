from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .excel import generate_report_xlsx, load_cell_map, safe_output_name
from .models import RuralVisitReport
from .parser import parse_notes
from .validation import validate_output_file


@dataclass(frozen=True)
class GenerationResult:
    report: RuralVisitReport
    output_path: Path


def analyze_notes(
    notes: str,
    *,
    client_name: str | None = None,
    municipality: str | None = None,
    uf: str | None = None,
) -> RuralVisitReport:
    return parse_notes(notes, client_name=client_name, municipality=municipality, uf=uf)


def generate_report_from_notes(
    *,
    notes: str,
    template_path: Path,
    cell_map_path: Path,
    output_dir: Path,
    client_name: str | None = None,
    municipality: str | None = None,
    uf: str | None = None,
    photo_paths: list[Path] | None = None,
) -> GenerationResult:
    report = analyze_notes(notes, client_name=client_name, municipality=municipality, uf=uf)
    cell_map = load_cell_map(cell_map_path)
    output_pattern = cell_map.get("workbook", {}).get(
        "output_pattern",
        "RELATÓRIO DE VISITA - {client_name}.xlsx",
    )
    output_path = output_dir / safe_output_name(output_pattern, report.client_name)
    written = generate_report_xlsx(
        template_path=template_path,
        output_path=output_path,
        report=report,
        cell_map=cell_map,
        photo_paths=photo_paths or [],
    )
    validate_output_file(
        output_path=output_path,
        written_fields=written,
        cell_map=cell_map,
        expected_photo_count=len(photo_paths or []),
    )
    return GenerationResult(report=report, output_path=output_path)
