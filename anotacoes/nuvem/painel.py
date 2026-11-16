"""
painel.py
---------
Lado do programa para o painel de controle (funções `painel_*` do Supabase).

Só guarda e repassa NÚMEROS e contas: o servidor nunca devolve texto de paciente. A decisão
de quem é administrador é do servidor (`painel_meu_papel`); aqui nada é "confiado" a partir
do que o usuário digita ou do que está no computador.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from anotacoes.nuvem.cliente import ClienteSupabase, NuvemErro, validar_email, validar_senha
from anotacoes.nuvem.sincronizacao import da_nuvem

PAPEL_ADMIN = "admin"
PAPEL_USUARIO = "usuario"
ROTULO_PAPEL = {PAPEL_ADMIN: "Administrador", PAPEL_USUARIO: "Usuário"}

_ACOES = {
    "ativar_acesso": "ativou o acesso de",
    "desativar_acesso": "desativou o acesso de",
    "definir_papel": "alterou o papel de",
    "criar_usuario": "criou a conta de",
}


@dataclass(frozen=True)
class UsuarioPainel:
    id: str
    email: str
    papel: str
    ativo: bool
    criado_em: str
    ultimo_acesso: str
    registros: int
    pendentes: int
    atendidas: int
    urgentes: int
    ultima_atividade: str

    @property
    def eh_admin(self) -> bool:
        return self.papel == PAPEL_ADMIN


@dataclass(frozen=True)
class AcaoAuditoria:
    quando: str
    admin_email: str
    acao: str
    alvo_email: str
    detalhe: str


def formatar_data(valor: Optional[str], com_hora: bool = True) -> str:
    """ISO do servidor -> data local legível ('-' se vazio ou ilegível)."""
    if not valor:
        return "-"
    try:
        utc = datetime.strptime(da_nuvem(valor)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "-"
    local = utc.replace(tzinfo=timezone.utc).astimezone()
    return local.strftime("%d/%m/%Y %H:%M" if com_hora else "%d/%m/%Y")


def _inteiro(valor) -> int:
    try:
        return max(0, int(valor or 0))
    except (TypeError, ValueError):
        return 0


def _lista(resposta) -> list:
    return resposta if isinstance(resposta, list) else []


def meu_papel(cliente: ClienteSupabase) -> str:
    """Papel confirmado pelo servidor. Qualquer resposta estranha vira 'usuario'."""
    resposta = cliente.rpc("painel_meu_papel")
    return PAPEL_ADMIN if resposta == PAPEL_ADMIN else PAPEL_USUARIO


def listar_usuarios(cliente: ClienteSupabase) -> List[UsuarioPainel]:
    usuarios = []
    for u in _lista(cliente.rpc("painel_listar_usuarios")):
        if not isinstance(u, dict) or not u.get("id"):
            continue
        usuarios.append(UsuarioPainel(
            id=str(u["id"]), email=str(u.get("email") or ""),
            papel=PAPEL_ADMIN if u.get("papel") == PAPEL_ADMIN else PAPEL_USUARIO,
            ativo=bool(u.get("ativo", True)),
            criado_em=formatar_data(u.get("criado_em"), False),
            ultimo_acesso=formatar_data(u.get("ultimo_acesso")),
            registros=_inteiro(u.get("registros")), pendentes=_inteiro(u.get("pendentes")),
            atendidas=_inteiro(u.get("atendidas")), urgentes=_inteiro(u.get("urgentes")),
            ultima_atividade=formatar_data(u.get("ultima_atividade")),
        ))
    return usuarios


def totais(usuarios: List[UsuarioPainel]) -> dict:
    """Somas para os cartões da administração."""
    return {
        "usuarios": len(usuarios),
        "ativos": sum(1 for u in usuarios if u.ativo),
        "admins": sum(1 for u in usuarios if u.eh_admin),
        "registros": sum(u.registros for u in usuarios),
        "pendentes": sum(u.pendentes for u in usuarios),
        "atendidas": sum(u.atendidas for u in usuarios),
        "urgentes": sum(u.urgentes for u in usuarios),
    }


def definir_acesso(cliente: ClienteSupabase, usuario_id: str, ativo: bool) -> None:
    cliente.rpc("painel_definir_acesso", {"p_usuario": usuario_id, "p_ativo": bool(ativo)})


def definir_papel(cliente: ClienteSupabase, usuario_id: str, papel: str) -> None:
    if papel not in ROTULO_PAPEL:
        raise NuvemErro("Papel inválido.")
    cliente.rpc("painel_definir_papel", {"p_usuario": usuario_id, "p_papel": papel})


def criar_usuario(cliente: ClienteSupabase, email: str, senha: str, papel: str = PAPEL_USUARIO) -> str:
    """Cria uma conta já confirmada (função do servidor; só administradores). Devolve o id."""
    try:
        email = validar_email(email)
    except ValueError as exc:
        raise NuvemErro(str(exc)) from None
    erro = validar_senha(senha)
    if erro:
        raise NuvemErro(erro)
    if papel not in ROTULO_PAPEL:
        raise NuvemErro("Papel inválido.")
    return str(cliente.rpc("painel_criar_usuario",
                           {"p_email": email, "p_senha": senha, "p_papel": papel}) or "")


def listar_auditoria(cliente: ClienteSupabase, limite: int = 20) -> List[AcaoAuditoria]:
    itens = []
    for a in _lista(cliente.rpc("painel_listar_auditoria", {"p_limite": int(limite)})):
        if isinstance(a, dict):
            itens.append(AcaoAuditoria(
                quando=formatar_data(a.get("quando")), admin_email=str(a.get("admin_email") or ""),
                acao=str(a.get("acao") or ""), alvo_email=str(a.get("alvo_email") or ""),
                detalhe=str(a.get("detalhe") or "")))
    return itens


def descrever_acao(a: AcaoAuditoria) -> str:
    """'admin@x ativou o acesso de fulano@y' (papel novo entre parênteses)."""
    verbo = _ACOES.get(a.acao, a.acao or "executou uma ação em")
    extra = (f" ({ROTULO_PAPEL.get(a.detalhe, a.detalhe)})"
             if a.acao in ("definir_papel", "criar_usuario") and a.detalhe else "")
    return f"{a.admin_email or 'Alguém'} {verbo} {a.alvo_email or '-'}{extra}"
