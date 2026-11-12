"""
instancia.py
------------
Uma única janela do programa por usuário do Windows.

Com "Iniciar com o Windows", é fácil o programa ser aberto duas vezes (uma pelo início
automático e outra pelo atalho): duas cópias repetiriam os alertas de pausa e disputariam
o banco de dados. Usa um "mutex" nomeado do Windows. Em outros sistemas, não faz nada.

Na atualização, o programa antigo chama `liberar()` antes de abrir o novo; mesmo assim,
`adquirir()` espera alguns segundos pelo mutex antes de desistir.
"""

import sys
import time

NOME_MUTEX = "Local\\AnotacoesHospitalares.UmaInstancia"
ERRO_JA_EXISTE = 183
_handle = None


def adquirir(espera_s: float = 3.0) -> bool:
    """True se esta é a única instância (ou se não foi possível verificar). False se
    já existe outra em execução depois de esperar `espera_s` segundos."""
    global _handle
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        k32.CreateMutexW.restype = wintypes.HANDLE
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        limite = time.monotonic() + max(0.0, espera_s)
        while True:
            ctypes.set_last_error(0)
            handle = k32.CreateMutexW(None, False, NOME_MUTEX)
            if handle and ctypes.get_last_error() != ERRO_JA_EXISTE:
                _handle = handle
                return True
            if handle:
                k32.CloseHandle(handle)       # não é nosso: só abrimos uma referência
            if time.monotonic() >= limite:
                return False
            time.sleep(0.25)
    except Exception:
        return True                           # na dúvida, deixa o programa abrir


def liberar() -> None:
    """Libera a trava (ex.: antes de abrir a versão nova na atualização)."""
    global _handle
    if _handle is None or sys.platform != "win32":
        _handle = None
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.CloseHandle(_handle)
    except Exception:
        pass
    _handle = None
