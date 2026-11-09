"""
app.py
------
Inicialização do programa. Use `python main.py` (ou `python -m anotacoes`).
"""

import sys


def _identificar_aplicativo() -> None:
    """No Windows, agrupa a janela com o ícone correto na barra de tarefas."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "ligacontraocancer.solicitacoes"
        )
    except Exception:
        pass


def main() -> None:
    _identificar_aplicativo()
    from anotacoes.interface.janela import App

    app = App()
    app.mainloop()
