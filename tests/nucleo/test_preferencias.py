import os
import tempfile
import unittest

from anotacoes.nucleo.preferencias import Preferencias


def escrever(caminho, texto):
    with open(caminho, "w", encoding="utf-8") as arq:
        arq.write(texto)


class T(unittest.TestCase):
    def test_ciclo_e_arquivo_ruim(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "p.json")
            p = Preferencias(c)
            self.assertEqual(p.get("tema", "claro"), "claro")       # sem arquivo
            p.definir(tema="escuro", janela={"w": 1300})
            self.assertTrue(p.salvar())
            self.assertEqual(Preferencias(c).get("tema"), "escuro")
            self.assertEqual(Preferencias(c).get("janela")["w"], 1300)
            self.assertFalse(os.path.exists(c + ".tmp"))
            escrever(c, "{ isto não é json")                          # corrompido
            self.assertEqual(Preferencias(c).get("tema", "claro"), "claro")
            escrever(c, "[1, 2]")                                     # tipo errado
            self.assertEqual(Preferencias(c).dados, {})

    def test_alertas_de_pausa(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "p.json")
            p = Preferencias(c)
            self.assertTrue(p.alertas_pausa)                      # padrão: ligado
            p.alertas_pausa = False
            self.assertTrue(p.salvar())
            self.assertFalse(Preferencias(c).alertas_pausa)       # persiste
            p.alertas_pausa = True
            p.salvar()
            self.assertTrue(Preferencias(c).alertas_pausa)
            escrever(c, '{"alertas_pausa": "nao"}')               # valor inválido
            self.assertTrue(Preferencias(c).alertas_pausa)

    def test_horarios_de_pausa(self):
        padrao = {"nr17_1": "14:40", "lanche": "17:00", "nr17_2": "18:10"}
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "p.json")
            p = Preferencias(c)
            self.assertEqual(p.horarios_pausa, padrao)
            p.horarios_pausa = {"nr17_1": "9h30", "lanche": "12:00", "nr17_2": "bad"}
            self.assertTrue(p.salvar())
            self.assertEqual(Preferencias(c).horarios_pausa,
                             {"nr17_1": "09:30", "lanche": "12:00", "nr17_2": "18:10"})
            escrever(c, '{"horarios_pausa": [1, 2]}')                 # tipo errado
            self.assertEqual(Preferencias(c).horarios_pausa, padrao)

    def test_pasta_inexistente_nao_levanta(self):
        p = Preferencias(os.path.join(tempfile.gettempdir(), "nao_existe_xyz", "p.json"))
        p.definir(a=1)
        self.assertFalse(p.salvar())


if __name__ == "__main__":
    unittest.main()
