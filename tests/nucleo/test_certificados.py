"""Certificados HTTPS: repositório do Windows, ca-extra.pem e importação acumulativa."""

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
import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


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


@unittest.skipUnless(shutil.which("openssl"), "openssl indisponível")
class TestImportarCertificado(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        chave, self.pem = (os.path.join(self.tmp, n) for n in ("k.pem", "c.pem"))
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", chave,
                        "-out", self.pem, "-days", "2", "-subj", "/CN=Teste",
                        "-addext", "basicConstraints=critical,CA:TRUE"],
                       check=True, capture_output=True)
        self.der = os.path.join(self.tmp, "c.cer")
        subprocess.run(["openssl", "x509", "-in", self.pem, "-outform", "DER", "-out", self.der],
                       check=True, capture_output=True)
        self.dados = os.path.join(self.tmp, "dados")

    def test_importa_pem(self):
        destino = certificados.importar_certificado(self.pem, self.dados)
        self.assertEqual(os.path.basename(destino), certificados.NOME_CA_EXTRA)
        self.assertIn("BEGIN CERTIFICATE", open(destino, encoding="ascii").read())

    def test_importa_der_e_converte_para_pem(self):
        destino = certificados.importar_certificado(self.der, self.dados)
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cafile=destino)

    def test_rejeita_arquivo_que_nao_e_certificado(self):
        lixo = os.path.join(self.tmp, "x.txt")
        with open(lixo, "w") as f:
            f.write("nada")
        with self.assertRaises(ValueError):
            certificados.importar_certificado(lixo, self.dados)
        self.assertFalse(os.path.exists(os.path.join(self.dados, certificados.NOME_CA_EXTRA)))

    def test_rejeita_arquivo_inexistente(self):
        with self.assertRaises(ValueError):
            certificados.importar_certificado(os.path.join(self.tmp, "nao.pem"), self.dados)


# Raiz pública real "Sectigo Public Server Authentication Root E46" (exportada do Chrome, com CRLF)
SECTIGO_E46 = (
    "-----BEGIN CERTIFICATE-----\r\n"
    "MIICOjCCAcGgAwIBAgIQQvLM2htpN0RfFf51KBC49DAKBggqhkjOPQQDAzBfMQsw\r\n"
    "CQYDVQQGEwJHQjEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTYwNAYDVQQDEy1T\r\n"
    "ZWN0aWdvIFB1YmxpYyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gUm9vdCBFNDYwHhcN\r\n"
    "MjEwMzIyMDAwMDAwWhcNNDYwMzIxMjM1OTU5WjBfMQswCQYDVQQGEwJHQjEYMBYG\r\n"
    "A1UEChMPU2VjdGlnbyBMaW1pdGVkMTYwNAYDVQQDEy1TZWN0aWdvIFB1YmxpYyBT\r\n"
    "ZXJ2ZXIgQXV0aGVudGljYXRpb24gUm9vdCBFNDYwdjAQBgcqhkjOPQIBBgUrgQQA\r\n"
    "IgNiAAR2+pmpbiDt+dd34wc7qNs9Xzjoq1WmVk/WSOrsfy2qw7LFeeyZYX8QeccC\r\n"
    "WvkEN/U0NSt3zn8gj1KjAIns1aeibVvjS5KToID1AZTc8GgHHs3u/iVStSBDHBv+\r\n"
    "6xnOQ6OjQjBAMB0GA1UdDgQWBBTRItpMWfFLXyY4qp3W7usNw/upYTAOBgNVHQ8B\r\n"
    "Af8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB/zAKBggqhkjOPQQDAwNnADBkAjAn7qRa\r\n"
    "qCG76UeXlImldCBteU/IvZNeWBj7LRoAasm4PdCkT0RHlAFWovgzJQxC36oCMB3q\r\n"
    "4S6ILuH5px0CMk7yn2xVdOOurvulGu7t0vzCAxHrRVxgED1cf5kDW21USAGKcw==\r\n"
    "-----END CERTIFICATE-----\r\n")


def _raiz_de_teste(nome: str) -> bytes:
    chave = ec.generate_private_key(ec.SECP256R1())
    alvo = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, nome)])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(alvo).issuer_name(alvo)
            .public_key(chave.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(agora).not_valid_after(agora + datetime.timedelta(days=2))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(chave, hashes.SHA256()))
    return cert.public_bytes(serialization.Encoding.DER)


class TestAcumular(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.dados = os.path.join(self.tmp, "dados")
        self.der_a, self.der_b = _raiz_de_teste("Raiz A"), _raiz_de_teste("Raiz B")

    def arquivo(self, nome: str, conteudo: bytes) -> str:
        caminho = os.path.join(self.tmp, nome)
        with open(caminho, "wb") as f:
            f.write(conteudo)
        return caminho

    def pem(self, der: bytes) -> bytes:
        return ssl.DER_cert_to_PEM_cert(der).encode("ascii")

    def test_importacoes_se_somam_sem_repetir(self):
        a, b = self.arquivo("a.pem", self.pem(self.der_a)), self.arquivo("b.cer", self.der_b)
        self.assertEqual(certificados.importar_certificado_detalhe(a, self.dados)[1:], (1, 1))
        destino, novos, total = certificados.importar_certificado_detalhe(b, self.dados)
        self.assertEqual((novos, total), (1, 2))
        self.assertEqual(certificados.importar_certificado_detalhe(a, self.dados)[1:], (0, 2))
        self.assertEqual(certificados.certificados_importados(self.dados), [self.der_a, self.der_b])
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_verify_locations(cafile=destino)
        self.assertEqual(ctx.cert_store_stats()["x509_ca"], 2)

    def test_arquivo_com_varios_certificados(self):
        junto = self.arquivo("cadeia.pem", self.pem(self.der_a) + b"\n texto solto \n" + self.pem(self.der_b))
        self.assertEqual(certificados.importar_certificado_detalhe(junto, self.dados)[1:], (2, 2))

    def test_formatos_do_chrome_e_do_windows(self):
        casos = {
            "crlf": SECTIGO_E46.encode("ascii"),
            "lf": SECTIGO_E46.replace("\r\n", "\n").encode("ascii"),
            "bom": b"\xef\xbb\xbf" + SECTIGO_E46.encode("ascii"),
            "utf16": SECTIGO_E46.encode("utf-16"),
            "der": ssl.PEM_cert_to_DER_cert(SECTIGO_E46),
        }
        for nome, conteudo in casos.items():
            with self.subTest(nome):
                pasta = os.path.join(self.tmp, "d_" + nome)
                _d, novos, total = certificados.importar_certificado_detalhe(
                    self.arquivo(nome, conteudo), pasta)
                self.assertEqual((novos, total), (1, 1))
        with open(os.path.join(self.tmp, "d_crlf", certificados.NOME_CA_EXTRA), "rb") as f:
            self.assertNotIn(b"\r", f.read())          # arquivo gravado limpo (só LF)

    def test_erros_claros_e_nada_gravado(self):
        pkcs7 = self.arquivo("x.p7b", b"-----BEGIN PKCS7-----\nMIIB\n-----END PKCS7-----\n")
        with self.assertRaisesRegex(ValueError, "PKCS#7"):
            certificados.importar_certificado(pkcs7, self.dados)
        quebrado = self.arquivo("q.pem", b"-----BEGIN CERTIFICATE-----\n@@@@\n-----END CERTIFICATE-----\n")
        with self.assertRaisesRegex(ValueError, "danificado"):
            certificados.importar_certificado(quebrado, self.dados)
        lixo = self.arquivo("l.txt", b"nada de certificado")
        with self.assertRaises(ValueError):
            certificados.importar_certificado(lixo, self.dados)
        vazio = self.arquivo("v.cer", b"")
        with self.assertRaises(ValueError):
            certificados.importar_certificado(vazio, self.dados)
        self.assertFalse(os.path.exists(os.path.join(self.dados, certificados.NOME_CA_EXTRA)))

    def test_erro_nao_apaga_o_que_ja_estava(self):
        certificados.importar_certificado(self.arquivo("a.pem", self.pem(self.der_a)), self.dados)
        with self.assertRaises(ValueError):
            certificados.importar_certificado(self.arquivo("l.txt", b"lixo"), self.dados)
        self.assertEqual(certificados.certificados_importados(self.dados), [self.der_a])

    def test_contexto_ssl_confia_em_todos_os_importados(self):
        certificados.importar_certificado(self.arquivo("a.pem", self.pem(self.der_a)), self.dados)
        certificados.importar_certificado(self.arquivo("b.pem", self.pem(self.der_b)), self.dados)
        with mock.patch.object(certificados, "pastas_ca_extra", lambda: [self.dados]):
            ctx = certificados.contexto_ssl()
        confiaveis = {c["subject"][0][0][1] for c in ctx.get_ca_certs()}
        self.assertTrue({"Raiz A", "Raiz B"} <= confiaveis)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)     # a verificação continua ligada


if __name__ == "__main__":
    unittest.main()
