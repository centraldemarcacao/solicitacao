"""WAL, verificação de integridade ao abrir e restauração automática do último backup válido."""

import os
import sqlite3
import logging
import tempfile
import unittest

from anotacoes.nucleo.database import Database

# Sem manipulador, o Python imprime avisos no console durante os testes.
logging.getLogger("anotacoes").addHandler(logging.NullHandler())


class TestWal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = os.path.join(self.tmp.name, "teste.db")

    def tearDown(self):
        self.tmp.cleanup()

    def _modo(self, caminho):
        conn = sqlite3.connect(caminho)
        try:
            return conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
        finally:
            conn.close()

    def test_banco_novo_usa_wal(self):
        db = Database(self.caminho)
        self.assertEqual(db.modo_journal, "wal")
        self.assertEqual(self._modo(self.caminho), "wal")

    def test_banco_antigo_e_convertido_para_wal(self):
        conn = sqlite3.connect(self.caminho)
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.close()
        Database(self.caminho)
        self.assertEqual(self._modo(self.caminho), "wal")

    def test_operacoes_continuam_funcionando_em_wal(self):
        db = Database(self.caminho)
        rid = db.inserir("Maria", "1", "Solicita água")
        self.assertEqual(db.listar()[0][0], rid)
        db.excluir(rid)
        self.assertEqual(db.contar_lixeira(), 1)

    def test_backup_e_arquivo_unico_e_abre_somente_leitura(self):
        db = Database(self.caminho)
        db.inserir("Ana", "", "teste")
        destino = db.fazer_backup()
        self.assertEqual(self._modo(destino), "delete")
        self.assertFalse(os.path.exists(destino + "-wal"))
        self.assertEqual(db.listar_backups()[0]["registros"], 1)

    def test_restaurar_backup_mantem_wal(self):
        db = Database(self.caminho)
        db.inserir("Ana", "", "teste")
        backup = db.fazer_backup()
        db.inserir("Beto", "", "outro")
        db.restaurar_backup(backup)
        self.assertEqual(db.total_registros(), 1)
        self.assertEqual(self._modo(self.caminho), "wal")

    def test_falha_ao_ativar_wal_nao_impede_abrir(self):
        class SemWal(Database):
            def _ativar_wal(self, conn):      # simula pasta que recusa WAL
                self.modo_journal = "delete"

        db = SemWal(self.caminho)
        db.inserir("Ana", "", "teste")
        self.assertEqual(db.total_registros(), 1)


class TestIntegridade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = os.path.join(self.tmp.name, "teste.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_banco_saudavel(self):
        db = Database(self.caminho)
        self.assertEqual(db.verificar_integridade(), (True, "ok"))
        self.assertIsNone(db.problema_integridade)
        self.assertFalse(db.banco_ilegivel)

    def test_arquivo_que_nao_e_banco(self):
        with open(self.caminho, "wb") as arq:
            arq.write(b"isto nao e um banco de dados sqlite" * 50)
        db = Database(self.caminho)      # não pode explodir
        self.assertTrue(db.banco_ilegivel)
        self.assertIn("ilegível", db.problema_integridade)

    def test_banco_vazio_novo_nao_e_problema(self):
        open(self.caminho, "wb").close()
        db = Database(self.caminho)
        self.assertIsNone(db.problema_integridade)
        db.inserir("Ana", "", "ok")

    def test_restaura_ultimo_backup_valido_apos_corrupcao(self):
        db = Database(self.caminho)
        db.inserir("Ana", "", "primeiro")
        db.fazer_backup("backup_2026-01-01.db")
        db.inserir("Beto", "", "segundo")
        # corrompe o banco em uso
        del db
        with open(self.caminho, "wb") as arq:
            arq.write(b"lixo" * 1000)
        for sufixo in ("-wal", "-shm"):
            if os.path.exists(self.caminho + sufixo):
                os.remove(self.caminho + sufixo)

        db = Database(self.caminho)
        self.assertTrue(db.banco_ilegivel)
        usado = db.restaurar_ultimo_backup_valido()
        self.assertEqual(usado, "backup_2026-01-01.db")
        self.assertIsNone(db.problema_integridade)
        self.assertEqual(db.total_registros(), 1)
        self.assertEqual(db.verificar_integridade(), (True, "ok"))
        guardados = [n for n in os.listdir(self.tmp.name) if ".corrompido-" in n]
        self.assertEqual(len(guardados), 1)       # o arquivo danificado fica para análise

    def test_pula_backup_invalido_e_usa_o_anterior(self):
        db = Database(self.caminho)
        db.inserir("Ana", "", "primeiro")
        db.fazer_backup("backup_2026-01-01.db")
        ruim = os.path.join(db.pasta_backups(), "backup_2026-01-02.db")
        with open(ruim, "wb") as arq:
            arq.write(b"nao e um banco" * 100)
        os.utime(ruim)       # o inválido é o mais recente
        self.assertEqual(db.restaurar_ultimo_backup_valido(), "backup_2026-01-01.db")

    def test_sem_nenhum_backup_valido(self):
        db = Database(self.caminho)
        with self.assertRaises(ValueError):
            db.restaurar_ultimo_backup_valido()
        self.assertEqual(db.verificar_integridade(), (True, "ok"))   # nada foi movido


if __name__ == "__main__":
    unittest.main()
