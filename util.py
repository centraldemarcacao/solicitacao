"""
util.py
-------
Funções auxiliares de texto, datas e cores usadas pela interface.
"""

import re
from datetime import date, datetime, timedelta

import theme as T
from database import FORMATO_DATA, STATUS_ATENDIDA


def plural(n: int, singular: str, plural_: str) -> str:
    """plural(1, 'registro', 'registros') -> '1 registro'."""
    return f"{n} {singular if n == 1 else plural_}"


def formatar_data(valor) -> str:
    """'2026-11-04 18:45:00' -> '04/11/2026 18:45'."""
    try:
        return datetime.strptime(valor, FORMATO_DATA).strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return valor or ""


def data_curta(valor) -> str:
    """'2026-11-04 18:45:00' -> '04/11 18:45'."""
    try:
        return datetime.strptime(valor, FORMATO_DATA).strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return valor or ""


def resumir(texto: str, limite: int) -> str:
    """Junta quebras de linha e corta com reticências."""
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def formatar_tamanho(n_bytes: int) -> str:
    """2048 -> '2 KB'; 1_500_000 -> '1,4 MB'."""
    if n_bytes < 1024:
        return f"{n_bytes} B"
    if n_bytes < 1024 * 1024:
        return f"{n_bytes / 1024:.0f} KB"
    return f"{n_bytes / (1024 * 1024):.1f}".replace(".", ",") + " MB"


def cores_status(status: str):
    """(fundo, texto) da etiqueta de status."""
    if status == STATUS_ATENDIDA:
        return T.VERDE_CLARO, T.VERDE
    return T.AMBAR_CLARO, T.AMBAR


# ----------------------------------------------------------------------
# Datas de retorno (lembrete)
# ----------------------------------------------------------------------
def interpretar_data(texto: str, hoje: "date | None" = None,
                     permitir_passado: bool = False) -> "str | None":
    """Converte 'dd/mm/aaaa' (ou 'dd/mm/aa' ou 'dd/mm') em 'AAAA-MM-DD'.

    Vazio -> None (sem retorno). 'dd/mm' sem ano usa o ano atual, ou o próximo se
    o dia já passou. Lança ValueError com mensagem para o usuário.
    """
    texto = (texto or "").strip()
    if not texto:
        return None
    hoje = hoje or date.today()
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2}|\d{4}))?", texto)
    if not m:
        raise ValueError("Data inválida. Use o formato dd/mm/aaaa.")
    dia, mes, ano = int(m.group(1)), int(m.group(2)), m.group(3)
    try:
        if ano is None:
            alvo = date(hoje.year, mes, dia)
            if alvo < hoje:
                alvo = date(hoje.year + 1, mes, dia)
        else:
            alvo = date(2000 + int(ano) if len(ano) == 2 else int(ano), mes, dia)
    except ValueError:
        raise ValueError("Essa data não existe. Confira dia e mês.")
    if alvo < hoje and not permitir_passado:
        raise ValueError("A data de retorno já passou.")
    return alvo.isoformat()


def formatar_lembrete(iso: "str | None") -> str:
    """'2026-11-09' -> '09/11/2026' (vazio se não houver)."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return ""


def situacao_retorno(iso: "str | None", status: str, hoje: "date | None" = None) -> str:
    """'atrasado', 'hoje', 'futuro' ou '' (sem retorno ou já atendida)."""
    if not iso or status == STATUS_ATENDIDA:
        return ""
    hoje = (hoje or date.today()).isoformat()
    return "atrasado" if iso < hoje else "hoje" if iso == hoje else "futuro"


def rotulo_retorno(iso: "str | None", status: str, hoje: "date | None" = None) -> str:
    """Texto curto para a coluna 'Retorno' da tabela."""
    if not iso:
        return ""
    hoje = hoje or date.today()
    situacao = situacao_retorno(iso, status, hoje)
    if situacao == "atrasado":
        return "Atrasado " + formatar_lembrete(iso)[:5]
    if situacao == "hoje":
        return "Hoje"
    if situacao == "futuro" and iso == (hoje + timedelta(days=1)).isoformat():
        return "Amanhã"
    return formatar_lembrete(iso)


def inicio_do_periodo(nome: str, hoje: "date | None" = None) -> "str | None":
    """'Hoje', 'Últimos 7 dias', 'Este mês' -> data inicial ISO ('Todo o período' -> None)."""
    hoje = hoje or date.today()
    if nome == "Hoje":
        return hoje.isoformat()
    if nome == "Últimos 7 dias":
        return (hoje - timedelta(days=6)).isoformat()
    if nome == "Este mês":
        return hoje.replace(day=1).isoformat()
    return None
