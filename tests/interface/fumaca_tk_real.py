"""
fumaca_tk_real.py
-------------
Teste de fumaça com o Tk REAL (sem simulação): abre a janela de verdade, percorre as
páginas, abre os diálogos e o bloqueio por PIN, e falha se qualquer callback do Tk
levantar exceção. Pensado para o runner Windows do GitHub Actions (que tem tela).

Sem tela / sem tkinter / sem customtkinter: sai com código 0 dizendo que pulou.
Usa um banco temporário: nunca toca nos dados reais.
"""

import os
import sys
import tempfile
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

try:
    import tkinter
    import customtkinter  # noqa: F401
    tkinter.Tk().destroy()
except Exception as exc:                       # sem tela ou dependência ausente
    print(f"PULADO: Tk real indisponível ({type(exc).__name__}: {exc})")
    sys.exit(0)

from anotacoes.nucleo import database  # noqa: E402

pasta = tempfile.mkdtemp(prefix="teste_real_")
database.caminho_banco = lambda: os.path.join(pasta, "teste.db")

from anotacoes.interface import janela as gui  # noqa: E402
from anotacoes.interface.mixins import pausas as pausas_gui  # noqa: E402
from anotacoes.nucleo import pausas as pausas_nucleo  # noqa: E402

ERROS = []
passos = 0


def passo(nome):
    global passos
    passos += 1
    print(f"  ok - {nome}")


def processar(app, vezes=3):
    for _ in range(vezes):
        app.update_idletasks()
        app.update()


def main() -> int:
    app = gui.App()

    def registrar(_exc, valor, tb):
        ERROS.append("".join(traceback.format_exception(type(valor), valor, tb)))
    app.report_callback_exception = registrar

    processar(app)
    passo("janela abre")

    for chave in list(app.paginas):
        app.mostrar_pagina(chave)
        processar(app)
        assert app.paginas[chave].winfo_ismapped(), f"página {chave} não apareceu"
        passo(f"página '{chave}' aparece")

    app.mostrar_pagina("config")
    app.atualizar_config()
    processar(app)
    passo("página Configurações atualiza")

    # Diálogos
    pausa = pausas_nucleo.montar_pausas()[0]
    aviso = pausas_gui.DialogoPausa(app, pausa)
    processar(app)
    aviso.destroy()
    passo("aviso de pausa abre e fecha")

    horarios = pausas_gui.DialogoHorariosPausa(
        app, True, pausas_nucleo.horarios_validos(None), lambda *a: None, False)
    processar(app)
    horarios.destroy()
    passo("janela de horários abre e fecha")

    # PIN e bloqueio
    assert app.seguranca.ativar("senha-teste-1", criptografar_backups=False)
    app.bloquear()
    processar(app)
    assert app.esta_bloqueado()
    passo("bloqueio aparece")

    app._ent_pin.insert(0, "errada")
    app._tentar_desbloquear()
    processar(app)
    assert app.esta_bloqueado(), "PIN errado desbloqueou"
    passo("PIN errado mantém bloqueado")

    app._limite_pin.acertou()
    app._ent_pin.delete(0, "end")
    app._ent_pin.insert(0, "senha-teste-1")
    app._tentar_desbloquear()
    processar(app)
    assert not app.esta_bloqueado()
    passo("PIN correto desbloqueia")

    app.seguranca.desativar()
    app.destroy()
    return 0


try:
    codigo = main()
except Exception:
    traceback.print_exc()
    codigo = 1

if ERROS:
    print("\nExceções em callbacks do Tk:")
    for e in ERROS:
        print(e)
    codigo = 1
print(f"\n{passos} passos concluídos." if codigo == 0 else "\nFALHOU.")
sys.exit(codigo)
