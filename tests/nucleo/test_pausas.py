import unittest
from datetime import date, datetime

from anotacoes.nucleo.pausas import PAUSAS, TOLERANCIA_SEGUNDOS, marcar_avisada, pausa_devida


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
        self.assertEqual(avisadas, {(date(2026, 11, 12), "17:00")})


if __name__ == "__main__":
    unittest.main()
