"""
util.py
-------
Funções auxiliares de texto, datas e cores usadas pela interface.
"""

from datetime import datetime

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
