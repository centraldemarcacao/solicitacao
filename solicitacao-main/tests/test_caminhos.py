"""Testes de anotacoes/caminhos.py (onde ficam os dados e os recursos)."""

import os
import unittest
from unittest import mock

from anotacoes import caminhos


class TestCaminhos(unittest.TestCase):
    def test_pasta_programa_em_desenvolvimento_e_a_raiz_do_repositorio(self):
        raiz = caminhos.pasta_programa()
        self.assertTrue(os.path.isdir(os.path.join(raiz, "anotacoes")))
        self.assertTrue(os.path.isfile(os.path.join(raiz, "main.py")))

    def test_localiza_recursos_em_assets(self):
        caminho = caminhos.localizar_arquivo("icone.ico")
        self.assertTrue(caminho and caminho.endswith(os.path.join("assets", "icone.ico")))
        self.assertIsNone(caminhos.localizar_arquivo("nao_existe.xyz"))

    def test_empacotado_usa_a_pasta_do_executavel(self):
        with mock.patch.object(caminhos.sys, "frozen", True, create=True), \
                mock.patch.object(caminhos.sys, "executable", os.path.join("C:", "x", "app.exe")):
            self.assertTrue(caminhos.empacotado())
            self.assertEqual(caminhos.pasta_programa(), os.path.join("C:", "x"))


if __name__ == "__main__":
    unittest.main()
