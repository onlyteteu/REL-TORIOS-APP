from __future__ import annotations

from pathlib import Path
import base64
import sys
import tempfile

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from relatorios_rurais.formatters import format_decimal_br
from relatorios_rurais.models import MissingText, RuralVisitReport
from relatorios_rurais.service import analyze_notes, generate_report_from_notes


CELL_MAP_PATH = ROOT / "config" / "cell_map.yaml"
OUTPUT_DIR = ROOT / "outputs"
TEMPLATE_PARTS_DIR = ROOT / "template_parts"
RECONSTRUCTED_TEMPLATE = ROOT / "RELATÓRIO DE VISITA - MODELO.xlsx"


def find_template() -> Path | None:
    matches = sorted(ROOT.glob("*MODELO.xlsx"))
    if matches:
        return matches[0]
    parts = sorted(TEMPLATE_PARTS_DIR.glob("modelo_*.b64"))
    if not parts:
        return None
    payload = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
    try:
        RECONSTRUCTED_TEMPLATE.write_bytes(base64.b64decode(payload, validate=True))
    except Exception:
        return None
    return RECONSTRUCTED_TEMPLATE


def save_uploaded_template(uploaded_template) -> Path | None:
    if uploaded_template is None:
        return None
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / "_modelo_enviado.xlsx"
    path.write_bytes(uploaded_template.getbuffer())
    return path


def area_value(report: RuralVisitReport, field: str) -> str:
    area = getattr(report, field)
    if area is None:
        return MissingText
    return f"{format_decimal_br(area.hectares)} ha"


def summary_rows(report: RuralVisitReport) -> list[dict[str, str]]:
    return [
        {"Campo": "Cliente", "Valor": report.client_name},
        {"Campo": "Município/UF", "Valor": report.municipality_uf},
        {"Campo": "Nome da propriedade", "Valor": report.property_name},
        {"Campo": "Tipo de exploração", "Valor": report.exploitation_type},
        {"Campo": "Atividades desenvolvidas", "Valor": ", ".join(report.activities) if report.activities else MissingText},
        {"Campo": "Situação produtiva", "Valor": report.productive_situation},
        {"Campo": "Área Total", "Valor": area_value(report, "total_area_hectares")},
        {"Campo": "Área de Pastagens", "Valor": area_value(report, "pasture_area_hectares")},
        {"Campo": "Área de Cultivo", "Valor": area_value(report, "crop_area_hectares")},
        {"Campo": "Atividade principal", "Valor": report.main_activity},
        {"Campo": "Principais culturas", "Valor": ", ".join(report.main_cultures) if report.main_cultures else MissingText},
    ]


def save_uploaded_photos(uploaded_photos, output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for index, uploaded_photo in enumerate(uploaded_photos or [], start=1):
        suffix = Path(uploaded_photo.name).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            suffix = ".jpg"
        path = output_dir / f"foto_{index:02d}{suffix}"
        path.write_bytes(uploaded_photo.getbuffer())
        paths.append(path)
    return paths


def main() -> None:
    st.set_page_config(page_title="Relatório de Visita Rural", layout="centered")
    st.title("Relatório de Visita Rural")

    template_path = find_template()
    if template_path is None:
        st.info("Envie o arquivo modelo .xlsx para gerar o relatório.")
        uploaded_template = st.file_uploader("Arquivo modelo", type=["xlsx"])
        template_path = save_uploaded_template(uploaded_template)
        if template_path is None:
            st.stop()

    notes = st.text_area("Anotações da visita", height=260, key="notes")

    analyze_clicked = st.button("Analisar", type="primary")
    if analyze_clicked:
        if not notes.strip():
            st.warning("Cole as anotações da visita antes de analisar.")
        else:
            st.session_state.report = analyze_notes(notes)

    report = st.session_state.get("report")
    if report:
        st.subheader("Resumo dos dados identificados")
        st.dataframe(summary_rows(report), hide_index=True, use_container_width=True)

        st.subheader("Avisos dos dados não informados")
        if report.missing_warnings:
            for warning in report.missing_warnings:
                st.warning(warning)
        else:
            st.success("Nenhum aviso obrigatório.")

        uploaded_photos = st.file_uploader(
            "Fotos da visita",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="As fotos serão inseridas automaticamente na área de registro fotográfico da planilha.",
        )

        if st.button("Gerar relatório"):
            with tempfile.TemporaryDirectory() as temp_dir:
                photo_paths = save_uploaded_photos(uploaded_photos, Path(temp_dir))
                result = generate_report_from_notes(
                    notes=notes,
                    template_path=template_path,
                    cell_map_path=CELL_MAP_PATH,
                    output_dir=OUTPUT_DIR,
                    photo_paths=photo_paths,
                )
            file_bytes = result.output_path.read_bytes()
            st.success(f"Relatório gerado: {result.output_path.name}")
            st.download_button(
                "Download do arquivo Excel",
                data=file_bytes,
                file_name=result.output_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


if __name__ == "__main__":
    main()
