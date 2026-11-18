"""Testes da identidade personalizável (identidade.py).
Execute (na raiz do repositório): python -m unittest tests.nucleo.test_identidade -v"""

import json
import os
import tempfile
import unittest

from PIL import Image

from anotacoes.nucleo import identidade
from anotacoes import theme as T
from anotacoes.nucleo.identidade import Identidade, titulo_completo, validar_textos


class TestIdentidade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = os.path.join(self.tmp.name, "dados")
        self.ident = Identidade(self.pasta)
        n, s = T.NOME_INSTITUICAO, T.SUBTITULO
        self.addCleanup(lambda: (setattr(T, "NOME_INSTITUICAO", n), setattr(T, "SUBTITULO", s)))

    def imagem(self, nome="x.png", tamanho=(300, 120), formato="PNG", modo="RGB", cor=(200, 30, 30)):
        caminho = os.path.join(self.tmp.name, nome)
        Image.new(modo, tamanho, cor).save(caminho, format=formato)
        return caminho

    # --- textos --------------------------------------------------------
    def test_validar_textos(self):
        self.assertEqual(validar_textos("  Intesoftware   Desenvolvimento ", " Anotações "),
                         ("Intesoftware Desenvolvimento", "Anotações"))
        self.assertEqual(validar_textos("Só nome", ""), ("Só nome", ""))
        with self.assertRaises(ValueError):
            validar_textos("   ", "x")
        with self.assertRaises(ValueError):
            validar_textos("x" * (identidade.MAX_NOME + 1), "")
        with self.assertRaises(ValueError):
            validar_textos("ok", "y" * (identidade.MAX_SUBTITULO + 1))

    def test_salvar_e_aplicar(self):
        self.assertIsNone(self.ident.carregar())
        self.ident.salvar_textos("Intesoftware Desenvolvimento", "Anotações de clientes")
        self.assertEqual(self.ident.carregar(),
                         ("Intesoftware Desenvolvimento", "Anotações de clientes"))
        self.ident.aplicar()
        self.assertEqual((T.NOME_INSTITUICAO, T.SUBTITULO),
                         ("Intesoftware Desenvolvimento", "Anotações de clientes"))
        with open(os.path.join(self.pasta, "identidade.json"), encoding="utf-8") as a:
            self.assertEqual(json.load(a)["nome"], "Intesoftware Desenvolvimento")   # acentos legíveis

    def test_subtitulo_vazio_e_titulo_completo(self):
        self.ident.salvar_textos("Minha Empresa", "")
        self.ident.aplicar()
        self.assertEqual(titulo_completo(), "Minha Empresa")
        self.ident.salvar_textos("Minha Empresa", "Anotações")
        self.ident.aplicar()
        self.assertEqual(titulo_completo(), "Minha Empresa — Anotações")

    def test_arquivo_corrompido_nao_quebra(self):
        os.makedirs(self.pasta)
        for conteudo in ("{ ruim", "[]", "null", '{"nome": 5}', '{"subtitulo": "x"}', ""):
            with open(os.path.join(self.pasta, "identidade.json"), "w", encoding="utf-8") as a:
                a.write(conteudo)
            self.assertIsNone(self.ident.carregar(), conteudo)
            self.ident.aplicar()     # não pode lançar

    # --- logo e ícone ----------------------------------------------------
    def test_definir_logo_gera_png_e_ico(self):
        self.ident.definir_logo(self.imagem(tamanho=(900, 300)))
        logo, ico = self.ident.caminho_logo(), self.ident.caminho_icone()
        self.assertTrue(logo and ico)
        with Image.open(logo) as im:
            self.assertLessEqual(max(im.size), identidade.LADO_LOGO)
            self.assertAlmostEqual(im.width / im.height, 3.0, delta=0.05)   # proporção mantida
            self.assertEqual(im.mode, "RGBA")
        with Image.open(ico) as im:
            self.assertEqual(im.format, "ICO")
            self.assertIn((32, 32), im.info["sizes"])
            self.assertIn((256, 256), im.info["sizes"])

    def test_formatos_aceitos(self):
        for formato, ext, modo in (("JPEG", "jpg", "RGB"), ("BMP", "bmp", "RGB"),
                                   ("GIF", "gif", "P"), ("PNG", "png", "RGBA"),
                                   ("WEBP", "webp", "RGB"), ("ICO", "ico", "RGBA")):
            c = self.imagem(f"t.{ext}", (64, 64), formato, modo, 0 if modo == "P" else
                            (10, 20, 30, 255) if modo == "RGBA" else (10, 20, 30))
            self.ident.definir_logo(c)
            self.assertTrue(self.ident.caminho_logo(), formato)

    def test_arquivo_que_nao_e_imagem(self):
        falso = os.path.join(self.tmp.name, "falso.png")
        with open(falso, "w") as a:
            a.write("isto não é uma imagem")
        with self.assertRaisesRegex(ValueError, "abrir essa imagem"):
            self.ident.definir_logo(falso)
        self.assertIsNone(self.ident.caminho_logo())

    def test_imagem_ruim_nao_apaga_o_logo_atual(self):
        self.ident.definir_logo(self.imagem())
        def ler(c):
            with open(c, "rb") as a:
                return a.read()
        antes = ler(self.ident.caminho_logo())
        falso = os.path.join(self.tmp.name, "falso.png")
        with open(falso, "w") as a:
            a.write("x")
        with self.assertRaises(ValueError):
            self.ident.definir_logo(falso)
        self.assertEqual(ler(self.ident.caminho_logo()), antes)

    def test_limites_de_tamanho(self):
        c = self.imagem()
        original = identidade.MAX_BYTES_IMAGEM
        identidade.MAX_BYTES_IMAGEM = 10
        try:
            with self.assertRaisesRegex(ValueError, "muito grande"):
                self.ident.definir_logo(c)
        finally:
            identidade.MAX_BYTES_IMAGEM = original
        original = identidade.MAX_PIXELS
        identidade.MAX_PIXELS = 100
        try:
            with self.assertRaisesRegex(ValueError, "dimensões"):
                self.ident.definir_logo(c)
        finally:
            identidade.MAX_PIXELS = original

    def test_arquivo_inexistente(self):
        with self.assertRaises(ValueError):
            self.ident.definir_logo(os.path.join(self.tmp.name, "nao_existe.png"))

    def test_remover_e_restaurar_padrao(self):
        self.ident.definir_logo(self.imagem())
        self.ident.salvar_textos("Outra", "Coisa")
        self.ident.aplicar()
        self.ident.remover_logo()
        self.assertIsNone(self.ident.caminho_logo())
        self.assertIsNone(self.ident.caminho_icone())
        self.ident.definir_logo(self.imagem())
        self.ident.restaurar_padrao()
        self.assertIsNone(self.ident.carregar())
        self.assertIsNone(self.ident.caminho_logo())
        self.assertEqual((T.NOME_INSTITUICAO, T.SUBTITULO), (T.NOME_PADRAO, T.SUBTITULO_PADRAO))
        self.ident.restaurar_padrao()      # repetir não dá erro

    def test_sem_arquivos_temporarios_sobrando(self):
        self.ident.definir_logo(self.imagem())
        self.ident.salvar_textos("A", "B")
        self.assertFalse([f for f in os.listdir(self.pasta) if f.endswith(".tmp")])


if __name__ == "__main__":
    unittest.main()
