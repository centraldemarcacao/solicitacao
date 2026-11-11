"""
atalhos.py
----------
Atalhos de teclado e "Desfazer" (Ctrl+Z).

Desfaz as últimas ações: mudar status, excluir (envia à lixeira) e editar.
Não desfaz: criar registro (basta excluí-lo) e apagar definitivamente.
"""

import tkinter as tk

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.widgets import centralizar, fonte, tornar_modal

LIMITE_DESFAZER = 20

ATALHOS = (
    ("Ctrl + N", "Novo registro"),
    ("Ctrl + S", "Salvar o registro do formulário"),
    ("Ctrl + F", "Buscar no histórico"),
    ("Ctrl + E", "Exportar a lista para Excel (CSV)"),
    ("Ctrl + P", "Imprimir a lista"),
    ("Ctrl + Z", "Desfazer a última ação (status, exclusão ou edição)"),
    ("Ctrl + T", "Alternar entre tema claro e escuro"),
    ("Ctrl + L", "Ligar ou desligar os alertas de pausa (14:40, 17:00 e 18:10)"),
    ("F2", "Editar o registro selecionado"),
    ("Enter / duplo clique", "Abrir os detalhes do registro"),
    ("Delete", "Excluir (enviar para a lixeira)"),
    ("F1", "Mostrar esta lista"),
)


class AtalhosMixin:
    """Requer: self.mostrar_pagina, self.ent_contato, self.busca, self.toast, self.db,
    self.atualizar_tudo, self.exportar_csv, self.imprimir_lista, self.alternar_tema,
    self.alternar_alertas_pausa."""

    def _iniciar_atalhos(self) -> None:
        self._pilha_desfazer = []
        for tecla, acao in (
            ("n", self._atalho_novo), ("f", self._atalho_buscar),
            ("e", self._atalho_exportar), ("p", self._atalho_imprimir),
            ("z", self._atalho_desfazer), ("t", lambda: self.alternar_tema()),
            ("l", lambda: self.alternar_alertas_pausa()),
            ("s", self._atalho_salvar),
        ):
            for variante in (tecla, tecla.upper()):
                self.bind(f"<Control-{variante}>", lambda _e, a=acao: (a(), "break")[1])
        self.bind("<F1>", lambda _e: self.mostrar_atalhos())

    # --- Navegação por teclado -------------------------------------------
    def _atalho_novo(self) -> None:
        self.mostrar_pagina("novo")
        self.ent_contato.focus_set()

    def _atalho_buscar(self) -> None:
        self.mostrar_pagina("historico")
        self.busca.entry.focus_set()

    def _atalho_exportar(self) -> None:
        self.mostrar_pagina("historico")
        self.exportar_csv()

    def _atalho_imprimir(self) -> None:
        self.mostrar_pagina("historico")
        self.imprimir_lista()

    def _atalho_desfazer(self) -> None:
        # Dentro de um campo de texto, Ctrl+Z continua desfazendo a digitação.
        foco = self.focus_get()
        if isinstance(foco, (tk.Entry, tk.Text)):
            return
        self.desfazer()

    # --- Desfazer ---------------------------------------------------------
    def registrar_desfazer(self, tipo: str, dados, descricao: str) -> None:
        self._pilha_desfazer.append((tipo, dados, descricao))
        del self._pilha_desfazer[:-LIMITE_DESFAZER]

    def desfazer(self) -> bool:
        if not self._pilha_desfazer:
            self.toast.mostrar("Não há nada para desfazer.", "aviso")
            return False
        tipo, dados, descricao = self._pilha_desfazer.pop()
        try:
            if tipo == "status":
                for rid, status in dados.items():
                    self.db.atualizar_status(rid, status)
            elif tipo == "excluir":
                self.db.restaurar(dados)
            elif tipo == "edicao":
                self.db.atualizar(
                    dados["id"], dados["nome"], dados["contato"], dados["descricao"],
                    dados["lembrete"], dados["prioridade"])
        except Exception as exc:
            self.toast.mostrar(f"Não foi possível desfazer: {exc}", "erro", 6000)
            return False
        self.atualizar_tudo()
        self.toast.mostrar(f"Desfeito: {descricao}.", "info")
        return True

    # --- Janela de ajuda ----------------------------------------------------
    def mostrar_atalhos(self) -> None:
        janela = ctk.CTkToplevel(self, fg_color=T.CARD)
        janela.title("Atalhos de teclado")
        janela.resizable(False, False)
        centralizar(janela, self, 560, 120 + 36 * len(ATALHOS))
        ctk.CTkLabel(janela, text="Atalhos de teclado", font=fonte(20, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w", padx=28, pady=(24, 12))
        grade = ctk.CTkFrame(janela, fg_color="transparent")
        grade.pack(fill="x", padx=28)
        for linha, (tecla, texto) in enumerate(ATALHOS):
            ctk.CTkLabel(grade, text=tecla, font=fonte(13, "bold"), text_color=T.TEAL,
                         anchor="w", width=170).grid(row=linha, column=0, sticky="w", pady=4)
            ctk.CTkLabel(grade, text=texto, font=fonte(14), text_color=T.TEXTO,
                         anchor="w").grid(row=linha, column=1, sticky="w", pady=4)
        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(side="bottom", fill="x", padx=28, pady=(0, 20))
        ctk.CTkButton(
            botoes, text="Fechar", width=110, height=40, corner_radius=10,
            font=fonte(14, "bold"), fg_color="transparent", text_color=T.TEXTO,
            border_width=2, border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
            command=janela.destroy,
        ).pack(side="right")
        tornar_modal(janela, self)
