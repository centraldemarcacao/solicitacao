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


def main(argv=None) -> None:
    _identificar_aplicativo()
    argv = sys.argv[1:] if argv is None else argv

    # Uma janela só: com "Iniciar com o Windows", é fácil abrir o programa duas vezes.
    from anotacoes.nucleo import instancia
    if not instancia.adquirir():
        _avisar_ja_aberto()
        return

    from anotacoes.interface.janela import App

    app = App(minimizado="--minimizado" in argv)
    app.mainloop()


def _avisar_ja_aberto() -> None:
    try:
        from tkinter import Tk, messagebox
        raiz = Tk()
        raiz.withdraw()
        messagebox.showinfo("Programa já aberto",
                            "O programa já está aberto neste computador "
                            "(procure-o na barra de tarefas).")
        raiz.destroy()
    except Exception:
        pass
