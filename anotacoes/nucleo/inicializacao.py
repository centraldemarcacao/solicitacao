"""
inicializacao.py
----------------
"Iniciar com o Windows": o programa abre sozinho, minimizado, ao ligar o computador
(necessário para os alertas de pausa funcionarem sem abrir o programa à mão).

Grava um valor em HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
(só do usuário atual, não exige administrador). Só vale para o .exe; em desenvolvimento
(python main.py) fica indisponível.
"""

import os
import sys
from typing import Optional

CHAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOME_VALOR = "AnotacoesHospitalares"
ARGUMENTO_MINIMIZADO = "--minimizado"


def _winreg():
    """O módulo winreg (só no Windows). Separado para os testes poderem trocá-lo."""
    if sys.platform != "win32":
        return None
    import winreg
    return winreg


def suportado() -> bool:
    return _winreg() is not None and bool(getattr(sys, "frozen", False))


def comando() -> str:
    """Linha gravada no registro: o .exe entre aspas + argumento de início minimizado."""
    return f'"{os.path.abspath(sys.executable)}" {ARGUMENTO_MINIMIZADO}'


def _ler(wr) -> Optional[str]:
    try:
        with wr.OpenKey(wr.HKEY_CURRENT_USER, CHAVE_RUN, 0, wr.KEY_READ) as chave:
            valor, _tipo = wr.QueryValueEx(chave, NOME_VALOR)
            return valor if isinstance(valor, str) else None
    except OSError:
        return None


def ativo() -> bool:
    """True se há a entrada de início automático (de qualquer pasta deste programa)."""
    wr = _winreg()
    return bool(wr and _ler(wr))


def ativar() -> None:
    """Liga o início automático. Levanta OSError se o Windows recusar."""
    wr = _winreg()
    if wr is None or not suportado():
        raise OSError("O início com o Windows só funciona no programa instalado (.exe).")
    with wr.CreateKeyEx(wr.HKEY_CURRENT_USER, CHAVE_RUN, 0, wr.KEY_SET_VALUE) as chave:
        wr.SetValueEx(chave, NOME_VALOR, 0, wr.REG_SZ, comando())


def desativar() -> None:
    wr = _winreg()
    if wr is None:
        return
    try:
        with wr.OpenKey(wr.HKEY_CURRENT_USER, CHAVE_RUN, 0, wr.KEY_SET_VALUE) as chave:
            wr.DeleteValue(chave, NOME_VALOR)
    except FileNotFoundError:
        pass                                  # já estava desligado


def corrigir_caminho() -> None:
    """Se o início automático está ligado mas aponta para outro lugar (o .exe foi movido
    ou renomeado), atualiza para o caminho atual. Falhas são ignoradas."""
    try:
        wr = _winreg()
        if wr is None or not suportado():
            return
        atual = _ler(wr)
        if atual and atual != comando():
            ativar()
    except Exception:
        pass
