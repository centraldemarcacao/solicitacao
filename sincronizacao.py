"""
sincronizacao.py
----------------
Mantém a cópia na nuvem (Supabase) igual ao banco local.

Regras:
  - O banco local (SQLite) continua sendo o principal: o programa funciona
    normalmente sem internet e envia o que ficou pendente quando voltar.
  - Cada registro tem um identificador próprio (uuid) e a data da última
    alteração (UTC). Em caso de conflito, vale a alteração mais recente.
  - Exclusões definitivas viajam como "marcas de remoção" que apagam o
    conteúdo na nuvem (o texto do paciente não fica lá).
  - Ordem: primeiro baixa o que mudou na nuvem, depois envia o que mudou aqui.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from database import Database
from nuvem import ClienteSupabase, NuvemErro
from nuvem_sql import TABELA

LOTE_ENVIO = 100
PAGINA = 500
SOBREPOSICAO = timedelta(minutes=2)   # tolera diferença de relógio entre computadores
_FORMATO = "%Y-%m-%d %H:%M:%S"


@dataclass
class Resultado:
    enviados: int = 0
    recebidos: int = 0      # registros novos ou atualizados vindos da nuvem
    removidos: int = 0
    erros: int = 0

    @property
    def mudou_localmente(self) -> bool:
        return bool(self.recebidos or self.removidos)


# ----------------------------------------------------------------------
# Conversão de datas: local 'AAAA-MM-DD HH:MM:SS.mmm' (UTC) <-> ISO do servidor
# ----------------------------------------------------------------------
_ISO = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d+))?\s*(Z|[+-]\d{2}(?::?\d{2})?)?$")


def para_nuvem(ts: str) -> str:
    """'2026-11-08 12:00:00.123' -> '2026-11-08T12:00:00.123Z'."""
    return ts.replace(" ", "T") + "Z"


def da_nuvem(valor: str) -> str:
    """ISO do servidor (qualquer fuso/fração) -> formato local em UTC com milissegundos."""
    m = _ISO.match((valor or "").strip())
    if not m:
        raise ValueError(f"Data inválida vinda da nuvem: {valor!r}")
    dia, hora, fracao, fuso = m.groups()
    t = datetime.strptime(f"{dia} {hora}", _FORMATO)
    if fuso and fuso != "Z":
        sinal = 1 if fuso[0] == "+" else -1
        digitos = fuso[1:].replace(":", "")
        desloc = timedelta(hours=int(digitos[:2]), minutes=int(digitos[2:4] or 0))
        t -= sinal * desloc
    ms = int((fracao or "0").ljust(3, "0")[:3])
    return t.strftime(_FORMATO) + f".{ms:03d}"


def _menos(ts: str, delta: timedelta) -> str:
    t = datetime.strptime(ts[:19], _FORMATO).replace(tzinfo=timezone.utc) - delta
    return t.strftime(_FORMATO) + ts[19:]


# ----------------------------------------------------------------------
def _linha_para_nuvem(reg: dict) -> dict:
    return {
        "uuid": reg["uuid"],
        "data_hora": reg["data_hora"],
        "nome": reg["nome_paciente"],
        "contato": reg["contato"] or None,
        "descricao": reg["descricao"],
        "status": reg["status"],
        "lembrete": reg["lembrete"],
        "prioridade": reg["prioridade"] or "Normal",
        "editado_em": reg["editado_em"],
        "excluido_em": reg["excluido_em"],
        "apagado": False,
        "atualizado_em": para_nuvem(reg["atualizado_em"]),
    }


def _marca_de_remocao(uuid: str, ts: str) -> dict:
    """Substitui o conteúdo na nuvem por campos vazios (some o dado pessoal)."""
    return {
        "uuid": uuid, "data_hora": "", "nome": "", "contato": None, "descricao": "",
        "status": "Atendida", "lembrete": None, "prioridade": "Normal",
        "editado_em": None, "excluido_em": None, "apagado": True,
        "atualizado_em": para_nuvem(ts),
    }


def _linha_da_nuvem(bruta: dict) -> dict:
    linha = dict(bruta)
    linha["atualizado_em"] = da_nuvem(bruta["atualizado_em"])
    return linha


# ----------------------------------------------------------------------
def testar_conexao(cliente: ClienteSupabase) -> None:
    """Confirma login e existência da tabela. Lança NuvemErro se algo falhar."""
    cliente.requisitar("GET", TABELA, {"select": "uuid", "limit": "1"})


def baixar(db: Database, cliente: ClienteSupabase, resultado: Resultado) -> None:
    cursor = db.sync_cursor()
    desde = _menos(cursor, SOBREPOSICAO) if cursor else None
    ultimo: Optional[tuple] = None   # (atualizado_em, uuid) da última linha vista
    maior = cursor

    while True:
        parametros = {"select": "*", "order": "atualizado_em.asc,uuid.asc",
                      "limit": str(PAGINA)}
        if ultimo is not None:
            ts, u = ultimo
            parametros["or"] = (f"(atualizado_em.gt.{ts},"
                                f"and(atualizado_em.eq.{ts},uuid.gt.{u}))")
        elif desde:
            parametros["atualizado_em"] = f"gte.{para_nuvem(desde)}"
        linhas = cliente.requisitar("GET", TABELA, parametros) or []

        for bruta in linhas:
            try:
                linha = _linha_da_nuvem(bruta)
                efeito = db.sync_aplicar_remoto(linha)
            except Exception:
                resultado.erros += 1
                continue
            if efeito in ("novo", "atualizado"):
                resultado.recebidos += 1
            elif efeito == "removido":
                resultado.removidos += 1
            if maior is None or linha["atualizado_em"] > maior:
                maior = linha["atualizado_em"]

        if linhas:
            ultimo = (para_nuvem(da_nuvem(linhas[-1]["atualizado_em"])), linhas[-1]["uuid"])
        if maior:
            db.sync_definir_cursor(maior)
        if len(linhas) < PAGINA:
            break


def enviar(db: Database, cliente: ClienteSupabase, resultado: Resultado) -> None:
    cabecalhos = {"Prefer": "resolution=merge-duplicates,return=minimal"}
    caminho = {"on_conflict": "uuid"}

    while True:
        lote = db.sync_pendentes(LOTE_ENVIO)
        if not lote:
            break
        cliente.requisitar("POST", TABELA, caminho,
                           [_linha_para_nuvem(r) for r in lote], cabecalhos)
        db.sync_confirmar_envio([(r["uuid"], r["atualizado_em"]) for r in lote])
        resultado.enviados += len(lote)
        if len(lote) < LOTE_ENVIO:
            break

    while True:
        lote = db.sync_remocoes(LOTE_ENVIO)
        if not lote:
            break
        cliente.requisitar("POST", TABELA, caminho,
                           [_marca_de_remocao(u, ts) for u, ts in lote], cabecalhos)
        db.sync_confirmar_remocoes(lote)
        resultado.enviados += len(lote)
        if len(lote) < LOTE_ENVIO:
            break


def sincronizar(db: Database, cliente: ClienteSupabase) -> Resultado:
    """Baixa e envia. Lança NuvemErro em caso de falha (o que já foi
    sincronizado permanece; o restante fica pendente para a próxima vez)."""
    resultado = Resultado()
    baixar(db, cliente, resultado)
    enviar(db, cliente, resultado)
    return resultado
