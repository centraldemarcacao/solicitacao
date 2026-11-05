"""Testes da camada de banco (rodar: python test_database.py)."""

import os
import tempfile
import unittest

from database import (
    caminho_banco,
    MAX_DESCRICAO,
    MAX_NOME,
    STATUS_ATENDIDA,
    STATUS_PENDENTE,
    Database,
)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "teste.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_inserir_e_listar(self):
        rid = self.db.inserir("Maria Silva", "Ramal 2045", "Solicita água")
        regs = self.db.listar()
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0][0], rid)
        self.assertEqual(regs[0][5], STATUS_PENDENTE)

    def test_validacao_campos_vazios(self):
        with self.assertRaises(ValueError):
            self.db.inserir("   ", "x", "desc")
        with self.assertRaises(ValueError):
            self.db.inserir("João", "x", "")

    def test_validacao_tamanho_maximo(self):
        with self.assertRaises(ValueError):
            self.db.inserir("A" * (MAX_NOME + 1), "", "desc")
        with self.assertRaises(ValueError):
            self.db.inserir("Ana", "", "d" * (MAX_DESCRICAO + 1))
        self.assertEqual(len(self.db.listar()), 0)

    def test_filtro_nome_e_contato(self):
        self.db.inserir("Maria Silva", "9999-0000", "a")
        self.db.inserir("José Souza", "ramal 12", "b")
        self.assertEqual(len(self.db.listar("maria")), 1)
        self.assertEqual(len(self.db.listar("RAMAL")), 1)
        self.assertEqual(len(self.db.listar("zzz")), 0)

    def test_busca_ignora_acentos_e_maiusculas(self):
        self.db.inserir("José da Conceição", "", "a")
        self.db.inserir("JOÃO PEREIRA", "", "b")
        self.assertEqual(len(self.db.listar("jose")), 1)
        self.assertEqual(len(self.db.listar("CONCEICAO")), 1)
        self.assertEqual(len(self.db.listar("joão")), 1)
        self.assertEqual(len(self.db.listar("joao")), 1)
        self.assertEqual(len(self.db.listar("zé")), 0)

    def test_busca_trata_curingas_como_texto(self):
        self.db.inserir("Ana", "100%", "a")
        self.db.inserir("Bia", "ramal_12", "b")
        self.assertEqual(len(self.db.listar("%")), 1)
        self.assertEqual(len(self.db.listar("_")), 1)
        self.assertEqual(len(self.db.listar("l_1")), 1)   # '_' não vira coringa
        self.assertEqual(len(self.db.listar("l-1")), 0)

    def test_filtro_por_status(self):
        a = self.db.inserir("Ana", "1", "x")
        self.db.inserir("Beatriz", "2", "y")
        self.db.atualizar_status(a, STATUS_ATENDIDA)
        self.assertEqual(len(self.db.listar(status=STATUS_ATENDIDA)), 1)
        self.assertEqual(len(self.db.listar(status=STATUS_PENDENTE)), 1)
        self.assertEqual(len(self.db.listar("ana", STATUS_PENDENTE)), 0)
        with self.assertRaises(ValueError):
            self.db.listar(status="Qualquer")

    def test_sql_injection_nao_funciona(self):
        self.db.inserir("Ana", "1", "x")
        self.assertEqual(len(self.db.listar("'; DROP TABLE solicitacoes;--")), 0)
        self.assertEqual(len(self.db.listar()), 1)

    def test_atualizar_status(self):
        rid = self.db.inserir("Ana", "1", "x")
        self.db.atualizar_status(rid, STATUS_ATENDIDA)
        self.assertEqual(self.db.obter(rid)[5], STATUS_ATENDIDA)
        self.db.atualizar_status(rid, STATUS_PENDENTE)
        self.assertEqual(self.db.obter(rid)[5], STATUS_PENDENTE)
        with self.assertRaises(ValueError):
            self.db.atualizar_status(rid, "Qualquer")

    def test_excluir_um(self):
        a = self.db.inserir("Ana", "1", "x")
        b = self.db.inserir("Bia", "2", "y")
        self.assertTrue(self.db.excluir(a))
        self.assertIsNone(self.db.obter(a))
        self.assertIsNotNone(self.db.obter(b))
        self.assertFalse(self.db.excluir(a))  # já removido
        self.assertEqual(len(self.db.listar()), 1)

    def test_excluir_varios(self):
        ids = [self.db.inserir(f"Paciente {i}", "", "x") for i in range(4)]
        self.assertEqual(self.db.excluir_varios(ids[:3]), 3)
        self.assertEqual(len(self.db.listar()), 1)
        self.assertEqual(self.db.excluir_varios([]), 0)
        self.assertEqual(self.db.excluir_varios([9999]), 0)

    def test_contagem(self):
        a = self.db.inserir("A", "", "x")
        self.db.inserir("B", "", "y")
        self.db.atualizar_status(a, STATUS_ATENDIDA)
        c = self.db.contar_por_status()
        self.assertEqual(c[STATUS_ATENDIDA], 1)
        self.assertEqual(c[STATUS_PENDENTE], 1)
        self.db.excluir(a)
        self.assertEqual(self.db.contar_por_status()[STATUS_ATENDIDA], 0)

    def test_limite_e_ordem(self):
        for i in range(7):
            self.db.inserir(f"Paciente {i}", "", "x")
        ultimos = self.db.listar(limite=5)
        self.assertEqual(len(ultimos), 5)
        self.assertEqual(ultimos[0][2], "Paciente 6")  # mais recente primeiro

    def test_contar_hoje(self):
        self.assertEqual(self.db.contar_hoje(), 0)
        self.db.inserir("Ana", "", "x")
        self.db.inserir("Bia", "", "y")
        self.assertEqual(self.db.contar_hoje(), 2)

    def test_caminho_banco_gravavel(self):
        import os as _os
        caminho = caminho_banco()
        self.assertTrue(_os.path.isdir(_os.path.dirname(caminho)))


if __name__ == "__main__":
    unittest.main()
