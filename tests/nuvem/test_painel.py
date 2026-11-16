"""Painel de controle: cliente (rpc + erros), nuvem/painel.py, indicadores locais e o SQL."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from anotacoes.nucleo.database import Database
from anotacoes.nuvem import cliente, painel
from anotacoes.nuvem.cliente import ClienteSupabase, NuvemErro
from anotacoes.nuvem.sql import SQL_PAINEL

URL = "https://abcdefgh.supabase.co"
PUBLICA = "sb_publishable_" + "p" * 30


class FakeRpc:
    def __init__(self, respostas):
        self.respostas, self.chamadas = respostas, []

    def http(self, cli, metodo, caminho, corpo=None, cabecalhos=None, token=None):
        self.chamadas.append((metodo, caminho, corpo, token))
        if caminho.startswith("/auth/v1/token"):
            return {"access_token": "acesso", "refresh_token": "r2", "expires_in": 3600}
        resposta = self.respostas[caminho.rsplit("/", 1)[1]]
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def _cliente(respostas):
    fake = FakeRpc(respostas)
    p = mock.patch.object(ClienteSupabase, "_http", lambda cli, *a, **k: fake.http(cli, *a, **k))
    p.start()
    c = ClienteSupabase(URL, PUBLICA, refresh_token="r1")
    return c, fake, p


class TestRpcEErros(unittest.TestCase):
    def test_rpc_usa_o_token_do_usuario(self):
        c, fake, p = _cliente({"painel_meu_papel": "admin"})
        self.addCleanup(p.stop)
        self.assertEqual(painel.meu_papel(c), "admin")
        metodo, caminho, corpo, token = fake.chamadas[-1]
        self.assertEqual((metodo, caminho, corpo, token), ("POST", "/rest/v1/rpc/painel_meu_papel", {}, "acesso"))

    def test_resposta_estranha_vira_usuario(self):
        for estranha in (None, "", "ADMIN", True, {"role": "admin"}, ["admin"]):
            c, _f, p = _cliente({"painel_meu_papel": estranha})
            self.addCleanup(p.stop)
            self.assertEqual(painel.meu_papel(c), "usuario", msg=repr(estranha))

    def test_mensagens_de_erro(self):
        casos = [
            (403, {"code": "PT403", "message": "x"}, "administradores"),
            (400, {"code": "PT400", "message": "Você não pode desativar o seu próprio acesso."}, "próprio acesso"),
            (404, {"code": "PT404", "message": "Usuário não encontrado."}, "não encontrado"),
            (404, {"code": "PGRST202", "message": "Could not find the function public.painel_meu_papel"}, "SQL do painel"),
        ]
        for http, detalhe, trecho in casos:
            self.assertIn(trecho, str(cliente._erro_http(http, detalhe)), msg=str(detalhe))

    def test_403_comum_continua_sendo_permissao_de_tabela(self):
        self.assertIn("Sem permissão", str(cliente._erro_http(403, {"code": "42501"})))


class TestPainelNuvem(unittest.TestCase):
    def test_listar_usuarios_normaliza(self):
        bruto = [
            {"id": "a", "email": "a@x.co", "papel": "admin", "ativo": True, "registros": "5",
             "pendentes": 2, "atendidas": 3, "urgentes": 1, "criado_em": "2026-01-02T10:00:00+00:00",
             "ultimo_acesso": None, "ultima_atividade": "lixo"},
            {"id": "b", "email": "b@x.co", "papel": "qualquer", "ativo": False, "registros": -4},
            {"email": "sem-id@x.co"}, "texto solto",
        ]
        c, _f, p = _cliente({"painel_listar_usuarios": bruto})
        self.addCleanup(p.stop)
        usuarios = painel.listar_usuarios(c)
        self.assertEqual([u.email for u in usuarios], ["a@x.co", "b@x.co"])
        self.assertTrue(usuarios[0].eh_admin)
        self.assertFalse(usuarios[1].eh_admin)          # papel desconhecido nunca vira admin
        self.assertEqual((usuarios[0].registros, usuarios[1].registros), (5, 0))
        self.assertEqual((usuarios[0].ultimo_acesso, usuarios[0].ultima_atividade), ("-", "-"))
        soma = painel.totais(usuarios)
        self.assertEqual((soma["usuarios"], soma["ativos"], soma["admins"], soma["registros"]), (2, 1, 1, 5))

    def test_lista_vazia_ou_invalida(self):
        c, _f, p = _cliente({"painel_listar_usuarios": None, "painel_listar_auditoria": {"x": 1}})
        self.addCleanup(p.stop)
        self.assertEqual(painel.listar_usuarios(c), [])
        self.assertEqual(painel.listar_auditoria(c), [])

    def test_acoes_enviam_os_parametros_certos(self):
        c, fake, p = _cliente({"painel_definir_acesso": None, "painel_definir_papel": None})
        self.addCleanup(p.stop)
        painel.definir_acesso(c, "u1", False)
        painel.definir_papel(c, "u1", "admin")
        corpos = [x[2] for x in fake.chamadas if x[1].startswith("/rest/")]
        self.assertEqual(corpos, [{"p_usuario": "u1", "p_ativo": False},
                                  {"p_usuario": "u1", "p_papel": "admin"}])
        with self.assertRaises(NuvemErro):
            painel.definir_papel(c, "u1", "root")

    def test_criar_usuario(self):
        c, fake, p = _cliente({"painel_criar_usuario": "novo-id"})
        self.addCleanup(p.stop)
        self.assertEqual(painel.criar_usuario(c, "  Ana@X.co ", "SenhaForte123", "admin"), "novo-id")
        self.assertEqual(fake.chamadas[-1][2], {"p_email": "Ana@X.co", "p_senha": "SenhaForte123", "p_papel": "admin"})
        n = len(fake.chamadas)
        for email, senha, papel in (("sem-arroba", "SenhaForte123", "usuario"),
                                    ("a@b.co", "curta", "usuario"), ("a@b.co", "SenhaForte123", "root")):
            with self.assertRaises(NuvemErro):
                painel.criar_usuario(c, email, senha, papel)
        self.assertEqual(len(fake.chamadas), n)          # nada inválido sai do computador

    def test_gerar_senha_fica_no_cliente(self):
        a, b = cliente.gerar_senha(), cliente.gerar_senha()
        self.assertEqual(len(a), 16)
        self.assertNotEqual(a, b)
        self.assertIsNone(cliente.validar_senha(a))

    def test_erro_do_servidor_sobe(self):
        c, _f, p = _cliente({"painel_listar_usuarios": cliente._erro_http(403, {"code": "PT403"})})
        self.addCleanup(p.stop)
        with self.assertRaisesRegex(NuvemErro, "administradores"):
            painel.listar_usuarios(c)

    def test_descrever_acao_e_datas(self):
        a = painel.AcaoAuditoria("10/11/2026 09:00", "adm@x.co", "definir_papel", "b@x.co", "admin")
        self.assertEqual(painel.descrever_acao(a), "adm@x.co alterou o papel de b@x.co (Administrador)")
        a = painel.AcaoAuditoria("-", "adm@x.co", "desativar_acesso", "b@x.co", "")
        self.assertIn("desativou o acesso de b@x.co", painel.descrever_acao(a))
        a = painel.AcaoAuditoria("-", "adm@x.co", "criar_usuario", "n@x.co", "usuario")
        self.assertEqual(painel.descrever_acao(a), "adm@x.co criou a conta de n@x.co (Usuário)")
        self.assertEqual(painel.formatar_data(None), "-")
        self.assertEqual(painel.formatar_data("nada"), "-")
        self.assertRegex(painel.formatar_data("2026-11-08T12:00:00.5Z"), r"^\d\d/\d\d/2026 \d\d:\d\d$")
        self.assertRegex(painel.formatar_data("2026-11-08T12:00:00Z", False), r"^\d\d/11/2026$")


class TestIndicadores(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.db = Database(os.path.join(self.pasta.name, "t.db"))
        self.addCleanup(self.db.fechar) if hasattr(self.db, "fechar") else None

    def _inserir(self, dias_atras, status="Pendente", urgente=False):
        d = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d 10:00:00")
        self.db._executar(
            "INSERT INTO solicitacoes (data_hora, nome_paciente, contato, descricao, status, prioridade) "
            "VALUES (?, 'Nome', 'c', 'texto', ?, ?)", (d, status, "Urgente" if urgente else "Normal"))

    def test_vazio(self):
        ind = self.db.indicadores(14)
        self.assertEqual((ind["total"], ind["pendentes"], ind["atendidas"]), (0, 0, 0))
        self.assertEqual(len(ind["por_dia"]), 14)
        self.assertTrue(all(n == 0 for _d, n in ind["por_dia"]))

    def test_contagens_e_grafico(self):
        self._inserir(0); self._inserir(0, "Atendida"); self._inserir(1, urgente=True)
        self._inserir(10); self._inserir(30, "Atendida")
        ind = self.db.indicadores(14)
        self.assertEqual((ind["total"], ind["pendentes"], ind["atendidas"]), (5, 3, 2))
        self.assertEqual((ind["urgentes"], ind["hoje"], ind["antigas"]), (1, 2, 1))
        dias = dict(ind["por_dia"])
        hoje = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(dias[hoje], 2)
        self.assertEqual(sum(dias.values()), 4)          # o de 30 dias fica fora da janela
        self.assertEqual(ind["por_dia"][-1][0], hoje)

    def test_lixeira_nao_conta_e_nao_vaza_texto(self):
        self._inserir(0)
        self.db.excluir(1)
        ind = self.db.indicadores()
        self.assertEqual(ind["total"], 0)
        self.assertNotIn("texto", repr(ind))


class TestSqlDoPainel(unittest.TestCase):
    def test_arquivo_igual_ao_modulo(self):
        raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(raiz, "supabase", "painel.sql"), encoding="utf-8") as arq:
            self.assertEqual(arq.read(), SQL_PAINEL)

    def test_protecoes_essenciais(self):
        sql = SQL_PAINEL.lower()
        self.assertEqual(sql.count("security definer"), sql.count("set search_path = ''") )
        for nome in ("listar_usuarios", "definir_acesso", "definir_papel", "listar_auditoria"):
            self.assertIn(f"public.painel_{nome}", sql)
        self.assertIn("perform public.painel_exigir_admin()", sql)
        self.assertIn("from public, anon", sql)
        self.assertIn("enable row level security", sql)
        # nenhuma coluna de texto de paciente é lida pelo painel
        codigo = "\n".join(l.split("--")[0] for l in sql.splitlines())   # ignora comentários
        for proibido in ("nome_paciente", "descricao", "contato"):
            self.assertNotIn(proibido, codigo)
        # o papel vem de app_metadata (só o servidor altera), nunca de user_metadata
        self.assertIn("raw_app_meta_data", sql)
        self.assertNotIn("raw_user_meta_data ->", sql)      # nunca LÊ o papel de user_metadata
        self.assertIn("public.painel_criar_usuario(text, text, text) from public, anon", sql)


if __name__ == "__main__":
    unittest.main()
