"""
admin.py
--------
Administração de usuários da nuvem (Supabase), SEM abrir o painel do Supabase.

Pensado para o ADMINISTRADOR, em linha de comando (veja scripts/usuarios_nuvem.py):

    python scripts/usuarios_nuvem.py listar
    python scripts/usuarios_nuvem.py criar medico@hospital.org --gerar-senha
    python scripts/usuarios_nuvem.py senha medico@hospital.org

Usa a chave SECRETA do projeto (Secret key / service_role). Ela pode tudo, por isso:
  * NUNCA vai para o programa, o repositório ou o GitHub: é lida da variável de ambiente
    SUPABASE_SERVICE_KEY ou digitada na hora (sem aparecer na tela);
  * a API de administração funciona mesmo com o cadastro aberto DESLIGADO no Supabase,
    que é o que se recomenda (assim ninguém de fora cria conta).
Sem interface (não importa nada de `interface/`).
"""

import argparse
import base64
import getpass
import json
import os
import secrets
from typing import Callable, List, Optional

from anotacoes.nuvem import projeto
from anotacoes.nuvem.cliente import (MIN_SENHA, ClienteSupabase, NuvemErro, normalizar_url,
                                     validar_email, validar_senha)

VARIAVEL_CHAVE = "SUPABASE_SERVICE_KEY"
VARIAVEL_URL = "SUPABASE_URL"
POR_PAGINA = 100
# sem caracteres parecidos (0/O, 1/l/I) para ser fácil de ler e digitar
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def gerar_senha(tamanho: int = 16) -> str:
    """Senha aleatória forte (letras e números sem ambiguidade)."""
    return "".join(secrets.choice(_ALFABETO) for _ in range(max(tamanho, MIN_SENHA)))


def _papel_jwt(chave: str) -> Optional[str]:
    try:
        carga = chave.split(".")[1]
        carga += "=" * (-len(carga) % 4)
        return json.loads(base64.urlsafe_b64decode(carga)).get("role")
    except Exception:
        return None


def validar_chave_servico(chave: str) -> str:
    """Aceita só a chave SECRETA (sb_secret_... ou JWT service_role). Recusa a pública."""
    chave = "".join((chave or "").split())
    if chave.startswith("sb_publishable_"):
        raise ValueError("Essa é a chave PÚBLICA. Para administrar usuários use a chave "
                         "SECRETA (Secret key ou service_role): Project Settings > API Keys.")
    if chave.startswith("sb_secret_") and len(chave) >= 20:
        return chave
    if chave.startswith("eyJ"):
        papel = _papel_jwt(chave)
        if papel == "service_role":
            return chave
        raise ValueError("Essa chave não é a service_role (papel: "
                         f"{papel or 'desconhecido'}). Use a Secret key / service_role.")
    raise ValueError("Chave de administrador não reconhecida. Use a Secret key "
                     "(sb_secret_...) ou a service_role do projeto.")


class AdminSupabase(ClienteSupabase):
    """Chamadas de administração (criar, listar e trocar senha de usuários)."""

    def __init__(self, url: str, chave_servico: str, timeout: float = 20) -> None:
        # Não chama o __init__ da base: ele recusa chaves secretas, que aqui são o objetivo.
        self.url = normalizar_url(url)
        self.chave = validar_chave_servico(chave_servico)
        self.refresh_token = None
        self.ao_renovar = None
        self.timeout = timeout
        self._acesso = None
        self._expira = 0.0

    def _admin(self, metodo: str, caminho: str, corpo=None):
        return self._http(metodo, "/auth/v1/admin" + caminho, corpo, None, self.chave)

    # --- operações -----------------------------------------------------
    def listar_usuarios(self) -> List[dict]:
        """Todos os usuários: [{'id', 'email', 'criado_em', 'ultimo_acesso', 'confirmado'}]."""
        usuarios, pagina = [], 1
        while True:
            resposta = self._admin("GET", f"/users?page={pagina}&per_page={POR_PAGINA}")
            lote = resposta.get("users", []) if isinstance(resposta, dict) else (resposta or [])
            usuarios += [{
                "id": u.get("id"),
                "email": u.get("email") or "",
                "criado_em": (u.get("created_at") or "")[:19].replace("T", " "),
                "ultimo_acesso": (u.get("last_sign_in_at") or "")[:19].replace("T", " "),
                "confirmado": bool(u.get("email_confirmed_at") or u.get("confirmed_at")),
            } for u in lote]
            if len(lote) < POR_PAGINA:
                return usuarios
            pagina += 1

    def criar_usuario(self, email: str, senha: str) -> dict:
        """Cria o usuário já confirmado (não depende de e-mail nem do cadastro aberto)."""
        email = validar_email(email)
        erro = validar_senha(senha)
        if erro:
            raise NuvemErro(erro)
        u = self._admin("POST", "/users", {"email": email, "password": senha,
                                            "email_confirm": True})
        return {"id": (u or {}).get("id"), "email": (u or {}).get("email") or email}

    def _achar(self, email: str) -> dict:
        email = validar_email(email).lower()
        for u in self.listar_usuarios():
            if u["email"].lower() == email:
                return u
        raise NuvemErro(f"Não existe usuário com o e-mail {email}.")

    def trocar_senha(self, email: str, senha: str) -> None:
        erro = validar_senha(senha)
        if erro:
            raise NuvemErro(erro)
        usuario = self._achar(email)
        self._admin("PUT", f"/users/{usuario['id']}", {"password": senha})

    def definir_papel(self, email: str, papel: str) -> None:
        """Define o papel ('admin' ou 'usuario') em app_metadata (só o servidor altera)."""
        if papel not in PAPEIS:
            raise NuvemErro("Papel inválido. Use admin ou usuario.")
        usuario = self._achar(email)
        self._admin("PUT", f"/users/{usuario['id']}",
                    {"app_metadata": {"role": papel}})


# ----------------------------------------------------------------------
# Linha de comando
# ----------------------------------------------------------------------
PAPEIS = ("admin", "usuario")


def _montar_parser() -> argparse.ArgumentParser:
    comum = argparse.ArgumentParser(add_help=False)
    comum.add_argument("--url", help=f"Project URL (padrão: ${VARIAVEL_URL} ou o de nuvem/projeto.py)")
    parser = argparse.ArgumentParser(
        prog="usuarios_nuvem",
        description="Administra os usuários da nuvem (Supabase) sem abrir o painel. "
                    f"A chave secreta vem de ${VARIAVEL_CHAVE} ou é digitada na hora.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("listar", parents=[comum], help="lista os usuários")
    for nome, ajuda in (("criar", "cria um usuário (já confirmado)"),
                        ("senha", "troca a senha de um usuário")):
        p = sub.add_parser(nome, parents=[comum], help=ajuda)
        p.add_argument("email")
        p.add_argument("--gerar-senha", action="store_true",
                       help="gera uma senha forte e mostra uma única vez")
        if nome == "criar":
            p.add_argument("--admin", action="store_true",
                           help="já cria como administrador do painel")
    p = sub.add_parser("papel", parents=[comum], help="define o papel: admin ou usuario")
    p.add_argument("email")
    p.add_argument("papel", choices=PAPEIS)
    return parser


def executar_cli(argv: List[str], ambiente: Optional[dict] = None,
                 ler_segredo: Callable[[str], str] = getpass.getpass,
                 saida: Callable[[str], None] = print) -> int:
    """Executa um comando. Retorna 0 em sucesso e 1 em erro (a mensagem vai para `saida`)."""
    ambiente = os.environ if ambiente is None else ambiente
    args = _montar_parser().parse_args(argv)
    try:
        url = args.url or ambiente.get(VARIAVEL_URL) or projeto.URL_PROJETO
        chave = ambiente.get(VARIAVEL_CHAVE) or ler_segredo(
            "Chave secreta do Supabase (não aparece ao digitar): ")
        admin = AdminSupabase(url, chave)

        if args.comando == "listar":
            usuarios = admin.listar_usuarios()
            if not usuarios:
                saida("Nenhum usuário cadastrado.")
            for u in usuarios:
                saida(f"{u['email']:<40} criado em {u['criado_em'] or '-':<19}  "
                      f"último acesso {u['ultimo_acesso'] or 'nunca'}"
                      + ("" if u["confirmado"] else "   (e-mail não confirmado)"))
            saida(f"{len(usuarios)} usuário(s).")
            return 0

        if args.comando == "papel":
            admin.definir_papel(args.email, args.papel)
            saida(f"{args.email} agora é {args.papel}. "
                  "Vale no próximo login (ou quando a sessão renovar).")
            return 0

        if args.gerar_senha:
            senha = gerar_senha()
        else:
            senha = ler_segredo(f"Senha para {args.email} (mín. {MIN_SENHA} caracteres): ")
            if senha != ler_segredo("Repita a senha: "):
                raise ValueError("As senhas não conferem.")
        if args.comando == "criar":
            usuario = admin.criar_usuario(args.email, senha)
            saida(f"Usuário criado: {usuario['email']}")
            if args.admin:
                admin.definir_papel(usuario["email"], "admin")
                saida("Papel: administrador.")
        else:
            admin.trocar_senha(args.email, senha)
            saida(f"Senha de {args.email} alterada.")
        if args.gerar_senha:
            saida(f"Senha gerada (anote agora; não será mostrada de novo): {senha}")
        saida("No programa: Nuvem > e-mail e senha > Conectar e sincronizar.")
        return 0
    except (ValueError, NuvemErro) as exc:
        saida(f"Erro: {exc}")
        return 1
