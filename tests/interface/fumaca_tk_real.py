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

# No Windows o console usa cp1252 e não imprime caracteres como "▲": força UTF-8 na saída.
for _fluxo in (sys.stdout, sys.stderr):
    try:
        _fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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

    # Novo registro: com a janela no menor tamanho permitido, a caixa da descrição continua visível
    app.mostrar_pagina("novo")
    processar(app)
    mw, mh = app.wm_minsize()
    app.geometry(f"{mw}x{mh}")
    processar(app)
    assert app.txt_desc.winfo_height() >= 60, f"caixa da descrição sumiu ({app.txt_desc.winfo_height()} px)"
    assert app.txt_desc.winfo_ismapped()
    passo("Novo registro: descrição visível na menor janela")

    # Painel: aba de administração com dados de mentira (sem rede)
    from anotacoes.nuvem import painel as _pn
    app.mostrar_pagina("painel")
    app._painel_papel = _pn.PAPEL_ADMIN
    app._aplicar_papel()
    app._preencher_admin(
        [_pn.UsuarioPainel("u1", "eu@x.com", "admin", True, "-", "-", 3, 1, 2, 0, "-"),
         _pn.UsuarioPainel("u2", "ana@x.com", "usuario", False, "-", "-", 0, 0, 0, 0, "-")],
        [_pn.AcaoAuditoria("-", "eu@x.com", "ativar_acesso", "ana@x.com", "")])
    app._trocar_aba_painel("Administração")
    processar(app)
    assert app._aba_admin.winfo_ismapped(), "aba Administração não apareceu"
    app.tabela_painel.tree.selection_set("u2")
    processar(app)
    assert app.btn_painel_acesso.cget("text") == "Ativar acesso"
    passo("painel: aba Administração e seleção de conta")
    from anotacoes.interface.widgets import DialogoNovoUsuario
    dlg = DialogoNovoUsuario(app, app._validar_novo_usuario, lambda: "GeradaForte99")
    processar(app)
    dlg._gerar_senha()
    dlg.ent_email.insert(0, "ana@x.com")
    dlg._confirmar()
    processar(app)
    assert dlg.resultado and dlg.resultado["senha"] == "GeradaForte99"
    passo("painel: janela Novo usuário")
    app._painel_papel = None
    app._aplicar_papel()
    app.mostrar_pagina("novo")

    for atalho, aba in (("backup", "_aba_backup"), ("nuvem", "_aba_nuvem")):
        app.mostrar_pagina(atalho)
        processar(app)
        assert getattr(app, aba).winfo_ismapped(), f"aba {atalho} em Configurações não apareceu"
        passo(f"Configurações > aba '{atalho}' aparece")

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

    # Menus suspensos (clique direito e Exportar) com o Tk real
    from anotacoes.interface.widgets import MenuPopup
    app.db.inserir("Paciente Teste", "1234", "Solicita água.")
    app.atualizar_tudo()
    app.mostrar_pagina("historico")
    processar(app)
    arvore = app.tabela.tree
    iid = arvore.get_children()[0]
    arvore.selection_set(iid)
    x0, y0 = arvore.winfo_rootx() + 40, arvore.winfo_rooty() + 40
    menu = MenuPopup.abrir(app, x0, y0, app._itens_menu_contexto(),
                           titulo="1 registro selecionado")
    processar(app, 5)
    assert menu.winfo_exists() and menu.winfo_ismapped(), "menu de contexto não apareceu"
    assert menu.winfo_width() > 150 and menu.winfo_height() > 100, "menu de contexto sem tamanho"
    menu._destacar(0)
    menu._mover(1)
    processar(app)
    assert menu._atual == 1
    passo("menu de contexto abre, destaca e navega")
    menu._fechar()
    processar(app)
    assert not menu.winfo_exists(), "menu de contexto não fechou"
    passo("menu de contexto fecha")

    app._abrir_menu_exportar()
    processar(app, 5)
    menu = app._menu_popup
    assert menu is not None and menu.winfo_ismapped(), "menu Exportar não apareceu"
    for tecla in ("<Escape>", "<Up>", "<Down>", "<Return>"):
        assert menu.bind(tecla), f"menu sem atalho de teclado {tecla}"   # o foco real depende do Windows
    menu._fechar()
    processar(app, 5)
    assert app._menu_popup is None and not menu.winfo_exists(), "menu Exportar não fechou"
    passo("menu Exportar abre, tem teclado e fecha")

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
