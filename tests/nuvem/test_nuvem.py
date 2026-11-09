"""
Testes da sincronização com a nuvem (nuvem/cliente.py, nuvem/sincronizacao.py e as colunas /
gatilhos de nucleo/database.py).

Não usam internet: um "Supabase de mentira" (FakeSupabase) responde no lugar da
rede, imitando login, renovação de sessão e a API REST (filtros, ordenação,
limite e gravação em lote com 'merge-duplicates').

Execute (na raiz do repositório):  python -m unittest tests.nuvem.test_nuvem -v
"""

import os
import re
import sqlite3
import tempfile
import unittest
import urllib.parse
from datetime import datetime
from unittest import mock

from anotacoes.nuvem import cliente as nuvem
from anotacoes.nuvem import sincronizacao
from anotacoes.nucleo.database import Database, agora_utc
from anotacoes.nuvem.cliente import ClienteSupabase, NuvemErro
from anotacoes.nuvem.sql import SQL_CONFIGURACAO, TABELA
from anotacoes.nuvem.sincronizacao import da_nuvem, para_nuvem, sincronizar

CHAVE = "sb_publishable_" + "x" * 30
URL = "https://abcdefgh.supabase.co"


# ----------------------------------------------------------------------
# Supabase de mentira
# ----------------------------------------------------------------------
def _para_pg(ts_iso: str) -> str:
    """Formata como o PostgreSQL devolve: fuso +00:00 e fração sem zeros à direita."""
    base = datetime.strptime(ts_iso[:19], "%Y-%m-%dT%H:%M:%S")
    m = re.search(r"\.(\d+)", ts_iso)
    fracao = (m.group(1).rstrip("0") if m else "")
    return base.strftime("%Y-%m-%dT%H:%M:%S") + ("." + fracao if fracao else "") + "+00:00"


def _dt(ts_iso: str) -> datetime:
    return datetime.strptime(da_nuvem(ts_iso), "%Y-%m-%d %H:%M:%S.%f")


class FakeSupabase:
    def __init__(self):
        self.linhas = {}                 # uuid -> dict
        self.senha = "segredo"
        self.email = "eu@exemplo.com"
        self.refresh_validos = set()
        self.contador = 0
        self.tabela_existe = True
        self.offline = False
        self.expirar_acesso = False      # força 'JWT expired' na próxima chamada REST
        self.posts = []                  # lotes recebidos
        self.gets = 0

    def _novo_token(self):
        self.contador += 1
        refresh = f"r{self.contador}"
        self.refresh_validos.add(refresh)
        return {"access_token": f"tok{self.contador}", "refresh_token": refresh,
                "expires_in": 3600}

    def http(self, cliente, metodo, caminho, corpo=None, cabecalhos=None, token=None):
        if self.offline:
            raise NuvemErro("Sem conexão com o Supabase.")
        url = urllib.parse.urlsplit(caminho)
        params = dict(urllib.parse.parse_qsl(url.query))
        if url.path == "/auth/v1/token":
            if params["grant_type"] == "password":
                if corpo["email"] != self.email or corpo["password"] != self.senha:
                    raise nuvem._erro_http(400, {"error_description": "Invalid login credentials"})
                return self._novo_token()
            if corpo["refresh_token"] not in self.refresh_validos:
                raise nuvem._erro_http(400, {"message": "Invalid Refresh Token: Not Found"})
            self.refresh_validos.discard(corpo["refresh_token"])
            return self._novo_token()
        assert url.path == f"/rest/v1/{TABELA}", url.path
        if not self.tabela_existe:
            raise nuvem._erro_http(404, {"code": "PGRST205",
                                         "message": "Could not find the table"})
        if self.expirar_acesso:
            self.expirar_acesso = False
            raise nuvem._erro_http(401, {"message": "JWT expired", "code": "PGRST303"})
        if not (token or "").startswith("tok"):
            raise nuvem._erro_http(401, {"message": "Invalid API key"})
        if metodo == "POST":
            assert params.get("on_conflict") == "uuid"
            assert "merge-duplicates" in cabecalhos["Prefer"]
            assert len({tuple(sorted(l)) for l in corpo}) == 1, "chaves diferentes no lote"
            self.posts.append(list(corpo))
            for linha in corpo:
                antigo = self.linhas.get(linha["uuid"], {})
                self.linhas[linha["uuid"]] = {**antigo, **linha}
            return None
        self.gets += 1
        linhas = list(self.linhas.values())
        if "atualizado_em" in params:
            op, _, valor = params["atualizado_em"].partition(".")
            assert op == "gte"
            linhas = [l for l in linhas if _dt(l["atualizado_em"]) >= _dt(valor)]
        if "or" in params:
            m = re.fullmatch(
                r"\(atualizado_em\.gt\.(\S+?),and\(atualizado_em\.eq\.(\S+?),uuid\.gt\.(\w+)\)\)",
                params["or"])
            assert m, params["or"]
            ts, ts2, u = m.groups()
            assert ts == ts2
            linhas = [l for l in linhas
                      if _dt(l["atualizado_em"]) > _dt(ts)
                      or (_dt(l["atualizado_em"]) == _dt(ts) and l["uuid"] > u)]
        linhas.sort(key=lambda l: (_dt(l["atualizado_em"]), l["uuid"]))
        linhas = linhas[:int(params.get("limit", 1000))]
        return [{**l, "atualizado_em": _para_pg(l["atualizado_em"]),
                 "user_id": "u1"} for l in linhas]


class BaseNuvem(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = FakeSupabase()
        patcher = mock.patch.object(
            ClienteSupabase, "_http",
            lambda cliente, *a, **k: self.server.http(cliente, *a, **k))
        patcher.start()
        self.addCleanup(patcher.stop)

    def novo_db(self, nome="a.db"):
        return Database(os.path.join(self.tmp.name, nome))

    def cliente(self):
        c = ClienteSupabase(URL, CHAVE)
        c.entrar(self.server.email, self.server.senha)
        return c


# ----------------------------------------------------------------------
class TestBancoLocal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(os.path.join(self.tmp.name, "t.db"))

    def estado(self, rid):
        return self.db._consultar(
            "SELECT uuid, sujo, atualizado_em FROM solicitacoes WHERE id = ?", (rid,))[0]

    def test_inserir_gera_uuid_e_marca_pendente(self):
        rid = self.db.inserir("Ana", "1", "x")
        uuid_, sujo, ts = self.estado(rid)
        self.assertEqual(len(uuid_), 32)
        self.assertEqual(sujo, 1)
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$")
        self.assertEqual(self.db.sync_contar_pendentes(), 1)

    def test_confirmar_envio_e_nova_edicao(self):
        rid = self.db.inserir("Ana", "1", "x")
        uuid_, _, ts = self.estado(rid)
        self.db.sync_confirmar_envio([(uuid_, ts)])
        self.assertEqual(self.db.sync_contar_pendentes(), 0)
        self.db.atualizar_status(rid, "Atendida")
        self.assertEqual(self.estado(rid)[1], 1)
        self.assertEqual(self.db.sync_contar_pendentes(), 1)

    def test_alteracao_durante_o_envio_continua_pendente(self):
        rid = self.db.inserir("Ana", "1", "x")
        uuid_, _, ts_antigo = self.estado(rid)
        self.db.atualizar(rid, "Ana", "1", "novo texto")
        self.db.sync_confirmar_envio([(uuid_, ts_antigo)])   # envio da versão velha
        self.assertEqual(self.db.sync_contar_pendentes(), 1)

    def test_todas_as_escritas_marcam_pendente(self):
        rid = self.db.inserir("Ana", "1", "x")
        for acao in (lambda: self.db.atualizar(rid, "Ana", "1", "y", prioridade="Urgente"),
                     lambda: self.db.excluir(rid),
                     lambda: self.db.restaurar([rid])):
            self.db.sync_confirmar_envio(
                [(self.estado(rid)[0], self.estado(rid)[2])])
            acao()
            self.assertEqual(self.estado(rid)[1], 1)

    def test_exclusao_definitiva_vira_remocao(self):
        rid = self.db.inserir("Ana", "1", "x")
        uuid_ = self.estado(rid)[0]
        self.db.excluir(rid)
        self.db.apagar_definitivamente([rid])
        remocoes = self.db.sync_remocoes()
        self.assertEqual([u for u, _ in remocoes], [uuid_])
        self.assertEqual(self.db.sync_contar_pendentes(), 1)

    def test_esvaziar_lixeira_gera_remocoes(self):
        ids = [self.db.inserir(n, "", "x") for n in ("A", "B")]
        self.db.excluir_varios(ids)
        self.db.esvaziar_lixeira()
        self.assertEqual(len(self.db.sync_remocoes()), 2)

    def test_migracao_de_banco_antigo(self):
        caminho = os.path.join(self.tmp.name, "antigo.db")
        conn = sqlite3.connect(caminho)
        conn.executescript("""
            CREATE TABLE solicitacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT NOT NULL,
                nome_paciente TEXT NOT NULL, contato TEXT, descricao TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pendente');
            INSERT INTO solicitacoes (data_hora, nome_paciente, contato, descricao)
                VALUES ('2025-01-01 10:00:00', 'Velho', '1', 'x'),
                       ('2025-01-02 10:00:00', 'Velha', '2', 'y');
        """)
        conn.commit()
        conn.close()
        db = Database(caminho)
        linhas = db._consultar("SELECT uuid, atualizado_em, sujo FROM solicitacoes")
        self.assertEqual(len({l[0] for l in linhas}), 2)
        self.assertTrue(all(l[0] and l[1] and l[2] == 1 for l in linhas))
        self.assertEqual(len(db.listar()), 2)
        Database(caminho)    # abrir de novo não muda nada
        self.assertEqual({l[0] for l in db._consultar("SELECT uuid FROM solicitacoes")},
                         {l[0] for l in linhas})

    def test_aplicar_remoto_regras(self):
        base = dict(uuid="u1", atualizado_em="2026-01-01 10:00:00.000", apagado=False,
                    data_hora="2026-01-01 09:00:00", nome="Nuvem", contato="9",
                    descricao="d", status="Pendente", lembrete=None, prioridade="Normal",
                    editado_em=None, excluido_em=None)
        self.assertEqual(self.db.sync_aplicar_remoto(base), "novo")
        self.assertEqual(self.db.sync_contar_pendentes(), 0)     # veio da nuvem: nada a enviar
        self.assertEqual(self.db.sync_aplicar_remoto(base), "ignorado")   # mesma versão
        mais_nova = {**base, "atualizado_em": "2026-01-01 11:00:00.000", "nome": "Editado"}
        self.assertEqual(self.db.sync_aplicar_remoto(mais_nova), "atualizado")
        self.assertEqual(self.db.listar()[0][2], "Editado")
        self.assertEqual(self.db.sync_contar_pendentes(), 0)
        mais_velha = {**base, "atualizado_em": "2026-01-01 08:00:00.000", "nome": "Velho"}
        self.assertEqual(self.db.sync_aplicar_remoto(mais_velha), "ignorado")
        apagado = {**base, "atualizado_em": "2026-01-01 12:00:00.000", "apagado": True}
        self.assertEqual(self.db.sync_aplicar_remoto(apagado), "removido")
        self.assertEqual(self.db.total_registros(), 0)
        self.assertEqual(self.db.sync_remocoes(), [])            # não ecoa de volta
        # linha apagada na nuvem que nunca existiu aqui
        self.assertEqual(self.db.sync_aplicar_remoto({**apagado, "uuid": "u9"}), "ignorado")

    def test_local_mais_novo_vence_e_exclusao_local_vence(self):
        rid = self.db.inserir("Local", "", "x")
        uuid_ = self.estado(rid)[0]
        remoto = dict(uuid=uuid_, atualizado_em="2000-01-01 00:00:00.000", apagado=False,
                      data_hora="2000-01-01 00:00:00", nome="Velho", contato="",
                      descricao="d", status="Pendente", lembrete=None,
                      prioridade="Normal", editado_em=None, excluido_em=None)
        self.assertEqual(self.db.sync_aplicar_remoto(remoto), "ignorado")
        self.assertEqual(self.db.listar()[0][2], "Local")
        # apago aqui (definitivo) e a nuvem ainda tem uma versão MAIS ANTIGA
        self.db.excluir(rid)
        self.db.apagar_definitivamente([rid])
        self.assertEqual(self.db.sync_aplicar_remoto(remoto), "ignorado")
        self.assertEqual(self.db.total_registros(), 0)
        # mas uma edição feita DEPOIS na nuvem traz o registro de volta
        futuro = {**remoto, "atualizado_em": "2999-01-01 00:00:00.000"}
        self.assertEqual(self.db.sync_aplicar_remoto(futuro), "novo")
        self.assertEqual(self.db.sync_remocoes(), [])

    def test_restaurar_backup_reenvia_tudo(self):
        self.db.inserir("A", "", "x")
        caminho = self.db.fazer_backup("b.db")
        self.db.sync_confirmar_envio(
            [(r["uuid"], r["atualizado_em"]) for r in self.db.sync_pendentes()])
        self.assertEqual(self.db.sync_contar_pendentes(), 0)
        self.db.restaurar_backup(caminho)
        self.assertEqual(self.db.sync_contar_pendentes(), 1)
        self.assertIsNotNone(self.db.sync_cursor())

    def test_resetar(self):
        rid = self.db.inserir("A", "", "x")
        self.db.sync_confirmar_envio(
            [(r["uuid"], r["atualizado_em"]) for r in self.db.sync_pendentes()])
        self.db.sync_definir_cursor("2026-01-01 00:00:00.000")
        self.db.sync_resetar()
        self.assertEqual(self.db.sync_contar_pendentes(), 1)
        self.assertIsNone(self.db.sync_cursor())

    def test_busca_e_listagem_continuam_iguais(self):
        self.db.inserir("João", "(85) 9", "dor de cabeça")
        self.assertEqual(len(self.db.listar("joao")), 1)
        self.assertEqual(len(self.db.listar("CABECA")), 1)


# ----------------------------------------------------------------------
class TestDatas(unittest.TestCase):
    def test_da_nuvem_formatos_do_postgres(self):
        self.assertEqual(da_nuvem("2026-11-08T12:00:00+00:00"), "2026-11-08 12:00:00.000")
        self.assertEqual(da_nuvem("2026-11-08T12:00:00.12+00:00"), "2026-11-08 12:00:00.120")
        self.assertEqual(da_nuvem("2026-11-08T12:00:00.123456Z"), "2026-11-08 12:00:00.123")
        self.assertEqual(da_nuvem("2026-11-08 12:00:00.5+00"), "2026-11-08 12:00:00.500")
        self.assertEqual(da_nuvem("2026-11-08T09:00:00-03:00"), "2026-11-08 12:00:00.000")
        self.assertEqual(da_nuvem("2026-11-08T15:30:00+0530"), "2026-11-08 10:00:00.000")
        with self.assertRaises(ValueError):
            da_nuvem("ontem")

    def test_ida_e_volta(self):
        ts = agora_utc()
        self.assertEqual(da_nuvem(para_nuvem(ts)), ts)

    def test_ordem_de_texto_igual_a_ordem_do_tempo(self):
        a, b = "2026-11-08 12:00:00.009", "2026-11-08 12:00:00.100"
        self.assertLess(a, b)
        self.assertLess(da_nuvem("2026-11-08T12:00:00.009Z"),
                        da_nuvem("2026-11-08T12:00:00.1Z"))


class TestValidacao(unittest.TestCase):
    def test_url(self):
        self.assertEqual(nuvem.normalizar_url("abc.supabase.co/"), "https://abc.supabase.co")
        self.assertEqual(nuvem.normalizar_url(" https://abc.supabase.co/rest/v1 "),
                         "https://abc.supabase.co")
        for ruim in ("", "http://abc.supabase.co", "localhost", "ftp://abc.supabase.co"):
            with self.assertRaises(ValueError, msg=ruim):
                nuvem.normalizar_url(ruim)

    def test_chave_secreta_recusada(self):
        import base64, json
        def jwt(papel):
            carga = base64.urlsafe_b64encode(json.dumps({"role": papel}).encode()).decode().rstrip("=")
            return f"eyJhbGciOiJIUzI1NiJ9.{carga}.assinatura1234567890"
        self.assertEqual(nuvem.validar_chave(jwt("anon")), jwt("anon"))
        self.assertEqual(nuvem.validar_chave(CHAVE), CHAVE)
        with self.assertRaises(ValueError):
            nuvem.validar_chave(jwt("service_role"))
        with self.assertRaises(ValueError):
            nuvem.validar_chave("sb_secret_" + "y" * 30)
        with self.assertRaises(ValueError):
            nuvem.validar_chave("curta")

    def test_email(self):
        self.assertEqual(nuvem.validar_email(" a@b.com "), "a@b.com")
        with self.assertRaises(ValueError):
            nuvem.validar_email("sem-arroba")

    def test_arquivo_sql_igual_ao_modulo(self):
        raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        caminho = os.path.join(raiz, "supabase", "setup.sql")
        with open(caminho, encoding="utf-8") as arq:
            self.assertEqual(arq.read(), SQL_CONFIGURACAO)
        self.assertIn("enable row level security", SQL_CONFIGURACAO)
        self.assertIn("revoke all", SQL_CONFIGURACAO)


# ----------------------------------------------------------------------
class TestCliente(BaseNuvem):
    def test_login_incorreto(self):
        c = ClienteSupabase(URL, CHAVE)
        with self.assertRaisesRegex(NuvemErro, "incorretos"):
            c.entrar(self.server.email, "errada")

    def test_tabela_inexistente(self):
        self.server.tabela_existe = False
        with self.assertRaisesRegex(NuvemErro, "tabela"):
            sincronizacao.testar_conexao(self.cliente())

    def test_renova_sessao_e_guarda_novo_refresh(self):
        guardados = []
        c = ClienteSupabase(URL, CHAVE, ao_renovar=guardados.append)
        c.entrar(self.server.email, self.server.senha)
        self.assertEqual(len(guardados), 1)
        c._expira = 0     # vence o token de acesso
        c.requisitar("GET", TABELA, {"select": "uuid"})
        self.assertEqual(len(guardados), 2)
        self.assertNotEqual(guardados[0], guardados[1])

    def test_retoma_com_refresh_salvo_sem_senha(self):
        c1 = self.cliente()
        c2 = ClienteSupabase(URL, CHAVE, refresh_token=c1.refresh_token)
        c2.requisitar("GET", TABELA, {"select": "uuid"})

    def test_refresh_invalido_pede_login(self):
        c = ClienteSupabase(URL, CHAVE, refresh_token="inexistente")
        with self.assertRaises(NuvemErro) as ctx:
            c.requisitar("GET", TABELA, {"select": "uuid"})
        self.assertTrue(ctx.exception.precisa_login)

    def test_token_rejeitado_no_meio_do_uso_tenta_renovar_uma_vez(self):
        c = self.cliente()
        self.server.expirar_acesso = True
        c.requisitar("GET", TABELA, {"select": "uuid"})    # não deve lançar

    def test_sem_conexao(self):
        self.server.offline = True
        c = ClienteSupabase(URL, CHAVE)
        with self.assertRaisesRegex(NuvemErro, "Sem conexão"):
            c.entrar("a@b.com", "x")

    def test_mensagens_de_erro_http(self):
        e = nuvem._erro_http
        self.assertIn("pausado", str(e(503, {})))
        self.assertIn("Muitas", str(e(429, {})))
        self.assertIn("permissão", str(e(403, {"code": "42501"})))
        self.assertIn("confirmado", str(e(400, {"msg": "Email not confirmed"})))


# ----------------------------------------------------------------------
class TestSincronizacao(BaseNuvem):
    def test_envio_inicial_e_nada_a_fazer_depois(self):
        db = self.novo_db()
        db.inserir("Ana", "(85) 1", "Consulta", prioridade="Urgente", lembrete="2030-01-01")
        db.inserir("Bia", "", "Exame")
        r = sincronizar(db, self.cliente())
        self.assertEqual((r.enviados, r.recebidos, r.erros), (2, 0, 0))
        self.assertEqual(len(self.server.linhas), 2)
        self.assertEqual(db.sync_contar_pendentes(), 0)
        linha = next(l for l in self.server.linhas.values() if l["nome"] == "Ana")
        self.assertEqual((linha["contato"], linha["prioridade"], linha["lembrete"]),
                         ("(85) 1", "Urgente", "2030-01-01"))
        self.assertFalse(linha["apagado"])
        r2 = sincronizar(db, self.cliente())
        self.assertEqual((r2.enviados, r2.recebidos, r2.removidos), (0, 0, 0))

    def test_dois_computadores(self):
        a, b = self.novo_db("a.db"), self.novo_db("b.db")
        a.inserir("Ana", "1", "da A")
        sincronizar(a, self.cliente())
        r = sincronizar(b, self.cliente())
        self.assertEqual(r.recebidos, 1)
        self.assertEqual([x[2] for x in b.listar()], ["Ana"])
        # B edita e conclui; A recebe
        rid_b = b.listar()[0][0]
        b.atualizar(rid_b, "Ana Maria", "1", "da A editada", prioridade="Urgente")
        b.atualizar_status(rid_b, "Atendida")
        sincronizar(b, self.cliente())
        r = sincronizar(a, self.cliente())
        self.assertEqual(r.recebidos, 1)
        reg = a.listar()[0]
        self.assertEqual((reg[2], reg[4], reg[5], reg[7]),
                         ("Ana Maria", "da A editada", "Atendida", "Urgente"))
        self.assertEqual(a.sync_contar_pendentes(), 0)

    def test_registros_diferentes_se_somam(self):
        a, b = self.novo_db("a.db"), self.novo_db("b.db")
        a.inserir("Ana", "", "x")
        b.inserir("Bia", "", "y")
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        sincronizar(a, self.cliente())
        self.assertEqual({r[2] for r in a.listar()}, {"Ana", "Bia"})
        self.assertEqual({r[2] for r in b.listar()}, {"Ana", "Bia"})

    def test_conflito_vale_o_mais_recente(self):
        a, b = self.novo_db("a.db"), self.novo_db("b.db")
        a.inserir("Ana", "", "original")
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        ra, rb = a.listar()[0][0], b.listar()[0][0]
        a.atualizar(ra, "Ana", "", "edição da A")
        sincronizar(a, self.cliente())                 # A envia primeiro
        # relógio do B: edição depois da A
        b.atualizar(rb, "Ana", "", "edição da B")
        b._executar("UPDATE solicitacoes SET atualizado_em = '2999-01-01 00:00:00.000'")
        sincronizar(b, self.cliente())
        sincronizar(a, self.cliente())
        self.assertEqual(a.listar()[0][4], "edição da B")
        self.assertEqual(b.listar()[0][4], "edição da B")

    def test_edicao_local_mais_antiga_perde_para_a_nuvem(self):
        a, b = self.novo_db("a.db"), self.novo_db("b.db")
        a.inserir("Ana", "", "original")
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        b.atualizar(b.listar()[0][0], "Ana", "", "edição velha da B")
        b._executar("UPDATE solicitacoes SET atualizado_em = '2000-01-01 00:00:00.000'")
        a.atualizar(a.listar()[0][0], "Ana", "", "edição nova da A")
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        self.assertEqual(b.listar()[0][4], "edição nova da A")

    def test_lixeira_e_restauracao_viajam(self):
        a, b = self.novo_db("a.db"), self.novo_db("b.db")
        rid = a.inserir("Ana", "", "x")
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        a.excluir(rid)
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        self.assertEqual(b.listar(), [])
        self.assertEqual(len(b.listar_lixeira()), 1)
        a.restaurar([rid])
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        self.assertEqual(len(b.listar()), 1)

    def test_exclusao_definitiva_apaga_o_conteudo_na_nuvem_e_no_outro(self):
        a, b = self.novo_db("a.db"), self.novo_db("b.db")
        rid = a.inserir("Paciente Secreto", "999", "informação sensível")
        sincronizar(a, self.cliente())
        sincronizar(b, self.cliente())
        a.excluir(rid)
        a.apagar_definitivamente([rid])
        r = sincronizar(a, self.cliente())
        self.assertEqual(r.enviados, 1)          # só a marca de remoção (o texto já saiu daqui)
        linha = next(iter(self.server.linhas.values()))
        self.assertTrue(linha["apagado"])
        self.assertEqual((linha["nome"], linha["descricao"], linha["contato"]), ("", "", None))
        self.assertNotIn("Secreto", str(self.server.linhas))
        r = sincronizar(b, self.cliente())
        self.assertEqual(r.removidos, 1)
        self.assertEqual(b.total_registros(), 0)
        self.assertEqual(b.sync_contar_pendentes(), 0)
        # depois de tudo, nenhuma das duas pontas tem pendência e nada "volta"
        sincronizar(a, self.cliente())
        self.assertEqual(a.total_registros(), 0)

    def test_falha_de_rede_mantem_pendente_e_retoma(self):
        db = self.novo_db()
        db.inserir("Ana", "", "x")
        cliente = self.cliente()
        self.server.offline = True
        with self.assertRaises(NuvemErro):
            sincronizar(db, cliente)
        self.assertEqual(db.sync_contar_pendentes(), 1)
        self.server.offline = False
        r = sincronizar(db, cliente)
        self.assertEqual(r.enviados, 1)
        self.assertEqual(db.sync_contar_pendentes(), 0)

    def test_lotes_e_paginas_com_muitos_registros_de_mesmo_horario(self):
        db = self.novo_db("a.db")
        for i in range(25):
            db.inserir(f"P{i:02d}", "", "x")
        db.sync_pos_restauracao()            # todos ficam com o MESMO atualizado_em
        outro = self.novo_db("b.db")
        with mock.patch.object(sincronizacao, "LOTE_ENVIO", 10), \
                mock.patch.object(sincronizacao, "PAGINA", 4):
            r = sincronizar(db, self.cliente())
            self.assertEqual(r.enviados, 25)
            self.assertEqual([len(p) for p in self.server.posts], [10, 10, 5])
            r = sincronizar(outro, self.cliente())
        self.assertEqual(r.recebidos, 25)
        self.assertEqual(outro.total_registros(), 25)

    def test_linha_invalida_da_nuvem_nao_derruba_a_sincronizacao(self):
        db = self.novo_db()
        self.server.linhas["x1"] = dict(
            uuid="x1", atualizado_em="2026-01-01T00:00:00Z", apagado=False,
            data_hora="2026-01-01 00:00:00", nome="Ruim", contato=None, descricao="d",
            status="INEXISTENTE", lembrete=None, prioridade="Normal",
            editado_em=None, excluido_em=None)
        self.server.linhas["x2"] = {**self.server.linhas["x1"], "uuid": "x2",
                                    "nome": "Boa", "status": "Pendente"}
        r = sincronizar(db, self.cliente())
        self.assertEqual((r.recebidos, r.erros), (1, 1))
        self.assertEqual([x[2] for x in db.listar()], ["Boa"])

    def test_cursor_avanca_e_evita_baixar_tudo_de_novo(self):
        a = self.novo_db("a.db")
        a.inserir("Ana", "", "x")
        sincronizar(a, self.cliente())
        sincronizar(a, self.cliente())    # a 2ª passada já vê as próprias linhas na nuvem
        self.assertIsNotNone(a.sync_cursor())
        r = sincronizar(a, self.cliente())
        self.assertEqual((r.recebidos, r.enviados), (0, 0))

    def test_reconectar_em_outra_conta_reenvia_tudo(self):
        db = self.novo_db()
        db.inserir("Ana", "", "x")
        sincronizar(db, self.cliente())
        db.sync_resetar()
        self.server.linhas.clear()           # outro projeto, vazio
        r = sincronizar(db, self.cliente())
        self.assertEqual(r.enviados, 1)
        self.assertEqual(len(self.server.linhas), 1)


if __name__ == "__main__":
    unittest.main()
