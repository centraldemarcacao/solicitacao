import os
import tempfile
import unittest

from anotacoes.nucleo import modelos, primeiro_uso
from anotacoes.nucleo.preferencias import Preferencias


class TestModelos(unittest.TestCase):
    def test_ausente_ou_invalido_volta_ao_padrao(self):
        for ruim in (None, "x", 5, {"a": 1}):
            self.assertEqual(modelos.validar_modelos(ruim), modelos.padrao())

    def test_lista_vazia_e_respeitada(self):
        self.assertEqual(modelos.validar_modelos([]), [])

    def test_descarta_itens_ruins_repetidos_e_limita(self):
        lixo = [{"titulo": "A", "texto": "a"}, {"titulo": "a", "texto": "outra"}, 3, {"titulo": ""},
                {"titulo": "B", "texto": "  "}, {"titulo": "C" * 80, "texto": "t" * 999}]
        r = modelos.validar_modelos(lixo)
        self.assertEqual([m["titulo"] for m in r], ["A", "C" * modelos.MAX_TITULO])
        self.assertEqual(len(r[1]["texto"]), modelos.MAX_TEXTO)
        muitos = [{"titulo": f"t{i}", "texto": "x"} for i in range(40)]
        self.assertEqual(len(modelos.validar_modelos(muitos)), modelos.MAX_MODELOS)

    def test_texto_com_modelo(self):
        self.assertEqual(modelos.texto_com_modelo("", "Solicita água.", 100), "Solicita água.")
        self.assertEqual(modelos.texto_com_modelo("  Algo \n", "Água.", 100), "Algo\nÁgua.")
        self.assertIsNone(modelos.texto_com_modelo("x" * 99, "yy", 100))

    def test_preferencias_guardam_modelos_e_primeiro_uso(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = os.path.join(d, "p.json")
            p = Preferencias(caminho)
            self.assertEqual(p.modelos_descricao, modelos.padrao())
            self.assertFalse(p.primeiro_uso_concluido)
            p.modelos_descricao = [{"titulo": "X", "texto": "y"}]
            p.primeiro_uso_concluido = True
            self.assertTrue(p.salvar())
            q = Preferencias(caminho)
            self.assertEqual(q.modelos_descricao, [{"titulo": "X", "texto": "y"}])
            self.assertTrue(q.primeiro_uso_concluido)

    def test_assistente_so_em_instalacao_nova(self):
        self.assertTrue(primeiro_uso.deve_mostrar(False, 0, False, False))
        self.assertFalse(primeiro_uso.deve_mostrar(True, 0, False, False))
        self.assertFalse(primeiro_uso.deve_mostrar(False, 3, False, False))
        self.assertFalse(primeiro_uso.deve_mostrar(False, 0, True, False))
        self.assertFalse(primeiro_uso.deve_mostrar(False, 0, False, True))


if __name__ == "__main__":
    unittest.main()
