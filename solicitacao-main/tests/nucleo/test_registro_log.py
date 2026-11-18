import logging
import os
import tempfile
import unittest

from anotacoes.nucleo import registro_log


def _ler(caminho):
    with open(caminho, encoding="utf-8") as arq:
        return arq.read()


class TestRegistroLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        registro_log.desligar()
        self.tmp.cleanup()

    def test_grava_em_erros_log(self):
        caminho = registro_log.configurar(self.tmp.name)
        self.assertEqual(os.path.basename(caminho), "erros.log")
        try:
            raise OSError("falha de teste")
        except OSError:
            logging.getLogger("anotacoes.teste").warning("algo falhou", exc_info=True)
        registro_log.desligar()
        texto = _ler(caminho)
        self.assertIn("WARNING anotacoes.teste: algo falhou", texto)
        self.assertIn("OSError: falha de teste", texto)

    def test_debug_nao_entra_no_arquivo(self):
        caminho = registro_log.configurar(self.tmp.name)
        logging.getLogger("anotacoes.teste").debug("ruído")
        registro_log.desligar()
        self.assertFalse(os.path.exists(caminho) and "ruído" in _ler(caminho))

    def test_rotaciona_ao_passar_do_limite(self):
        original = registro_log.MAX_BYTES
        registro_log.MAX_BYTES = 2000
        try:
            caminho = registro_log.configurar(self.tmp.name)
            for i in range(100):
                logging.getLogger("anotacoes.teste").error("linha %d %s", i, "x" * 50)
            registro_log.desligar()
        finally:
            registro_log.MAX_BYTES = original
        self.assertTrue(os.path.exists(caminho + ".1"))
        self.assertLessEqual(len([n for n in os.listdir(self.tmp.name) if n.startswith("erros.log")]),
                             registro_log.COPIAS + 1)

    def test_reconfigurar_nao_duplica_linhas(self):
        registro_log.configurar(self.tmp.name)
        caminho = registro_log.configurar(self.tmp.name)
        logging.getLogger("anotacoes.teste").error("uma vez")
        registro_log.desligar()
        self.assertEqual(_ler(caminho).count("uma vez"), 1)

    def test_pasta_sem_gravacao_nao_explode(self):
        arquivo = os.path.join(self.tmp.name, "arquivo")
        open(arquivo, "w").close()
        self.assertIsNone(registro_log.configurar(os.path.join(arquivo, "subpasta")))


if __name__ == "__main__":
    unittest.main()
