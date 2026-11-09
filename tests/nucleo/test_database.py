"""Testes da camada de banco (rodar: python -m unittest discover -s tests -t .)."""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from anotacoes.nucleo.database import (
    BACKUPS_MANTER,
    caminho_banco,
    validar_campos,
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
        with tempfile.TemporaryDirectory() as raiz, \
                mock.patch("anotacoes.nucleo.database.pasta_programa", lambda: raiz):
            caminho = caminho_banco()
            self.assertEqual(os.path.dirname(caminho), os.path.join(raiz, "dados"))
            self.assertTrue(os.path.isdir(os.path.dirname(caminho)))

    # ---------------- edição ----------------
    def test_atualizar_registro(self):
        rid = self.db.inserir("Ana", "1", "original")
        self.assertIsNone(self.db.obter_detalhado(rid)["editado_em"])
        self.assertTrue(self.db.atualizar(rid, "  Ana Maria ", "2", " corrigido "))
        reg = self.db.obter_detalhado(rid)
        self.assertEqual((reg["nome"], reg["contato"], reg["descricao"]), ("Ana Maria", "2", "corrigido"))
        self.assertIsNotNone(reg["editado_em"])
        self.assertEqual(reg["status"], STATUS_PENDENTE)       # status não muda ao editar
        self.assertEqual(reg["data_hora"], self.db.obter(rid)[1])  # data original preservada

    def test_atualizar_valida_campos(self):
        rid = self.db.inserir("Ana", "", "x")
        with self.assertRaises(ValueError):
            self.db.atualizar(rid, "   ", "", "x")
        with self.assertRaises(ValueError):
            self.db.atualizar(rid, "Ana", "", "")
        with self.assertRaises(ValueError):
            self.db.atualizar(rid, "A" * (MAX_NOME + 1), "", "x")
        self.assertEqual(self.db.obter(rid)[2], "Ana")          # nada foi alterado

    def test_atualizar_inexistente_ou_na_lixeira(self):
        self.assertFalse(self.db.atualizar(999, "Ana", "", "x"))
        rid = self.db.inserir("Ana", "", "x")
        self.db.excluir(rid)
        self.assertFalse(self.db.atualizar(rid, "Novo", "", "x"))

    def test_validar_campos(self):
        self.assertEqual(validar_campos("Ana", "", "x"), {})
        self.assertEqual(set(validar_campos("", "", "")), {"nome", "descricao"})
        self.assertEqual(set(validar_campos("Ana", "c" * 81, "x")), {"contato"})

    # ---------------- lixeira ----------------
    def test_excluir_move_para_a_lixeira(self):
        a = self.db.inserir("Ana", "1", "x")
        b = self.db.inserir("Bia", "2", "y")
        self.assertTrue(self.db.excluir(a))
        self.assertEqual([r[0] for r in self.db.listar()], [b])
        self.assertEqual(self.db.listar("ana"), [])             # busca ignora a lixeira
        self.assertEqual(self.db.contar_hoje(), 1)
        self.assertEqual(sum(self.db.contar_por_status().values()), 1)
        self.assertEqual(self.db.contar_lixeira(), 1)
        self.assertEqual(self.db.listar_lixeira()[0][0], a)
        self.assertIsNotNone(self.db.obter_detalhado(a, incluir_excluidos=True)["excluido_em"])

    def test_restaurar(self):
        ids = [self.db.inserir(f"P{i}", "", "x") for i in range(3)]
        self.db.excluir_varios(ids)
        self.assertEqual(self.db.restaurar(ids[:2]), 2)
        self.assertEqual(len(self.db.listar()), 2)
        self.assertEqual(self.db.contar_lixeira(), 1)
        self.assertEqual(self.db.restaurar(ids[:2]), 0)         # já restaurados
        self.assertEqual(self.db.restaurar([]), 0)

    def test_apagar_definitivamente_so_age_na_lixeira(self):
        a = self.db.inserir("Ana", "", "x")
        b = self.db.inserir("Bia", "", "y")
        self.assertEqual(self.db.apagar_definitivamente([a]), 0)   # ativo: protegido
        self.assertIsNotNone(self.db.obter(a))
        self.db.excluir(b)
        self.assertEqual(self.db.apagar_definitivamente([a, b]), 1)
        self.assertIsNone(self.db.obter_detalhado(b, incluir_excluidos=True))
        self.assertIsNotNone(self.db.obter(a))

    def test_esvaziar_lixeira(self):
        a = self.db.inserir("Ana", "", "x")
        self.db.inserir("Bia", "", "y")
        self.db.excluir(a)
        self.assertEqual(self.db.esvaziar_lixeira(), 1)
        self.assertEqual(self.db.contar_lixeira(), 0)
        self.assertEqual(len(self.db.listar()), 1)

    def test_limpeza_automatica_da_lixeira(self):
        velho = self.db.inserir("Velho", "", "x")
        novo = self.db.inserir("Novo", "", "y")
        self.db.excluir_varios([velho, novo])
        antigo = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(self.db.caminho)
        conn.execute("UPDATE solicitacoes SET excluido_em = ? WHERE id = ?", (antigo, velho))
        conn.commit(); conn.close()
        self.assertEqual(self.db.limpar_lixeira_antiga(30), 1)
        self.assertEqual([r[0] for r in self.db.listar_lixeira()], [novo])

    def test_status_nao_muda_na_lixeira(self):
        rid = self.db.inserir("Ana", "", "x")
        self.db.excluir(rid)
        self.db.atualizar_status(rid, STATUS_ATENDIDA)
        self.assertEqual(self.db.obter_detalhado(rid, True)["status"], STATUS_PENDENTE)

    # ---------------- migração ----------------
    def test_migracao_de_banco_antigo(self):
        antigo = os.path.join(self.tmp.name, "antigo.db")
        conn = sqlite3.connect(antigo)
        conn.executescript("""
            CREATE TABLE solicitacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT NOT NULL,
                nome_paciente TEXT NOT NULL, contato TEXT, descricao TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente', 'Atendida')));
            INSERT INTO solicitacoes (data_hora, nome_paciente, contato, descricao, status)
            VALUES ('2026-01-05 10:00:00', 'Maria Antiga', '123', 'registro da v1', 'Atendida');
        """)
        conn.commit(); conn.close()
        db = Database(antigo)
        regs = db.listar()
        self.assertEqual(len(regs), 1)                          # dado antigo preservado
        self.assertEqual((regs[0][2], regs[0][5]), ("Maria Antiga", STATUS_ATENDIDA))
        self.assertTrue(db.excluir(regs[0][0]))                 # funções novas funcionam
        self.assertEqual(db.contar_lixeira(), 1)
        Database(antigo)                                        # reabrir não quebra

    # ---------------- backup ----------------
    def test_fazer_backup_e_listar(self):
        self.db.inserir("Ana", "", "x")
        self.db.inserir("Bia", "", "y")
        caminho = self.db.fazer_backup("backup_teste.db")
        self.assertTrue(os.path.isfile(caminho))
        self.assertFalse(os.path.exists(caminho + ".tmp"))
        itens = self.db.listar_backups()
        self.assertEqual(len(itens), 1)
        self.assertEqual((itens[0]["nome"], itens[0]["registros"]), ("backup_teste.db", 2))
        self.assertGreater(itens[0]["tamanho"], 0)

    def test_backup_automatico_um_por_dia(self):
        self.db.inserir("Ana", "", "x")
        primeiro = self.db.backup_automatico()
        self.assertIsNotNone(primeiro)
        self.assertIsNone(self.db.backup_automatico())           # já existe o de hoje
        self.db.inserir("Bia", "", "y")
        self.assertIsNotNone(self.db.backup_automatico(sobrescrever=True))
        self.assertEqual(self.db.listar_backups()[0]["registros"], 2)

    def test_backup_nao_troca_copia_com_dados_por_banco_vazio(self):
        rid = self.db.inserir("Ana", "", "x")
        self.db.backup_automatico()
        self.db.excluir(rid)
        self.db.esvaziar_lixeira()                               # banco ficou vazio
        self.assertIsNone(self.db.backup_automatico(sobrescrever=True))
        self.assertEqual(self.db.listar_backups()[0]["registros"], 1)

    def test_rotacao_de_backups(self):
        self.db.inserir("Ana", "", "x")
        pasta = self.db.pasta_backups()
        for i in range(BACKUPS_MANTER + 4):
            caminho = self.db.fazer_backup(f"backup_2026-01-{i + 1:02d}.db")
            os.utime(caminho, (1_700_000_000 + i * 86400,) * 2)  # datas crescentes
        nomes = sorted(n for n in os.listdir(pasta) if n.startswith("backup_"))
        self.assertEqual(len(nomes), BACKUPS_MANTER)
        self.assertNotIn("backup_2026-01-01.db", nomes)          # os mais antigos saíram

    def test_restaurar_backup(self):
        a = self.db.inserir("Ana", "", "original")
        caminho = self.db.fazer_backup("backup_bom.db")
        self.db.excluir(a)
        self.db.esvaziar_lixeira()
        self.db.inserir("Intruso", "", "criado depois do backup")
        seguranca = self.db.restaurar_backup(caminho)
        nomes = [r[2] for r in self.db.listar()]
        self.assertEqual(nomes, ["Ana"])                         # voltou ao estado do backup
        self.assertTrue(os.path.isfile(seguranca))               # cópia do estado anterior
        self.assertEqual(self.db._contar_em(seguranca), 1)       # ...com o "Intruso"

    def test_restaurar_backup_invalido_nao_altera_nada(self):
        self.db.inserir("Ana", "", "x")
        lixo = os.path.join(self.tmp.name, "lixo.db")
        with open(lixo, "wb") as arq:
            arq.write(b"isto nao e um banco de dados" * 50)
        with self.assertRaises(ValueError):
            self.db.restaurar_backup(lixo)
        outro = os.path.join(self.tmp.name, "outro.db")
        conn = sqlite3.connect(outro); conn.execute("CREATE TABLE coisa (x)"); conn.commit(); conn.close()
        with self.assertRaises(ValueError):
            self.db.restaurar_backup(outro)
        with self.assertRaises(ValueError):
            self.db.restaurar_backup(os.path.join(self.tmp.name, "naoexiste.db"))
        self.assertEqual(len(self.db.listar()), 1)
        self.assertEqual(self.db.listar_backups(), [])           # nem criou cópia de segurança

    def test_restaurar_backup_de_versao_antiga(self):
        antigo = os.path.join(self.tmp.name, "backup_v1.db")
        conn = sqlite3.connect(antigo)
        conn.executescript("""
            CREATE TABLE solicitacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT NOT NULL,
              nome_paciente TEXT NOT NULL, contato TEXT, descricao TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'Pendente');
            INSERT INTO solicitacoes (data_hora, nome_paciente, contato, descricao)
            VALUES ('2026-01-05 10:00:00', 'Da v1', '', 'x');
        """)
        conn.commit(); conn.close()
        self.db.restaurar_backup(antigo)
        self.assertEqual([r[2] for r in self.db.listar()], ["Da v1"])
        self.assertTrue(self.db.excluir(self.db.listar()[0][0]))  # colunas novas recriadas


class TestRetornoEBusca(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "t.db"))
        hoje = datetime.now().date()
        self.ontem = (hoje - timedelta(days=1)).isoformat()
        self.hoje = hoje.isoformat()
        self.amanha = (hoje + timedelta(days=1)).isoformat()

    def tearDown(self):
        self.tmp.cleanup()

    def test_lembrete_gravado_e_listado(self):
        rid = self.db.inserir("Ana", "1", "x", self.amanha)
        self.assertEqual(self.db.listar()[0][6], self.amanha)
        self.assertEqual(self.db.obter(rid)[6], self.amanha)
        self.assertEqual(self.db.obter_detalhado(rid)["lembrete"], self.amanha)
        self.assertIsNone(self.db.obter(self.db.inserir("Bia", "", "y"))[6])

    def test_lembrete_invalido(self):
        for ruim in ("31/12/2026", "2026-13-40", "abc"):
            with self.assertRaises(ValueError):
                self.db.inserir("Ana", "", "x", ruim)
        self.assertEqual(self.db.listar(), [])

    def test_atualizar_mantem_define_e_remove(self):
        rid = self.db.inserir("Ana", "", "x", self.amanha)
        self.db.atualizar(rid, "Ana", "", "y")                       # omitido: mantém
        self.assertEqual(self.db.obter(rid)[6], self.amanha)
        self.db.atualizar(rid, "Ana", "", "y", self.hoje)            # define
        self.assertEqual(self.db.obter(rid)[6], self.hoje)
        self.db.atualizar(rid, "Ana", "", "y", None)                 # remove
        self.assertIsNone(self.db.obter(rid)[6])

    def test_retornos_so_pendentes_hoje_ou_atrasados(self):
        a = self.db.inserir("A", "", "x", self.ontem)
        self.db.inserir("B", "", "x", self.hoje)
        self.db.inserir("C", "", "x", self.amanha)
        self.db.inserir("D", "", "x")
        e = self.db.inserir("E", "", "x", self.ontem)
        self.db.atualizar_status(e, STATUS_ATENDIDA)
        self.assertEqual(self.db.contar_retornos(), 2)
        self.assertEqual({r[2] for r in self.db.listar(so_retornos=True)}, {"A", "B"})
        self.db.excluir(a)
        self.assertEqual(self.db.contar_retornos(), 1)

    def test_busca_na_descricao(self):
        self.db.inserir("Ana", "1", "Pediu troca de LEITO urgente")
        self.db.inserir("Bia", "2", "Dúvida sobre visita")
        self.assertEqual(len(self.db.listar("leito")), 1)
        self.assertEqual(len(self.db.listar("duvida")), 1)
        self.assertEqual(len(self.db.listar("ana")), 1)

    def test_filtro_por_periodo(self):
        conn = sqlite3.connect(self.db.caminho)
        antigo = (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO solicitacoes (data_hora, nome_paciente, contato, descricao)"
                     " VALUES (?, 'Velho', '', 'x')", (antigo,))
        conn.commit(); conn.close()
        self.db.inserir("Novo", "", "x")
        self.assertEqual(len(self.db.listar()), 2)
        desde7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        self.assertEqual([r[2] for r in self.db.listar(desde=desde7)], ["Novo"])
        with self.assertRaises(ValueError):
            self.db.listar(desde="ontem")

    def test_migracao_adiciona_lembrete(self):
        caminho = os.path.join(self.tmp.name, "v1.db")
        conn = sqlite3.connect(caminho)
        conn.execute("""CREATE TABLE solicitacoes (id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL, nome_paciente TEXT NOT NULL, contato TEXT,
            descricao TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pendente')""")
        conn.execute("INSERT INTO solicitacoes (data_hora, nome_paciente, descricao)"
                     " VALUES ('2026-01-01 10:00:00', 'Velha', 'x')")
        conn.commit(); conn.close()
        db = Database(caminho)
        self.assertIsNone(db.listar()[0][6])
        db.atualizar(db.listar()[0][0], "Velha", "", "x", self.hoje)
        self.assertEqual(db.contar_retornos(), 1)


class TestPrioridade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "t.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_padrao_e_urgente(self):
        a = self.db.inserir("Ana", "", "x")
        b = self.db.inserir("Bia", "", "y", prioridade="Urgente")
        self.assertEqual(self.db.obter(a)[7], "Normal")
        self.assertEqual(self.db.obter_detalhado(b)["prioridade"], "Urgente")
        self.assertEqual([r[2] for r in self.db.listar(so_urgentes=True)], ["Bia"])
        self.assertEqual(self.db.contar_urgentes(), 1)

    def test_invalida(self):
        with self.assertRaises(ValueError):
            self.db.inserir("Ana", "", "x", prioridade="Altíssima")

    def test_atualizar_mantem_e_muda(self):
        a = self.db.inserir("Ana", "", "x", prioridade="Urgente")
        self.db.atualizar(a, "Ana", "", "y")
        self.assertEqual(self.db.obter(a)[7], "Urgente")
        self.db.atualizar(a, "Ana", "", "y", prioridade="Normal")
        self.assertEqual(self.db.obter(a)[7], "Normal")

    def test_urgente_atendida_nao_conta(self):
        a = self.db.inserir("Ana", "", "x", prioridade="Urgente")
        self.db.atualizar_status(a, STATUS_ATENDIDA)
        self.assertEqual(self.db.contar_urgentes(), 0)

    def test_filtro_ate(self):
        conn = sqlite3.connect(self.db.caminho)
        conn.execute("INSERT INTO solicitacoes (data_hora, nome_paciente, contato, descricao)"
                     " VALUES ('2026-01-05 10:00:00', 'Velha', '', 'x')")
        conn.commit(); conn.close()
        self.db.inserir("Nova", "", "x")
        self.assertEqual([r[2] for r in self.db.listar(ate="2026-01-31")], ["Velha"])

    def test_migracao_preserva_registros_como_normal(self):
        caminho = os.path.join(self.tmp.name, "v.db")
        conn = sqlite3.connect(caminho)
        conn.execute("""CREATE TABLE solicitacoes (id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL, nome_paciente TEXT NOT NULL, contato TEXT,
            descricao TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pendente')""")
        conn.execute("INSERT INTO solicitacoes (data_hora, nome_paciente, descricao)"
                     " VALUES ('2026-01-01 10:00:00', 'Velha', 'x')")
        conn.commit(); conn.close()
        self.assertEqual(Database(caminho).listar()[0][7], "Normal")


if __name__ == "__main__":
    unittest.main()
