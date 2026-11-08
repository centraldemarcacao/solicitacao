"""Testes do perfil da empresa (perfil.py). Execute: python -m unittest test_perfil -v"""

import json
import os
import tempfile
import unittest

import perfil
import theme as T


class TestPerfil(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.nome0, self.sub0 = T.NOME_INSTITUICAO, T.SUBTITULO
        self.addCleanup(lambda: (setattr(T, "NOME_INSTITUICAO", self.nome0),
                                 setattr(T, "SUBTITULO", self.sub0)))

    def escrever(self, conteudo, codificacao="utf-8"):
        with open(os.path.join(self.tmp.name, perfil.ARQUIVO), "w", encoding=codificacao) as a:
            a.write(conteudo if isinstance(conteudo, str) else json.dumps(conteudo))

    def test_sem_arquivo_usa_o_padrao(self):
        self.assertEqual(perfil.carregar(self.tmp.name), perfil.PADRAO)

    def test_perfil_valido(self):
        self.escrever({"nome": "Intesoftware Desenvolvimento",
                       "subtitulo": "Anotações de clientes"})
        p = perfil.aplicar(self.tmp.name)
        self.assertEqual(p["nome"], "Intesoftware Desenvolvimento")
        self.assertEqual(T.NOME_INSTITUICAO, "Intesoftware Desenvolvimento")
        self.assertEqual(T.SUBTITULO, "Anotações de clientes")

    def test_arquivo_com_bom_do_bloco_de_notas(self):
        self.escrever(json.dumps({"nome": "Empresa X"}), "utf-8-sig")
        self.assertEqual(perfil.carregar(self.tmp.name)["nome"], "Empresa X")

    def test_campo_ausente_mantem_o_padrao_dele(self):
        self.escrever({"nome": "Só o nome"})
        p = perfil.carregar(self.tmp.name)
        self.assertEqual((p["nome"], p["subtitulo"]),
                         ("Só o nome", perfil.PADRAO["subtitulo"]))

    def test_arquivos_invalidos_nao_quebram(self):
        for conteudo in ("{ não é json", "[]", '"texto"', "", "null",
                         '{"nome": 5, "subtitulo": ["a"]}',
                         '{"nome": "   ", "subtitulo": ""}'):
            self.escrever(conteudo)
            self.assertEqual(perfil.carregar(self.tmp.name), perfil.PADRAO, conteudo)

    def test_limita_tamanho_e_espacos(self):
        self.escrever({"nome": "  Empresa   com   espaços  " + "x" * 100})
        nome = perfil.carregar(self.tmp.name)["nome"]
        self.assertLessEqual(len(nome), perfil.MAX_NOME)
        self.assertTrue(nome.startswith("Empresa com espaços"))

    def test_arquivo_de_exemplo_do_projeto_e_valido(self):
        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "perfil_intesoftware.json"), encoding="utf-8") as a:
            dados = json.load(a)
        self.assertEqual(dados["nome"], "Intesoftware Desenvolvimento")


if __name__ == "__main__":
    unittest.main()
