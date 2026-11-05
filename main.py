"""
main.py
-------
Ponto de entrada do sistema de registro de solicitações.

Executar em desenvolvimento:   python main.py
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
    from gui import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
