import unittest

from relatorios_rurais.parser import parse_notes, render_fish_farming, render_livestock


RAW_NOTES = """Divino Oliveira Camargo
Pirenópolis - GO

Fazenda Brejão - 1 alqueires

Peixe (tambaqui, caranha, piau)
2 tanques (25x35) (8x12)

Gado de corte nelore - 15
Engorda

Brachiara

Aluguel 6 alqueires
25 cabeças gado nelore (engorda)
"""


LABELED_CHAT_NOTES = """Sandro Mabel
São Miguel do Araguaia - GO
Nome da Propriedade, Fazenda Boa Sorte
Área Total,700 alqueires
Foco de Produção,Gado de Corte (Fase de Recria)
Rebanho Ativo,2.600 cabeças
Movimentação Atual,Saída de 250 garrotes para confinamento (Destino: Fazenda Conforto)
"""

LABELED_CHAT_NOTES_WITHOUT_COMMAS = """Sandro Mabel
São Miguel do Araguaia - GO
Nome da Propriedade Fazenda Boa Sorte
Área Total 700 alqueires
Foco de Produção Gado de Corte (Fase de Recria)
Rebanho Ativo 2.600 cabeças
Movimentação Atual Saída de 250 garrotes para confinamento (Destino: Fazenda Conforto)
"""

FORM_STYLE_NOTES = """Proprietário / Contato
Sandro Mabel
Localização
São Miguel do Araguaia - GO
Nome da Propriedade
Fazenda Boa Sorte
Área Total
700 alqueires
Foco de Produção
Gado de Corte (Fase de Recria)
Rebanho Ativo
2.600 cabeças
"""


class ParserTest(unittest.TestCase):
    def test_parse_notes_extracts_core_fields(self):
        report = parse_notes(RAW_NOTES)

        self.assertEqual(report.client_name, "Divino Oliveira Camargo")
        self.assertEqual(report.municipality_uf, "Pirenópolis - GO")
        self.assertEqual(report.property_name, "Fazenda Brejão")
        self.assertEqual(report.own_area.display, "1,00 alqueire (4,84 ha)")
        self.assertEqual(report.leased_area.display, "6,00 alqueires (29,04 ha)")
        self.assertEqual(report.total_area.display, "7,00 alqueires (33,88 ha)")
        self.assertEqual(report.exploitation_type, "Arrendado")
        self.assertEqual(report.productive_situation, "Engorda")
        self.assertIsNone(report.pasture_area_hectares)
        self.assertIsNone(report.crop_area_hectares)
        self.assertIn("Brachiaria", report.main_cultures)
        self.assertIn("Pecuária de corte", report.activities)
        self.assertIn("Piscicultura", report.activities)

    def test_labeled_chat_notes_extract_property_area_activity_and_herd(self):
        report = parse_notes(LABELED_CHAT_NOTES)

        self.assertEqual(report.client_name, "Sandro Mabel")
        self.assertEqual(report.municipality_uf, "São Miguel do Araguaia - GO")
        self.assertEqual(report.property_name, "Fazenda Boa Sorte")
        self.assertEqual(report.total_area_hectares.hectares, 3388)
        self.assertIsNone(report.pasture_area_hectares)
        self.assertIsNone(report.crop_area_hectares)
        self.assertEqual(report.main_activity, "Pecuária de corte")
        self.assertEqual(report.productive_situation, "Recria")
        self.assertEqual(len(report.livestock), 1)
        self.assertEqual(report.livestock[0].count_heads, 2600)
        self.assertEqual(report.livestock[0].purpose, "Recria")
        self.assertIn("Saída de 250 garrotes", report.herd_movements[0])
        self.assertNotIn("Nome da propriedade", " ".join(report.missing_warnings))

    def test_labeled_chat_notes_work_without_commas(self):
        report = parse_notes(LABELED_CHAT_NOTES_WITHOUT_COMMAS)

        self.assertEqual(report.client_name, "Sandro Mabel")
        self.assertEqual(report.property_name, "Fazenda Boa Sorte")
        self.assertEqual(report.total_area_hectares.hectares, 3388)
        self.assertEqual(report.main_activity, "Pecuária de corte")
        self.assertEqual(report.productive_situation, "Recria")
        self.assertEqual(report.livestock[0].count_heads, 2600)
        self.assertIn("Saída de 250 garrotes", report.herd_movements[0])

    def test_form_style_notes_with_titles_on_separate_lines(self):
        report = parse_notes(FORM_STYLE_NOTES)

        self.assertEqual(report.client_name, "Sandro Mabel")
        self.assertEqual(report.municipality_uf, "São Miguel do Araguaia - GO")
        self.assertEqual(report.property_name, "Fazenda Boa Sorte")
        self.assertEqual(report.total_area_hectares.hectares, 3388)
        self.assertEqual(report.main_activity, "Pecuária de corte")
        self.assertEqual(report.productive_situation, "Recria")
        self.assertEqual(report.livestock[0].count_heads, 2600)
        warnings = " ".join(report.missing_warnings)
        self.assertNotIn("Nome da propriedade", warnings)

    def test_render_sections_are_conservative(self):
        report = parse_notes(RAW_NOTES)

        livestock = render_livestock(report.livestock)
        fish = render_fish_farming(report.fish_farming)

        self.assertIn("15 cabeças", livestock)
        self.assertIn("25 cabeças", livestock)
        self.assertIn("tambaqui, caranha, piau", fish)
        self.assertIn("25x35", fish)


if __name__ == "__main__":
    unittest.main()
