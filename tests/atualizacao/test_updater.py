import hashlib, os, tempfile, threading, unittest
from unittest import mock

from anotacoes.atualizacao import updater


class FakeResp:
    def __init__(self, dados, url="https://github.com/x", total=None):
        self._d, self._u, self.headers = dados, url, {"Content-Length": str(total or len(dados))}
        self._pos = 0
    def read(self, n=-1):
        b = self._d[self._pos:] if n < 0 else self._d[self._pos:self._pos + n]
        self._pos += len(b); return b
    def geturl(self): return self._u
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def close(self): pass


EXE = b"MZ" + b"\x00" * 1000
HASH = hashlib.sha256(EXE).hexdigest()


def info():
    return updater.InfoAtualizacao("2.2", "", "https://github.com/a/e.exe",
                                   "https://github.com/a/h.txt", len(EXE))


class T(unittest.TestCase):
    def test_versoes(self):
        self.assertTrue(updater.e_mais_nova("v2.10", "2.9"))
        self.assertFalse(updater.e_mais_nova("2.1", "2.1"))
        self.assertFalse(updater.e_mais_nova("2.0", "2.1"))
        self.assertFalse(updater.e_mais_nova("abc", "2.1"))

    def test_release(self):
        base = {"tag_name": "v2.2", "body": "x", "assets": [
            {"name": "AnotacoesHospitalares.exe", "browser_download_url": "u1", "size": 5},
            {"name": "SHA256.txt", "browser_download_url": "u2"}]}
        self.assertEqual(updater.interpretar_release(base).versao, "2.2")
        base["assets"].pop()  # sem assinatura -> recusa
        self.assertIsNone(updater.interpretar_release(base))

    def test_hosts(self):
        self.assertTrue(updater._url_segura("https://objects.githubusercontent.com/a"))
        self.assertFalse(updater._url_segura("http://github.com/a"))
        self.assertFalse(updater._url_segura("https://github.com.evil.io/a"))
        self.assertFalse(updater._url_segura("https://evilgithub.com/a"))

    def _baixar(self, exe, hash_txt):
        def fake(req, timeout=0, **_kw):
            return FakeResp(exe if req.full_url.endswith("e.exe") else hash_txt.encode())
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen", fake):
            try:
                return updater.baixar(info(), d), os.listdir(d)
            except updater.ErroAtualizacao as e:
                return e, os.listdir(d)

    def test_download_ok(self):
        r, arquivos = self._baixar(EXE, f"{HASH}  AnotacoesHospitalares.exe")
        self.assertTrue(str(r).endswith("novo.exe"))

    def test_hash_errado(self):
        r, arquivos = self._baixar(EXE, "0" * 64)
        self.assertIsInstance(r, updater.ErroAtualizacao)
        self.assertEqual(arquivos, [])  # nada sobra

    def test_nao_executavel(self):
        ruim = b"XX" + b"\x00" * 100
        r, _ = self._baixar(ruim, hashlib.sha256(ruim).hexdigest())
        self.assertIsInstance(r, updater.ErroAtualizacao)

    def test_cancelar(self):
        ev = threading.Event(); ev.set()
        def fake(req, timeout=0, **_kw):
            return FakeResp(EXE if req.full_url.endswith("e.exe") else HASH.encode())
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen", fake):
            with self.assertRaises(updater.ErroAtualizacao):
                updater.baixar(info(), d, cancelar=ev)
            self.assertEqual(os.listdir(d), [])

    def test_release_com_nome_novo_ou_antigo_do_exe(self):
        def rel(*nomes):
            return {"tag_name": "v9.9.9", "assets": [
                {"name": n, "browser_download_url": "u:" + n, "size": 5} for n in nomes]}
        for nomes, esperado in (
                (("Anotacoes.exe", "AnotacoesHospitalares.exe", "SHA256.txt"), "u:Anotacoes.exe"),
                (("AnotacoesHospitalares.exe", "SHA256.txt"), "u:AnotacoesHospitalares.exe"),
                (("Anotacoes.exe", "SHA256.txt"), "u:Anotacoes.exe")):
            self.assertEqual(updater.interpretar_release(rel(*nomes)).url_exe, esperado)
        self.assertIsNone(updater.interpretar_release(rel("Anotacoes.exe")))   # sem SHA256

    def test_erro_de_certificado_tem_mensagem_clara(self):
        import ssl, urllib.error
        def fake(req, timeout=0, **_kw):
            raise urllib.error.URLError(ssl.SSLCertVerificationError(1, "unable to get local issuer certificate"))
        with mock.patch("urllib.request.urlopen", fake):
            with self.assertRaises(updater.ErroAtualizacao) as cm:
                updater.buscar_ultima("usuario/repo")
        self.assertIn("Importar certificado", str(cm.exception))
        self.assertNotIn("CERTIFICATE_VERIFY_FAILED", str(cm.exception))

    def test_usa_verificacao_de_certificado(self):
        visto = {}
        def fake(req, timeout=0, context=None, **_kw):
            visto["ctx"] = context
            raise OSError("parou aqui")
        with mock.patch("urllib.request.urlopen", fake):
            with self.assertRaises(updater.ErroAtualizacao):
                updater.buscar_ultima("usuario/repo")
        import ssl
        self.assertEqual(visto["ctx"].verify_mode, ssl.CERT_REQUIRED)

    def test_script(self):
        with tempfile.TemporaryDirectory() as d:
            p = updater.gerar_script_troca(r"C:\Ünï\novo.exe", r"C:\Ünï\app.exe", d, pid=4321)
            with open(p, encoding="utf-8", newline="") as arq:   # newline="": vê os \r\n reais
                t = arq.read()
            self.assertIn("chcp 65001", t)
            self.assertIn(r'move /y "C:\Ünï\novo.exe" "C:\Ünï\app.exe"', t)
            self.assertIn('start "" "C:\\Ünï\\app.exe"', t)
            self.assertIn('tasklist /FI "PID eq 4321" /NH 2>nul | find " 4321 "', t)          # espera o programa fechar
            self.assertIn("atualizacao.log", t)                      # diagnóstico
            self.assertTrue(t.endswith("\r\n") and "\n" not in t.replace("\r\n", ""))

    def test_script_nunca_fica_em_laco_infinito(self):
        with tempfile.TemporaryDirectory() as d:
            t = open(updater.gerar_script_troca("n.exe", "a.exe", d, pid=7), encoding="utf-8").read()
        # todo "goto" que volta a um rótulo de repetição passa antes por um limite
        self.assertIn("if %espera% GEQ 60 goto fechou", t)
        self.assertIn("if %t% GEQ 30 goto fim", t)
        self.assertLess(t.index("if %t% GEQ 30"), t.index("goto trocar"))
        self.assertLess(t.index("if %espera% GEQ 60"), t.index("goto esperar"))

    def test_script_sem_pid_e_com_porcentagem(self):
        with tempfile.TemporaryDirectory() as d:
            t = open(updater.gerar_script_troca(r"C:\a%b\n.exe", r"C:\a%b\x.exe", d),
                     encoding="utf-8").read()
        self.assertNotIn("tasklist", t)
        self.assertIn(r'"C:\a%%b\x.exe"', t)                      # % dobrado no .bat

    # --- troca do .exe ----------------------------------------------------
    def _pasta_com_exes(self, d):
        atual, novo = os.path.join(d, "app.exe"), os.path.join(d, "AnotacoesHospitalares.novo.exe")
        for caminho, texto in ((atual, b"MZ-antigo"), (novo, b"MZ-novo")):
            with open(caminho, "wb") as f:
                f.write(texto)
        return atual, novo

    def _ler(self, caminho):
        with open(caminho, "rb") as f:
            return f.read()

    def test_troca_direta_sem_script(self):
        with tempfile.TemporaryDirectory() as d:
            atual, novo = self._pasta_com_exes(d)
            updater.aplicar_atualizacao(novo, atual)
            self.assertEqual(self._ler(atual), b"MZ-novo")
            self.assertEqual(self._ler(atual + ".anterior"), b"MZ-antigo")
            self.assertFalse(os.path.exists(novo))

    def test_troca_substitui_anterior_antigo(self):
        with tempfile.TemporaryDirectory() as d:
            atual, novo = self._pasta_com_exes(d)
            with open(atual + ".anterior", "wb") as f:
                f.write(b"MZ-muito-antigo")
            updater.aplicar_atualizacao(novo, atual)
            self.assertEqual(self._ler(atual + ".anterior"), b"MZ-antigo")

    def test_falha_ao_renomear_nao_altera_nada(self):
        with tempfile.TemporaryDirectory() as d:
            atual, novo = self._pasta_com_exes(d)
            with mock.patch.object(updater.os, "replace", side_effect=PermissionError("em uso")):
                with self.assertRaises(updater.ErroAtualizacao):
                    updater.aplicar_atualizacao(novo, atual)
            self.assertEqual(self._ler(atual), b"MZ-antigo")
            self.assertEqual(self._ler(novo), b"MZ-novo")

    def test_falha_ao_colocar_novo_restaura_o_antigo(self):
        with tempfile.TemporaryDirectory() as d:
            atual, novo = self._pasta_com_exes(d)
            real = os.replace
            def replace(origem, destino):
                if origem == novo:
                    raise PermissionError("bloqueado")
                return real(origem, destino)
            with mock.patch.object(updater.os, "replace", replace):
                with self.assertRaises(updater.ErroAtualizacao):
                    updater.aplicar_atualizacao(novo, atual)
            self.assertEqual(self._ler(atual), b"MZ-antigo")          # versão que funcionava volta
            self.assertFalse(os.path.exists(atual + ".anterior"))

    def _executar(self, d, falhar_troca=False, falhar_reabrir=False):
        chamadas = []
        def fake_popen(args, **kw):
            if falhar_reabrir and args[0] != "cmd":
                raise OSError("não abriu")
            chamadas.append((args, kw))
        atual, novo = self._pasta_com_exes(d)
        trocar = mock.patch.object(updater, "aplicar_atualizacao",
                                   side_effect=updater.ErroAtualizacao("preso")) if falhar_troca \
            else mock.patch.object(updater, "aplicar_atualizacao", wraps=updater.aplicar_atualizacao)
        with mock.patch.object(updater.sys, "executable", atual), \
                mock.patch.object(updater.subprocess, "Popen", fake_popen), trocar:
            return updater.executar_troca(novo), chamadas, atual

    def test_executar_troca_normal_reabre_sem_janela_e_sem_script(self):
        with tempfile.TemporaryDirectory() as d:
            resultado, chamadas, atual = self._executar(d)
            self.assertEqual(resultado, "direta")
            self.assertEqual(self._ler(atual), b"MZ-novo")
            self.assertFalse(os.path.exists(os.path.join(d, "atualizar.bat")))   # nenhum script
            (args, kw), = chamadas
            self.assertEqual(args, [atual])                                      # só reabre o programa
            self.assertFalse(kw["creationflags"] & 0x00000008)                  # sem DETACHED_PROCESS
            self.assertEqual(kw["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")

    def test_executar_troca_reserva_usa_script_oculto(self):
        with tempfile.TemporaryDirectory() as d:
            resultado, chamadas, atual = self._executar(d, falhar_troca=True)
            self.assertEqual(resultado, "script")
            self.assertTrue(os.path.isfile(os.path.join(d, "atualizar.bat")))
            (args, kw), = chamadas
            self.assertEqual(args[:2], ["cmd", "/c"])
            self.assertTrue(kw["creationflags"] & 0x08000000)                   # CREATE_NO_WINDOW
            self.assertFalse(kw["creationflags"] & 0x00000008)                  # nunca DETACHED_PROCESS

    def test_executar_troca_manual_quando_nao_consegue_reabrir(self):
        with tempfile.TemporaryDirectory() as d:
            resultado, _, atual = self._executar(d, falhar_reabrir=True)
            self.assertEqual(resultado, "manual")
            self.assertEqual(self._ler(atual), b"MZ-novo")

    def test_restos_e_pendencia(self):
        with tempfile.TemporaryDirectory() as d:
            atual, novo = self._pasta_com_exes(d)
            with open(atual + ".anterior", "wb") as f:
                f.write(b"x")
            with mock.patch.object(updater.sys, "executable", atual), \
                    mock.patch.object(updater.sys, "frozen", True, create=True):
                self.assertTrue(updater.ficou_pendente())       # .novo.exe sobrou: troca não aconteceu
                updater.limpar_restos()
                self.assertFalse(os.path.exists(atual + ".anterior"))
                os.remove(novo)
                self.assertFalse(updater.ficou_pendente())
            self.assertFalse(updater.ficou_pendente())          # fora do .exe (desenvolvimento): nunca



if __name__ == "__main__":
    unittest.main()
