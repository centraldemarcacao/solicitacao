import os
import socket
import ssl
import tempfile
import unittest
import urllib.error
from unittest import mock

from anotacoes.atualizacao import updater
from anotacoes.nucleo import diagnostico as d


def _falha(exc):
    def fake(*a, **k):
        raise exc
    return fake


class T(unittest.TestCase):
    # --- GitHub -----------------------------------------------------------------
    def _github(self, **patches):
        with mock.patch.object(updater, "buscar_ultima", **patches):
            return d.testar_github("usuario/repo")

    def test_github_ok_e_sem_versao(self):
        info = updater.InfoAtualizacao("2.10.1", "", "u", "h", 1)
        r = self._github(return_value=info)
        self.assertEqual((r.estado, "2.10.1" in r.mensagem), (d.OK, True))
        self.assertEqual(self._github(return_value=None).estado, d.AVISO)

    def test_github_certificado_orienta_ca_extra(self):
        causa = urllib.error.URLError(ssl.SSLCertVerificationError(1, "unable to get local issuer certificate"))
        erro = updater.ErroAtualizacao("x"); erro.__cause__ = causa
        r = self._github(side_effect=erro)
        self.assertEqual(r.estado, d.ERRO)
        self.assertIn("ca-extra.pem", r.mensagem)

    def test_github_dns_timeout_http(self):
        for causa, trecho in ((urllib.error.URLError(socket.gaierror(11001, "x")), "DNS"),
                              (urllib.error.URLError(TimeoutError()), "demorou"),
                              (urllib.error.HTTPError("u", 403, "x", {}, None), "limitou"),
                              (urllib.error.HTTPError("u", 404, "x", {}, None), "público")):
            erro = updater.ErroAtualizacao("x"); erro.__cause__ = causa
            r = self._github(side_effect=erro)
            self.assertEqual(r.estado, d.ERRO)
            self.assertIn(trecho, r.mensagem, trecho)

    def test_github_erro_sem_causa_usa_a_mensagem(self):
        r = self._github(side_effect=updater.ErroAtualizacao("Repositório de atualizações não configurado."))
        self.assertIn("não configurado", r.mensagem)

    # --- Supabase ---------------------------------------------------------------
    def test_supabase_nao_configurado_e_pulado(self):
        self.assertEqual(d.testar_supabase(None, None).estado, d.PULADO)
        self.assertEqual(d.testar_supabase("https://x.supabase.co", "").estado, d.PULADO)

    def _supabase(self, efeito):
        with mock.patch("urllib.request.urlopen", **efeito):
            return d.testar_supabase("https://abc.supabase.co/", "chave-secreta")

    def test_supabase_resultados(self):
        ok = mock.MagicMock()
        self.assertEqual(self._supabase({"return_value": ok}).estado, d.OK)
        self.assertEqual(self._supabase({"side_effect": urllib.error.HTTPError("u", 401, "x", {}, None)}).estado, d.AVISO)
        self.assertEqual(self._supabase({"side_effect": urllib.error.HTTPError("u", 500, "x", {}, None)}).estado, d.ERRO)
        cert = urllib.error.URLError(ssl.SSLCertVerificationError(1, "x"))
        self.assertIn("ca-extra.pem", self._supabase({"side_effect": cert}).mensagem)
        self.assertEqual(self._supabase({"side_effect": OSError("sem rede")}).estado, d.ERRO)

    def test_supabase_usa_ssl_verificado_e_nao_vaza_a_chave(self):
        visto = {}
        def fake(req, timeout=0, context=None):
            visto["ctx"], visto["url"] = context, req.full_url
            return mock.MagicMock()
        with mock.patch("urllib.request.urlopen", fake):
            r = d.testar_supabase("https://abc.supabase.co/", "chave-secreta")
        self.assertEqual(visto["ctx"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(visto["url"].endswith("/auth/v1/health"))
        self.assertNotIn("chave-secreta", r.mensagem)

    # --- informações ------------------------------------------------------------
    def test_ultima_linha(self):
        with tempfile.TemporaryDirectory() as t:
            c = os.path.join(t, "a.log")
            self.assertIsNone(d.ultima_linha(c))
            with open(c, "w", encoding="utf-8") as f:
                f.write("primeira\n\nsegunda com acento ç\n\n   \n")
            self.assertEqual(d.ultima_linha(c), "segunda com acento ç")
            with open(c, "w", encoding="utf-8") as f:
                f.write("x\n" * 5000 + "fim")
            self.assertEqual(d.ultima_linha(c), "fim")

    def test_linhas_de_informacao(self):
        with tempfile.TemporaryDirectory() as t:
            banco = os.path.join(t, "dados", "x.db")
            backups = os.path.join(t, "dados", "backups")
            os.makedirs(backups)
            for n in ("backup_1.db", "backup_2.dbx", "backup_3.dbx", "outro.txt"):
                open(os.path.join(backups, n), "wb").close()
            with open(os.path.join(t, "dados", "erros.log"), "w", encoding="utf-8") as f:
                f.write("[2026-11-12] algo\n")
            tab = dict(d.linhas_informacao("2.11.0", banco, backups, True, None, True))
        self.assertEqual(tab["Versão do programa"], "2.11.0")
        self.assertEqual(tab["Backups"], "3 arquivo(s), 2 criptografado(s)")
        self.assertEqual(tab["Proteção por PIN"], "ativada")
        self.assertIn("indisponível", tab["Iniciar com o Windows"])
        self.assertEqual(tab["Último registro de erro"], "[2026-11-12] algo")
        self.assertEqual(tab["Última atualização"], "nenhum")
        self.assertIn("não encontrado", tab["Banco de dados"])
        self.assertNotIn("Maria", " ".join(tab.values()))


if __name__ == "__main__":
    unittest.main()
