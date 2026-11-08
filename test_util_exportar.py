import csv, os, tempfile, unittest
from datetime import date

import exportar
import util


class TestDatas(unittest.TestCase):
    H = date(2026, 11, 7)

    def test_formatos(self):
        for texto, esperado in (("10/11/2026", "2026-11-10"), ("10/11", "2026-11-10"),
                                ("10/11/26", "2026-11-10"), ("10-11-2026", "2026-11-10"),
                                ("", None), ("  ", None), ("05/11", "2027-11-05")):
            self.assertEqual(util.interpretar_data(texto, self.H), esperado)

    def test_invalidas(self):
        for ruim in ("abc", "31/02/2026", "32/01/2026", "1/2/3/4"):
            with self.assertRaises(ValueError):
                util.interpretar_data(ruim, self.H)
        with self.assertRaises(ValueError):
            util.interpretar_data("05/11/2026", self.H)           # passada
        self.assertEqual(util.interpretar_data("05/11/2026", self.H, permitir_passado=True), "2026-11-05")

    def test_rotulos(self):
        r = lambda iso, st="Pendente": util.rotulo_retorno(iso, st, self.H)
        self.assertEqual(r("2026-11-05"), "Atrasado 05/11")
        self.assertEqual(r("2026-11-07"), "Hoje")
        self.assertEqual(r("2026-11-08"), "Amanhã")
        self.assertEqual(r("2026-12-08"), "08/12/2026")
        self.assertEqual(r("2026-11-05", "Atendida"), "05/11/2026")   # atendida: sem alerta
        self.assertEqual(r(None), "")
        self.assertEqual(util.situacao_retorno("2026-11-05", "Atendida", self.H), "")

    def test_periodos(self):
        self.assertEqual(util.inicio_do_periodo("Hoje", self.H), "2026-11-07")
        self.assertEqual(util.inicio_do_periodo("Últimos 7 dias", self.H), "2026-11-01")
        self.assertEqual(util.inicio_do_periodo("Este mês", self.H), "2026-11-01")
        self.assertIsNone(util.inicio_do_periodo("Todo o período", self.H))


class TestExportar(unittest.TestCase):
    REGS = [(1, "2026-11-04 18:45:00", "=CMD()", "99", "linha; com \"aspas\"\nquebra", "Pendente", "2026-11-09", "Urgente"),
            (2, "2026-11-05 09:00:00", "Ana <b>", None, "ok", "Atendida", None, "Normal")]

    def test_csv(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "x.csv")
            self.assertEqual(exportar.exportar_csv(self.REGS, c), 2)
            self.assertTrue(open(c, "rb").read().startswith(b"\xef\xbb\xbf"))
            linhas = list(csv.reader(open(c, encoding="utf-8-sig", newline=""), delimiter=";"))
        self.assertEqual(linhas[1][2], "'=CMD()")
        self.assertEqual(linhas[1][4], "linha; com \"aspas\"\nquebra")
        self.assertEqual(linhas[1][6], "09/11/2026")
        self.assertEqual(linhas[0][7], "Prioridade")
        self.assertEqual(linhas[1][7], "Urgente")
        self.assertEqual(linhas[2][3], "")

    def test_html_escapa(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "x.html")
            exportar.gerar_html_impressao(self.REGS, "Filtro: tudo", c)
            h = open(c, encoding="utf-8").read()
        self.assertIn("Ana &lt;b&gt;", h)
        self.assertNotIn("Ana <b>", h)
        self.assertIn("2 registros", h)


if __name__ == "__main__":
    unittest.main()
