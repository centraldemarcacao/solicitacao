import os, tempfile, unittest

from preferencias import Preferencias


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
            open(c, "w").write("{ isto não é json")                  # corrompido
            self.assertEqual(Preferencias(c).get("tema", "claro"), "claro")
            open(c, "w").write("[1, 2]")                              # tipo errado
            self.assertEqual(Preferencias(c).dados, {})

    def test_pasta_inexistente_nao_levanta(self):
        p = Preferencias(os.path.join(tempfile.gettempdir(), "nao_existe_xyz", "p.json"))
        p.definir(a=1)
        self.assertFalse(p.salvar())


if __name__ == "__main__":
    unittest.main()
