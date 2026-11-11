import unittest
from datetime import date, datetime

from anotacoes.nucleo.pausas import (HORARIOS_PADRAO, PAUSAS, TOLERANCIA_SEGUNDOS, horarios_validos,
                                     interpretar_horario, marcar_avisada, montar_pausas, pausa_devida)


def em(h, m, s=0, dia=11):
    return datetime(2026, 11, dia, h, m, s)


class T(unittest.TestCase):
    def test_horarios_e_tipos(self):
        self.assertEqual([(p.rotulo, p.tipo) for p in PAUSAS],
                         [("14:40", "nr17"), ("17:00", "lanche"), ("18:10", "nr17")])

    def test_dispara_no_segundo_zero_e_nao_antes(self):
        self.assertIsNone(pausa_devida(em(14, 39, 59), set()))
        self.assertEqual(pausa_devida(em(14, 40, 0), set()).rotulo, "14:40")
        self.assertEqual(pausa_devida(em(17, 0, 0), set()).tipo, "lanche")
        self.assertEqual(pausa_devida(em(18, 10, 30), set()).tipo, "nr17")

    def test_fora_de_horario_nao_dispara(self):
        for h, m in ((8, 0), (12, 0), (14, 38), (16, 59), (18, 9), (23, 59)):
            self.assertIsNone(pausa_devida(em(h, m), set()), f"{h}:{m}")

    def test_atraso_dentro_e_fora_da_tolerancia(self):
        self.assertIsNotNone(pausa_devida(em(14, 41, 59), set()))     # 1 min 59 s depois
        self.assertIsNone(pausa_devida(em(14, 42, 1), set()))         # passou de 2 min
        self.assertEqual(TOLERANCIA_SEGUNDOS, 120)

    def test_avisa_uma_vez_por_dia(self):
        avisadas = set()
        p = pausa_devida(em(14, 40), avisadas)
        marcar_avisada(avisadas, p, date(2026, 11, 11))
        self.assertIsNone(pausa_devida(em(14, 40, 1), avisadas))
        self.assertIsNone(pausa_devida(em(14, 41), avisadas))
        self.assertEqual(pausa_devida(em(14, 40, 0, dia=12), avisadas).rotulo, "14:40")  # dia seguinte

    def test_marcar_esquece_dias_anteriores(self):
        avisadas = set()
        marcar_avisada(avisadas, PAUSAS[0], date(2026, 11, 11))
        marcar_avisada(avisadas, PAUSAS[1], date(2026, 11, 12))
        self.assertEqual(avisadas, {(date(2026, 11, 12), "lanche", "17:00")})

    def test_interpretar_horario(self):
        for texto, esperado in (("14:40", (14, 40)), ("14h40", (14, 40)), ("14.40", (14, 40)),
                                ("1440", (14, 40)), ("940", (9, 40)), ("9", (9, 0)),
                                ("9h", (9, 0)), (" 7:05 ", (7, 5))):
            h = interpretar_horario(texto)
            self.assertEqual((h.hour, h.minute), esperado, texto)
        for ruim in ("24:00", "12:60", "abc", "", "14:4", "1:2", "14:40:10", None, 1440):
            self.assertIsNone(interpretar_horario(ruim), repr(ruim))

    def test_horarios_validos_completa_e_corrige(self):
        self.assertEqual(horarios_validos(None), HORARIOS_PADRAO)
        self.assertEqual(horarios_validos("lixo"), HORARIOS_PADRAO)
        r = horarios_validos({"lanche": "16h30", "nr17_1": "xx", "extra": "10:00"})
        self.assertEqual(r, {"nr17_1": "14:40", "lanche": "16:30", "nr17_2": "18:10"})

    def test_horarios_personalizados(self):
        pausas = montar_pausas({"nr17_1": "10:15", "lanche": "12:00", "nr17_2": "15:30"})
        self.assertEqual([p.rotulo for p in pausas], ["10:15", "12:00", "15:30"])
        self.assertIsNone(pausa_devida(em(14, 40), set(), pausas))          # horário antigo não dispara
        self.assertEqual(pausa_devida(em(12, 0), set(), pausas).tipo, "lanche")

    def test_mudar_horario_depois_de_avisar_avisa_de_novo(self):
        avisadas = set()
        antes = montar_pausas()
        p = pausa_devida(em(14, 40), avisadas, antes)
        marcar_avisada(avisadas, p, date(2026, 11, 11))
        depois = montar_pausas({"nr17_1": "14:50"})
        self.assertIsNone(pausa_devida(em(14, 40, 30), avisadas, depois))
        self.assertEqual(pausa_devida(em(14, 50), avisadas, depois).chave, "nr17_1")


if __name__ == "__main__":
    unittest.main()
