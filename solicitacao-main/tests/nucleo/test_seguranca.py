import json
import os
import tempfile
import unittest

from anotacoes.nucleo import seguranca as s


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.caminho = os.path.join(self.tmp.name, "seguranca.json")

    # --- PIN ---------------------------------------------------------------
    def test_pin_ciclo(self):
        seg = s.Seguranca(self.caminho)
        self.assertFalse(seg.ativa)
        self.assertFalse(seg.verificar("1234"))                   # sem PIN definido
        self.assertTrue(seg.ativar("2580", criptografar_backups=True, bloqueio_minutos=10))
        self.assertTrue(seg.ativa)
        self.assertTrue(seg.verificar("2580"))
        self.assertFalse(seg.verificar("2581"))
        self.assertFalse(seg.verificar(""))
        self.assertFalse(seg.verificar(None))
        outra = s.Seguranca(self.caminho)                          # persiste
        self.assertTrue(outra.ativa and outra.verificar("2580") and outra.bloqueio_minutos == 10)

    def test_pin_nao_fica_em_texto_claro(self):
        s.Seguranca(self.caminho).ativar("minha-senha-secreta")
        with open(self.caminho, encoding="utf-8") as f:
            texto = f.read()
        self.assertNotIn("minha-senha-secreta", texto)
        self.assertEqual(set(json.loads(texto)) & {"sal", "hash"}, {"sal", "hash"})

    def test_sal_diferente_a_cada_ativacao(self):
        seg = s.Seguranca(self.caminho)
        seg.ativar("1234"); a = seg._cfg.get("hash")
        seg.ativar("1234"); b = seg._cfg.get("hash")
        self.assertNotEqual(a, b)

    def test_validacao(self):
        self.assertIsNotNone(s.validar_segredo("123"))
        self.assertIsNotNone(s.validar_segredo("x" * 65))
        self.assertIsNone(s.validar_segredo("1234"))
        self.assertIsNone(s.validar_segredo("senha com espaço e acentuação"))
        with self.assertRaises(ValueError):
            s.Seguranca(self.caminho).ativar("12")
        self.assertTrue(s.segredo_fraco("1234") and not s.segredo_fraco("umasenhalonga"))

    def test_unicode_e_desativar(self):
        seg = s.Seguranca(self.caminho)
        seg.ativar("açaí-2026")
        self.assertTrue(seg.verificar("açaí-2026") and not seg.verificar("acai-2026"))
        self.assertTrue(seg.desativar())
        self.assertFalse(seg.ativa or s.Seguranca(self.caminho).ativa)
        self.assertFalse(seg.criptografar_backups)

    def test_arquivo_corrompido_nao_derruba(self):
        with open(self.caminho, "w") as f:
            f.write("{ não é json")
        seg = s.Seguranca(self.caminho)
        self.assertFalse(seg.ativa)
        with open(self.caminho, "w") as f:
            json.dump({"sal": "zz", "hash": "yy"}, f)              # hexadecimal inválido
        seg = s.Seguranca(self.caminho)
        self.assertTrue(seg.ativa)
        self.assertFalse(seg.verificar("1234"))                    # não levanta exceção

    def test_opcoes_de_bloqueio(self):
        seg = s.Seguranca(self.caminho)
        seg.ativar("1234")
        self.assertEqual(seg.bloqueio_minutos, s.BLOQUEIO_PADRAO)
        seg.definir_bloqueio_minutos(15); self.assertEqual(seg.bloqueio_minutos, 15)
        seg.definir_bloqueio_minutos(7);  self.assertEqual(seg.bloqueio_minutos, s.BLOQUEIO_PADRAO)

    # --- criptografia --------------------------------------------------------
    @unittest.skipUnless(s.criptografia_disponivel(), "biblioteca cryptography ausente")
    def test_criptografia_ida_e_volta(self):
        dados = os.urandom(5000) + "Maria da Silva — urgente".encode()
        blob = s.criptografar(dados, "segredo-123")
        self.assertTrue(blob.startswith(s.MAGIA))
        self.assertNotIn(b"Maria da Silva", blob)
        self.assertEqual(s.descriptografar(blob, "segredo-123"), dados)
        self.assertNotEqual(blob, s.criptografar(dados, "segredo-123"))     # sal/nonce novos

    @unittest.skipUnless(s.criptografia_disponivel(), "biblioteca cryptography ausente")
    def test_senha_errada_e_adulteracao(self):
        blob = s.criptografar(b"conteudo", "certa")
        with self.assertRaises(s.SenhaIncorreta):
            s.descriptografar(blob, "errada")
        adulterado = blob[:-1] + bytes([blob[-1] ^ 1])
        with self.assertRaises(s.SenhaIncorreta):
            s.descriptografar(adulterado, "certa")
        for ruim in (b"", b"qualquer coisa", s.MAGIA, b"SQLite format 3\x00" + b"\0" * 100):
            with self.assertRaises(s.ErroCriptografia):
                s.descriptografar(ruim, "certa")

    @unittest.skipUnless(s.criptografia_disponivel(), "biblioteca cryptography ausente")
    def test_arquivos(self):
        origem = os.path.join(self.tmp.name, "a.db")
        cifrado = os.path.join(self.tmp.name, "a.dbx")
        volta = os.path.join(self.tmp.name, "b.db")
        with open(origem, "wb") as f:
            f.write(b"SQLite format 3\x00dados")
        s.criptografar_arquivo(origem, cifrado, "x1y2z3")
        self.assertTrue(s.arquivo_criptografado(cifrado))
        self.assertFalse(s.arquivo_criptografado(origem))
        self.assertFalse(s.arquivo_criptografado(os.path.join(self.tmp.name, "nao_existe")))
        s.descriptografar_arquivo(cifrado, volta, "x1y2z3")
        with open(volta, "rb") as f:
            self.assertEqual(f.read(), b"SQLite format 3\x00dados")
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["a.db", "a.dbx", "b.db"])  # sem sobras .tmp
        with self.assertRaises(s.SenhaIncorreta):
            s.descriptografar_arquivo(cifrado, os.path.join(self.tmp.name, "c.db"), "outra")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "c.db")))

    # --- tentativas ------------------------------------------------------------
    def test_limite_de_tentativas(self):
        agora = [100.0]
        lim = s.LimiteTentativas(relogio=lambda: agora[0])
        for _ in range(2):
            lim.errou()
        self.assertEqual(lim.segundos_restantes(), 0)              # 2 erros: ainda sem espera
        lim.errou()
        self.assertEqual(lim.segundos_restantes(), 5)              # 3º erro: 5 s
        agora[0] += 5
        self.assertEqual(lim.segundos_restantes(), 0)
        lim.errou(); lim.errou()                                   # 5 erros
        self.assertEqual(lim.segundos_restantes(), 30)
        for _ in range(3):
            lim.errou()                                            # 8 erros
        self.assertEqual(lim.segundos_restantes(), 120)
        lim.acertou()
        self.assertEqual((lim.erros, lim.segundos_restantes()), (0, 0))


if __name__ == "__main__":
    unittest.main()
