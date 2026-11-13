"""Importação do certificado da rede (ca-extra.pem)."""

import os
import shutil
import ssl
import subprocess
import tempfile
import unittest

from anotacoes.nucleo import certificados


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


if __name__ == "__main__":
    unittest.main()
