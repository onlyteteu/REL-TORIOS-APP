from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .inspect import write_inspection_json
from .models import GenerationInput
from .service import generate_report_from_notes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="relatorio-rural",
        description="Gera relatorios de visita rural em Excel a partir de anotacoes brutas.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Gerar relatorio preenchido.")
    generate.add_argument("--model", required=True, type=Path, help="Arquivo modelo .xlsx preservado.")
    generate.add_argument("--notes-file", type=Path, help="Arquivo .txt com anotacoes brutas.")
    generate.add_argument("--notes", help="Texto bruto diretamente na linha de comando.")
    generate.add_argument("--client-name", help="Nome do cliente, se quiser sobrescrever o texto.")
    generate.add_argument("--municipality", help="Municipio, se quiser sobrescrever o texto.")
    generate.add_argument("--uf", help="UF, se quiser sobrescrever o texto.")
    generate.add_argument("--cell-map", type=Path, default=Path("config/cell_map.yaml"), help="Mapa de celulas YAML.")
    generate.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Pasta de saida.")

    inspect = subparsers.add_parser("inspect-template", help="Inspecionar abas, mesclagens e rotulos do modelo.")
    inspect.add_argument("--workbook", required=True, type=Path, help="Arquivo .xlsx a inspecionar.")
    inspect.add_argument("--output", type=Path, default=Path("outputs/template_labels.json"), help="JSON de saida.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect-template":
            write_inspection_json(args.workbook, args.output)
            print(f"Inspecao salva em: {args.output.resolve()}")
            return 0
        if args.command == "generate":
            return _generate(args)
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


def _generate(args: argparse.Namespace) -> int:
    notes = _load_notes(args.notes, args.notes_file)
    generation_input = GenerationInput(
        notes=notes,
        template_path=args.model,
        output_dir=args.output_dir,
        cell_map_path=args.cell_map,
        client_name=args.client_name,
        municipality=args.municipality,
        uf=args.uf,
    )
    result = generate_report_from_notes(
        notes=generation_input.notes,
        template_path=generation_input.template_path,
        cell_map_path=generation_input.cell_map_path,
        output_dir=generation_input.output_dir,
        client_name=generation_input.client_name,
        municipality=generation_input.municipality,
        uf=generation_input.uf,
    )
    print(f"Relatorio gerado: {result.output_path.resolve()}")
    return 0


def _load_notes(notes: str | None, notes_file: Path | None) -> str:
    if notes:
        return notes
    if notes_file:
        return notes_file.read_text(encoding="utf-8")
    raise ValueError("Informe --notes ou --notes-file.")


if __name__ == "__main__":
    raise SystemExit(main())
