import http.server
import os
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from anotacoes.nucleo import certificados


class T(unittest.TestCase):
    def test_deteccao_de_erro_de_certificado(self):
        cert = ssl.SSLCertVerificationError(1, "certificate verify failed")
        self.assertTrue(certificados.erro_de_certificado(cert))
        self.assertTrue(certificados.erro_de_certificado(urllib.error.URLError(cert)))
        try:
            try:
                raise cert
            except ssl.SSLError as e:
                raise RuntimeError("x") from e
        except RuntimeError as e:
            self.assertTrue(certificados.erro_de_certificado(e))
        self.assertFalse(certificados.erro_de_certificado(urllib.error.URLError("sem rede")))
        self.assertFalse(certificados.erro_de_certificado(TimeoutError()))
        self.assertFalse(certificados.erro_de_certificado(None))

    def test_ca_extra_invalido_nao_derruba(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "dados"))
            with open(os.path.join(d, "dados", certificados.NOME_CA_EXTRA), "w") as f:
                f.write("isto não é um certificado")
            with mock.patch.object(certificados, "pasta_programa", lambda: d):
                ctx = certificados.contexto_ssl()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)     # verificação continua ligada
        self.assertTrue(ctx.check_hostname)

    @unittest.skipUnless(shutil.which("openssl"), "openssl não encontrado")
    def test_servidor_https_com_ca_da_instituicao(self):
        """Servidor local com CA própria: falha sem o ca-extra.pem e funciona com ele."""
        with tempfile.TemporaryDirectory() as d:
            def run(*a):
                subprocess.run(a, cwd=d, check=True, capture_output=True)
            run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
                "-keyout", "ca.key", "-out", "ca.pem", "-subj", "/CN=CA Teste",
                "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign")
            run("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", "srv.key",
                "-out", "srv.csr", "-subj", "/CN=localhost")
            with open(os.path.join(d, "ext.cnf"), "w") as f:
                f.write("subjectAltName=DNS:localhost\n")
            run("openssl", "x509", "-req", "-in", "srv.csr", "-CA", "ca.pem", "-CAkey", "ca.key",
                "-CAcreateserial", "-out", "srv.pem", "-days", "2", "-extfile", "ext.cnf")

            class H(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200); self.send_header("Content-Length", "2")
                    self.end_headers(); self.wfile.write(b"ok")
                def log_message(self, *a): pass

            srv = http.server.HTTPServer(("127.0.0.1", 0), H)
            srv_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            srv_ctx.load_cert_chain(os.path.join(d, "srv.pem"), os.path.join(d, "srv.key"))
            srv.socket = srv_ctx.wrap_socket(srv.socket, server_side=True)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = f"https://localhost:{srv.server_address[1]}/"
            try:
                prog = os.path.join(d, "prog")
                os.makedirs(os.path.join(prog, "dados"))
                with mock.patch.object(certificados, "pasta_programa", lambda: prog), \
                        mock.patch.dict(os.environ, {"LOCALAPPDATA": ""}):
                    with self.assertRaises(urllib.error.URLError) as cm:
                        urllib.request.urlopen(url, timeout=5, context=certificados.contexto_ssl())
                    self.assertTrue(certificados.erro_de_certificado(cm.exception))
                    shutil.copy(os.path.join(d, "ca.pem"),
                                os.path.join(prog, "dados", certificados.NOME_CA_EXTRA))
                    with urllib.request.urlopen(url, timeout=5,
                                                context=certificados.contexto_ssl()) as r:
                        self.assertEqual(r.read(), b"ok")
            finally:
                srv.shutdown()


if __name__ == "__main__":
    unittest.main()
