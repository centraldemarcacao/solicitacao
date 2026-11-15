"""Administração de usuários (nuvem/admin.py), cadastro pelo cliente e a linha de comando.

Sem internet: um Supabase de mentira (FakeAuth) responde no lugar da rede.
"""

import base64
import json
import unittest
from unittest import mock

from anotacoes.nuvem import admin, cliente
from anotacoes.nuvem.admin import AdminSupabase, executar_cli, gerar_senha, validar_chave_servico
from anotacoes.nuvem.cliente import ClienteSupabase, NuvemErro

URL = "https://abcdefgh.supabase.co"
SECRETA = "sb_secret_" + "s" * 30
PUBLICA = "sb_publishable_" + "p" * 30


def _jwt(papel: str) -> str:
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'HS256'})}.{b64({'role': papel})}.assinatura"


class FakeAuth:
    """Imita /auth/v1/admin/users e /auth/v1/signup."""

    def __init__(self):
        self.usuarios = []                 # dicts como o Supabase devolve
        self.cadastro_aberto = False
        self.exigir_confirmacao = False
        self.chamadas = []
        self.chave_valida = SECRETA

    def adicionar(self, email, senha="x" * 8):
        u = {"id": f"id{len(self.usuarios) + 1}", "email": email, "password": senha,
             "created_at": "2026-11-01T10:00:00.123Z", "last_sign_in_at": None,
             "email_confirmed_at": "2026-11-01T10:00:00Z"}
        self.usuarios.append(u)
        return u

    def http(self, cli, metodo, caminho, corpo=None, cabecalhos=None, token=None):
        self.chamadas.append((metodo, caminho, corpo, token))
        if caminho.startswith("/auth/v1/admin"):
            if token != self.chave_valida:
                raise cliente._erro_http(401, {"message": "invalid JWT: unable to parse"})
            return self._admin(metodo, caminho, corpo)
        if caminho == "/auth/v1/signup":
            if not self.cadastro_aberto:
                raise cliente._erro_http(422, {"error_code": "signup_disabled",
                                               "msg": "Signups not allowed for this instance"})
            if any(u["email"] == corpo["email"] for u in self.usuarios):
                raise cliente._erro_http(422, {"error_code": "user_already_exists",
                                               "msg": "User already registered"})
            if len(corpo["password"]) < 6:
                raise cliente._erro_http(422, {"error_code": "weak_password",
                                               "msg": "Password should be at least 6 characters."})
            u = self.adicionar(corpo["email"], corpo["password"])
            if self.exigir_confirmacao:
                u["email_confirmed_at"] = None
                return {"id": u["id"], "email": u["email"]}
            return {"access_token": "tok1", "refresh_token": "r1", "expires_in": 3600}
        raise AssertionError(caminho)

    def _admin(self, metodo, caminho, corpo):
        if metodo == "GET":
            pagina = int(caminho.split("page=")[1].split("&")[0])
            por = int(caminho.split("per_page=")[1])
            lote = self.usuarios[(pagina - 1) * por: pagina * por]
            return {"users": [{k: v for k, v in u.items() if k != "password"} for u in lote]}
        if metodo == "POST":
            if any(u["email"] == corpo["email"] for u in self.usuarios):
                raise cliente._erro_http(422, {"error_code": "email_exists",
                                               "msg": "A user with this email address has already been registered"})
            assert corpo["email_confirm"] is True
            u = self.adicionar(corpo["email"], corpo["password"])
            return {"id": u["id"], "email": u["email"]}
        if metodo == "PUT":
            uid = caminho.rsplit("/", 1)[1]
            usuario = next(u for u in self.usuarios if u["id"] == uid)
            usuario["password"] = corpo["password"]
            return {"id": uid}
        raise AssertionError(metodo)


class Base(unittest.TestCase):
    def setUp(self):
        self.server = FakeAuth()
        p = mock.patch.object(ClienteSupabase, "_http",
                              lambda cli, *a, **k: self.server.http(cli, *a, **k))
        p.start()
        self.addCleanup(p.stop)


class TestChaveServico(unittest.TestCase):
    def test_aceita_secreta_e_service_role(self):
        self.assertEqual(validar_chave_servico(SECRETA), SECRETA)
        jwt = _jwt("service_role")
        self.assertEqual(validar_chave_servico(" " + jwt + "\n"), jwt)

    def test_recusa_chave_publica_e_anon(self):
        for ruim in (PUBLICA, _jwt("anon"), "", "qualquer coisa", "sb_secret_curta"):
            with self.assertRaises(ValueError, msg=ruim):
                validar_chave_servico(ruim)

    def test_gerar_senha(self):
        a, b = gerar_senha(), gerar_senha()
        self.assertEqual(len(a), 16)
        self.assertNotEqual(a, b)
        self.assertFalse(set(a) & set("0O1lI"))


class TestAdmin(Base):
    def adm(self):
        return AdminSupabase(URL, SECRETA)

    def test_o_cliente_comum_continua_recusando_chave_secreta(self):
        with self.assertRaises(ValueError):
            ClienteSupabase(URL, SECRETA)

    def test_criar_usuario_confirmado_e_sem_depender_do_cadastro_aberto(self):
        self.assertFalse(self.server.cadastro_aberto)
        u = self.adm().criar_usuario("Medico@Hospital.org", "SenhaForte123")
        self.assertEqual(u["email"], "Medico@Hospital.org")
        metodo, caminho, corpo, token = self.server.chamadas[-1]
        self.assertEqual((metodo, caminho, token), ("POST", "/auth/v1/admin/users", SECRETA))
        self.assertTrue(corpo["email_confirm"])

    def test_criar_validacoes(self):
        for email, senha in (("sem-arroba", "SenhaForte123"), ("a@b.co", "curta")):
            with self.assertRaises((ValueError, NuvemErro)):
                self.adm().criar_usuario(email, senha)
        self.assertEqual(self.server.chamadas, [])

    def test_criar_duplicado(self):
        self.server.adicionar("a@b.co")
        with self.assertRaisesRegex(NuvemErro, "Já existe"):
            self.adm().criar_usuario("a@b.co", "SenhaForte123")

    def test_listar_com_paginacao(self):
        for i in range(admin.POR_PAGINA + 5):
            self.server.adicionar(f"u{i}@x.co")
        usuarios = self.adm().listar_usuarios()
        self.assertEqual(len(usuarios), admin.POR_PAGINA + 5)
        self.assertEqual(usuarios[0]["criado_em"], "2026-11-01 10:00:00")
        self.assertTrue(usuarios[0]["confirmado"])

    def test_trocar_senha(self):
        self.server.adicionar("a@b.co", "antiga-123")
        self.adm().trocar_senha("A@B.co", "NovaSenha456")      # ignora maiúsculas
        self.assertEqual(self.server.usuarios[0]["password"], "NovaSenha456")

    def test_trocar_senha_de_quem_nao_existe(self):
        with self.assertRaisesRegex(NuvemErro, "Não existe usuário"):
            self.adm().trocar_senha("ninguem@x.co", "NovaSenha456")

    def test_chave_errada_da_erro_claro(self):
        self.server.chave_valida = "outra"
        with self.assertRaises(NuvemErro):
            self.adm().listar_usuarios()


class TestCadastroNoCliente(Base):
    def cli(self):
        return ClienteSupabase(URL, PUBLICA)

    def test_cadastro_fechado_explica(self):
        with self.assertRaisesRegex(NuvemErro, "desativado"):
            self.cli().cadastrar("a@b.co", "SenhaForte123")

    def test_cadastro_aberto_ja_conecta(self):
        self.server.cadastro_aberto = True
        c = self.cli()
        self.assertEqual(c.cadastrar("a@b.co", "SenhaForte123"), "conectado")
        self.assertEqual(c.refresh_token, "r1")

    def test_cadastro_com_confirmacao_de_email(self):
        self.server.cadastro_aberto = self.server.exigir_confirmacao = True
        c = self.cli()
        self.assertEqual(c.cadastrar("a@b.co", "SenhaForte123"), "confirmar_email")
        self.assertIsNone(c.refresh_token)

    def test_email_ja_cadastrado(self):
        self.server.cadastro_aberto = True
        self.server.adicionar("a@b.co")
        with self.assertRaisesRegex(NuvemErro, "Já existe uma conta"):
            self.cli().cadastrar("a@b.co", "SenhaForte123")

    def test_senha_curta_nem_sai_do_computador(self):
        self.server.cadastro_aberto = True
        with self.assertRaisesRegex(NuvemErro, "pelo menos 8"):
            self.cli().cadastrar("a@b.co", "1234567")
        self.assertEqual(self.server.chamadas, [])

    def test_senha_fraca_recusada_pelo_servidor(self):
        e = cliente._erro_http(422, {"error_code": "weak_password",
                                     "msg": "Password should be at least 6 characters."})
        self.assertIn("Senha fraca", str(e))


class TestCli(Base):
    def rodar(self, argv, ambiente=None, segredos=()):
        saida, entradas = [], list(segredos)
        amb = {admin.VARIAVEL_CHAVE: SECRETA} if ambiente is None else ambiente
        codigo = executar_cli(argv, ambiente=amb, ler_segredo=lambda _p: entradas.pop(0),
                              saida=saida.append)
        return codigo, "\n".join(saida)

    def test_criar_com_senha_gerada(self):
        codigo, texto = self.rodar(["criar", "a@b.co", "--gerar-senha"])
        self.assertEqual(codigo, 0)
        senha = self.server.usuarios[0]["password"]
        self.assertIn(senha, texto)                  # mostrada uma vez
        self.assertNotIn(SECRETA, texto)

    def test_criar_digitando_a_senha(self):
        codigo, texto = self.rodar(["criar", "a@b.co"], segredos=["SenhaForte123", "SenhaForte123"])
        self.assertEqual(codigo, 0)
        self.assertEqual(self.server.usuarios[0]["password"], "SenhaForte123")
        self.assertNotIn("SenhaForte123", texto)     # a senha digitada nunca é repetida

    def test_senhas_diferentes(self):
        codigo, texto = self.rodar(["criar", "a@b.co"], segredos=["SenhaForte123", "outra-coisa"])
        self.assertEqual(codigo, 1)
        self.assertIn("não conferem", texto)
        self.assertEqual(self.server.usuarios, [])

    def test_pede_a_chave_quando_nao_ha_variavel(self):
        codigo, _ = self.rodar(["listar"], ambiente={}, segredos=[SECRETA])
        self.assertEqual(codigo, 0)

    def test_recusa_chave_publica(self):
        codigo, texto = self.rodar(["listar"], ambiente={admin.VARIAVEL_CHAVE: PUBLICA})
        self.assertEqual(codigo, 1)
        self.assertIn("PÚBLICA", texto)
        self.assertEqual(self.server.chamadas, [])

    def test_listar(self):
        self.server.adicionar("a@b.co")
        u = self.server.adicionar("c@d.co")
        u["email_confirmed_at"] = None
        codigo, texto = self.rodar(["listar"])
        self.assertEqual(codigo, 0)
        self.assertIn("a@b.co", texto)
        self.assertIn("e-mail não confirmado", texto)
        self.assertIn("2 usuário(s).", texto)

    def test_trocar_senha(self):
        self.server.adicionar("a@b.co", "antiga-123")
        codigo, texto = self.rodar(["senha", "a@b.co", "--gerar-senha"])
        self.assertEqual(codigo, 0)
        self.assertNotEqual(self.server.usuarios[0]["password"], "antiga-123")
        self.assertIn("alterada", texto)

    def test_usuario_inexistente(self):
        codigo, texto = self.rodar(["senha", "x@y.co", "--gerar-senha"])
        self.assertEqual(codigo, 1)
        self.assertIn("Não existe usuário", texto)

    def test_usa_a_url_do_projeto_por_padrao_e_aceita_outra(self):
        usadas = []
        original = AdminSupabase.__init__

        def espiao(self, url, *a, **k):
            usadas.append(url)
            original(self, url, *a, **k)
        with mock.patch.object(AdminSupabase, "__init__", espiao):
            self.rodar(["listar"])
            self.rodar(["listar", "--url", "https://outro.supabase.co"])
        self.assertEqual(usadas[0], admin.projeto.URL_PROJETO)
        self.assertEqual(usadas[1], "https://outro.supabase.co")


if __name__ == "__main__":
    unittest.main()
