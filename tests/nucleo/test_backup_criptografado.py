"""Backups criptografados (.dbx): criação, rotação, restauração e conversão."""
import os
import tempfile
import unittest

from anotacoes.nucleo import seguranca
from anotacoes.nucleo.database import BACKUPS_MANTER, Database

SENHA = "senha-de-teste-9"


@unittest.skipUnless(seguranca.criptografia_disponivel(), "biblioteca cryptography ausente")
class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(os.path.join(self.tmp.name, "teste.db"))
        self.db.inserir("Maria da Silva", "Ramal 1", "Solicita água")
        self.pasta = self.db.pasta_backups()

    def _ligar(self):
        self.db.backup_criptografado = True
        self.db.backup_segredo = SENHA

    def _arquivos(self):
        return sorted(os.listdir(self.pasta))

    def test_backup_criptografado_nao_vaza_dados(self):
        self._ligar()
        caminho = self.db.fazer_backup()
        self.assertTrue(caminho.endswith(".dbx") and seguranca.arquivo_criptografado(caminho))
        with open(caminho, "rb") as f:
            bruto = f.read()
        self.assertNotIn(b"Maria da Silva", bruto)
        self.assertNotIn(b"SQLite format 3", bruto)
        self.assertEqual([n for n in self._arquivos() if not n.endswith(".dbx")], [])  # sem cópia limpa/tmp

    def test_backup_automatico_bloqueado_adia(self):
        self.db.backup_criptografado = True                      # ligado, mas sem senha (tela bloqueada)
        self.assertTrue(self.db.backup_bloqueado())
        self.assertIsNone(self.db.backup_automatico())
        self.assertEqual(self._arquivos(), [])                   # nada em texto aberto
        with self.assertRaises(RuntimeError):
            self.db.fazer_backup()
        self.db.backup_segredo = SENHA                           # desbloqueou
        self.assertTrue(self.db.backup_automatico().endswith(".dbx"))

    def test_automatico_troca_o_do_dia_de_formato(self):
        plano = self.db.backup_automatico()
        self.assertTrue(plano.endswith(".db"))
        self._ligar()
        novo = self.db.backup_automatico(sobrescrever=True)
        self.assertTrue(novo.endswith(".dbx"))
        self.assertEqual(self._arquivos(), [os.path.basename(novo)])   # o .db do dia sumiu
        self.assertIsNone(self.db.backup_automatico())                 # já existe o de hoje

    def test_restaurar_criptografado(self):
        self._ligar()
        caminho = self.db.fazer_backup()
        self.db.inserir("Outro Paciente", "x", "depois do backup")
        self.assertEqual(len(self.db.listar()), 2)
        self.db.restaurar_backup(caminho)                        # usa a senha da sessão
        self.assertEqual([r[2] for r in self.db.listar()], ["Maria da Silva"])
        sobras = [n for n in self._arquivos() if n.endswith(".tmp") or n.startswith("restauracao_")]
        self.assertEqual(sobras, [])                             # nenhuma cópia limpa ficou

    def test_restaurar_com_senha_errada_nao_altera(self):
        self._ligar()
        caminho = self.db.fazer_backup()
        self.db.inserir("Outro Paciente", "x", "y")
        self.db.backup_segredo = "outra-senha-qualquer"
        with self.assertRaises(seguranca.SenhaIncorreta):
            self.db.restaurar_backup(caminho)
        self.assertEqual(len(self.db.listar()), 2)               # nada mudou
        self.db.restaurar_backup(caminho, segredo=SENHA)         # senha explícita do backup
        self.assertEqual(len(self.db.listar()), 1)

    def test_restaurar_exige_senha_se_nao_houver(self):
        self._ligar()
        caminho = self.db.fazer_backup()
        self.db.backup_segredo = None
        with self.assertRaises(seguranca.SenhaIncorreta):
            self.db.restaurar_backup(caminho)

    def test_backup_de_seguranca_da_restauracao_tambem_e_criptografado(self):
        self._ligar()
        caminho = self.db.fazer_backup()
        seguranca_copia = self.db.restaurar_backup(caminho)
        self.assertTrue(seguranca_copia.endswith(".dbx"))
        self.assertTrue(os.path.basename(seguranca_copia).startswith("antes_da_restauracao_"))

    def test_listagem_mostra_criptografados_sem_abrir(self):
        self.db.fazer_backup("backup_2020-01-01_000000.db")
        self._ligar()
        self.db.fazer_backup("backup_2020-01-02_000000.dbx")
        itens = {i["nome"]: i for i in self.db.listar_backups()}
        self.assertTrue(itens["backup_2020-01-02_000000.dbx"]["criptografado"])
        self.assertIsNone(itens["backup_2020-01-02_000000.dbx"]["registros"])
        self.assertFalse(itens["backup_2020-01-01_000000.db"]["criptografado"])
        self.assertEqual(itens["backup_2020-01-01_000000.db"]["registros"], 1)

    def test_rotacao_vale_para_os_dois_formatos(self):
        self._ligar()
        for i in range(BACKUPS_MANTER + 3):
            self.db.fazer_backup(f"backup_2020-01-{i + 1:02d}_000000.dbx")
            os.utime(os.path.join(self.pasta, f"backup_2020-01-{i + 1:02d}_000000.dbx"),
                     (1_600_000_000 + i, 1_600_000_000 + i))
        self.assertEqual(len([n for n in self._arquivos() if n.endswith(".dbx")]), BACKUPS_MANTER)

    def test_criptografar_existentes(self):
        self.db.fazer_backup("backup_2020-01-01_000000.db")
        self.db.fazer_backup("antes_da_restauracao_2020-01-02_000000.db")
        self.db.fazer_backup("arquivo_do_usuario.db")             # fora dos prefixos: não mexe
        with self.assertRaises(RuntimeError):
            self.db.criptografar_backups_existentes()             # sem senha
        self._ligar()
        self.assertEqual(self.db.criptografar_backups_existentes(), 2)
        self.assertEqual(self._arquivos(), ["antes_da_restauracao_2020-01-02_000000.dbx",
                                            "arquivo_do_usuario.db",
                                            "backup_2020-01-01_000000.dbx"])
        for nome in self._arquivos():
            if nome.endswith(".dbx"):
                with open(os.path.join(self.pasta, nome), "rb") as f:
                    dados = seguranca.descriptografar(f.read(), SENHA)
                self.assertTrue(dados.startswith(b"SQLite format 3"))


if __name__ == "__main__":
    unittest.main()
