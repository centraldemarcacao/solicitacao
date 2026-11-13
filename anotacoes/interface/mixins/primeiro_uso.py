"""
primeiro_uso.py
---------------
Assistente de boas-vindas, mostrado uma vez em instalação nova: começar do zero, entrar pela
nuvem (já uso em outro computador) ou restaurar um backup. Regras em nucleo/primeiro_uso.py.
"""

import os

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.widgets import alinhar_esquerda, centralizar, fonte
from anotacoes.nucleo import primeiro_uso as regras


class DialogoBoasVindas(ctk.CTkToplevel):
    """`ao_escolher(opcao)`: "zero", "nuvem" ou "backup"."""

    def __init__(self, pai, pasta_dados: str, ao_escolher) -> None:
        super().__init__(pai, fg_color=T.CARD)
        self._ao_escolher = ao_escolher
        self._escolhido = False
        self.title("Bem-vindo")
        self.resizable(False, False)
        centralizar(self, pai, 540, 520)
        self.transient(pai)
        self.protocol("WM_DELETE_WINDOW", lambda: self._escolher("zero"))

        ctk.CTkFrame(self, fg_color=T.TEAL, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=32, pady=(24, 0))
        ctk.CTkLabel(corpo, text="Bem-vindo!", font=fonte(24, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w")
        alinhar_esquerda(ctk.CTkLabel(
            corpo, text="Como você quer começar?", font=fonte(14),
            text_color=T.TEXTO_SUAVE, anchor="w")).pack(anchor="w", pady=(2, 16))

        self.btn_zero = self._opcao(
            corpo, "Começar do zero", "Primeira vez neste programa.", "zero", destaque=True)
        self.btn_nuvem = self._opcao(
            corpo, "Já uso em outro computador",
            "Entre com seu e-mail e senha para trazer seus registros da nuvem.", "nuvem")
        self.btn_backup = self._opcao(
            corpo, "Restaurar um backup",
            "Escolha um arquivo de backup (.db ou .dbx), de um pendrive ou da pasta de backups.",
            "backup")
        alinhar_esquerda(ctk.CTkLabel(
            corpo, text=f"Seus dados ficam em:\n{pasta_dados}\nEssa pasta não depende de onde o "
                        "programa está: mover ou atualizar o programa não apaga nada.",
            font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=470,
        )).pack(anchor="w", pady=(14, 0))

    def _opcao(self, pai, titulo: str, detalhe: str, chave: str, destaque: bool = False):
        quadro = ctk.CTkFrame(pai, fg_color="transparent")
        quadro.pack(fill="x", pady=(0, 10))
        botao = ctk.CTkButton(
            quadro, text=titulo, height=44, font=fonte(15, "bold"),
            fg_color=T.TEAL if destaque else "transparent",
            hover_color=T.TEAL_ESCURO if destaque else T.TEAL_CLARO,
            text_color=T.SOBRE_COR if destaque else T.TEAL,
            border_width=0 if destaque else 2, border_color=T.TEAL,
            command=lambda: self._escolher(chave))
        botao.pack(fill="x")
        alinhar_esquerda(ctk.CTkLabel(
            quadro, text=detalhe, font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w",
            wraplength=470)).pack(anchor="w", pady=(3, 0))
        return botao

    def _escolher(self, opcao: str) -> None:
        if self._escolhido:
            return
        self._escolhido = True
        try:
            self.destroy()
        finally:
            self._ao_escolher(opcao)


class PrimeiroUsoMixin:
    def _iniciar_primeiro_uso(self, minimizado: bool = False) -> None:
        """Chamar depois de a interface estar pronta."""
        if self.prefs.primeiro_uso_concluido:
            return
        try:
            total = len(self.db.listar())
        except Exception:
            return
        if not regras.deve_mostrar(False, total, self.nuvem_conectada(), self.seguranca.ativa):
            self._concluir_primeiro_uso()          # instalação já em uso: nunca mostrar
            return
        if minimizado:
            return                                 # abriu com o Windows: espera uma abertura normal
        self.after(700, self._mostrar_boas_vindas)

    def _concluir_primeiro_uso(self) -> None:
        self.prefs.primeiro_uso_concluido = True
        self.prefs.salvar()

    def _mostrar_boas_vindas(self) -> None:
        if self.esta_bloqueado():
            self.after(2000, self._mostrar_boas_vindas)
            return
        DialogoBoasVindas(self, os.path.dirname(self.db.caminho), self._ao_escolher_inicio)

    def _ao_escolher_inicio(self, opcao: str) -> None:
        self._concluir_primeiro_uso()
        if opcao == "nuvem":
            self.mostrar_pagina("nuvem")
        elif opcao == "backup":
            self.mostrar_pagina("backup")
            self.restaurar_de_arquivo()
        else:
            self.mostrar_pagina("novo")
