"""Importar certificados da rede: cada importação ACRESCENTA (GitHub e Supabase usam raízes
diferentes) e formatos comuns de exportação do Windows/Chrome são aceitos."""

import datetime
import os
import shutil
import ssl
import tempfile
import unittest
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from anotacoes.nucleo import certificados

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
