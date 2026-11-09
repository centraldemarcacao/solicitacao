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
        def fake(req, timeout=0):
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
        def fake(req, timeout=0):
            return FakeResp(EXE if req.full_url.endswith("e.exe") else HASH.encode())
        with tempfile.TemporaryDirectory() as d, mock.patch("urllib.request.urlopen", fake):
            with self.assertRaises(updater.ErroAtualizacao):
                updater.baixar(info(), d, cancelar=ev)
            self.assertEqual(os.listdir(d), [])

    def test_script(self):
        with tempfile.TemporaryDirectory() as d:
            p = updater.gerar_script_troca(r"C:\Ünï\novo.exe", r"C:\Ünï\app.exe", d)
            with open(p, encoding="utf-8") as arq:
                t = arq.read()
            self.assertIn("chcp 65001", t)
            self.assertIn(r'move /y "C:\Ünï\novo.exe" "C:\Ünï\app.exe"', t)
            self.assertIn('start "" "C:\\Ünï\\app.exe"', t)


if __name__ == "__main__":
    unittest.main()
