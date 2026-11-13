"""
modelos.py
----------
Modelos de descrição no formulário "Novo registro": botões com frases prontas e a janela
para editá-los. Regras em nucleo/modelos.py.

Requer em App: self.prefs, self.txt_desc, self.toast, self._texto, self._atualizar_contador,
self._frm_modelos (criado em _montar_formulario).
"""

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.widgets import alinhar_esquerda, centralizar, fonte
from anotacoes.nucleo import modelos as regras
from anotacoes.nucleo.database import MAX_DESCRICAO

POR_LINHA = 4


class DialogoModelos(ctk.CTkToplevel):
    """Editar, adicionar e remover modelos. `ao_salvar(lista)`."""

    def __init__(self, pai, modelos: list, ao_salvar) -> None:
        super().__init__(pai, fg_color=T.CARD)
        self._ao_salvar = ao_salvar
        self.title("Modelos de descrição")
        self.resizable(False, False)
        centralizar(self, pai, 640, 620)
        self.transient(pai)

        ctk.CTkFrame(self, fg_color=T.TEAL, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=28, pady=(20, 0))
        ctk.CTkLabel(corpo, text="Modelos de descrição", font=fonte(19, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w")
        alinhar_esquerda(ctk.CTkLabel(
            corpo, text=f"Frases prontas para os pedidos mais comuns (até {regras.MAX_MODELOS}). "
                        "Aparecem como botões no formulário.",
            font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=570,
        )).pack(anchor="w", pady=(4, 10))

        self._quadro = ctk.CTkFrame(corpo, fg_color="transparent")
        self._quadro.pack(fill="x")
        self._linhas = []
        for m in modelos:
            self._nova_linha(m["titulo"], m["texto"])

        self.btn_novo = ctk.CTkButton(
            corpo, text="+ Adicionar modelo", height=34, width=170, font=fonte(13, "bold"),
            fg_color="transparent", text_color=T.TEAL, border_width=2, border_color=T.TEAL,
            hover_color=T.TEAL_CLARO, command=self._adicionar)
        self.btn_novo.pack(anchor="w", pady=(10, 0))
        self.lbl_erro = ctk.CTkLabel(corpo, text="", font=fonte(13, "bold"),
                                     text_color=T.VERMELHO, anchor="w", wraplength=570)
        self.lbl_erro.pack(anchor="w", pady=(8, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=28, pady=(8, 22), side="bottom")
        ctk.CTkButton(botoes, text="Salvar", width=110, height=42, font=fonte(14, "bold"),
                      fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
                      command=self._salvar).pack(side="right")
        ctk.CTkButton(botoes, text="Cancelar", width=110, height=42, font=fonte(14, "bold"),
                      fg_color="transparent", text_color=T.TEXTO, border_width=2,
                      border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
                      command=self.destroy).pack(side="right", padx=(0, 10))
        ctk.CTkButton(botoes, text="Restaurar padrão", width=140, height=42, font=fonte(13, "bold"),
                      fg_color="transparent", text_color=T.TEXTO_SUAVE, hover_color=T.FUNDO,
                      command=self._restaurar).pack(side="left")
        self.bind("<Escape>", lambda _e: self.destroy())
        self._atualizar_botao_novo()

    # --- linhas ---------------------------------------------------------
    def _nova_linha(self, titulo: str = "", texto: str = "") -> None:
        linha = ctk.CTkFrame(self._quadro, fg_color="transparent")
        linha.pack(fill="x", pady=3)
        ent_t = ctk.CTkEntry(linha, width=150, height=38, font=fonte(14), fg_color=T.SUPERFICIE,
                             border_color=T.BORDA_FORTE, text_color=T.TEXTO,
                             placeholder_text="Título", placeholder_text_color=T.PLACEHOLDER)
        ent_t.pack(side="left")
        ent_x = ctk.CTkEntry(linha, height=38, font=fonte(14), fg_color=T.SUPERFICIE,
                             border_color=T.BORDA_FORTE, text_color=T.TEXTO,
                             placeholder_text="Texto que será inserido",
                             placeholder_text_color=T.PLACEHOLDER)
        ent_x.pack(side="left", fill="x", expand=True, padx=8)
        botao = ctk.CTkButton(linha, text="×", width=38, height=38, font=fonte(16, "bold"),
                              fg_color="transparent", text_color=T.VERMELHO,
                              border_width=2, border_color=T.BORDA_FORTE, hover_color=T.FUNDO)
        botao.pack(side="right")
        if titulo:
            ent_t.insert(0, titulo)
        if texto:
            ent_x.insert(0, texto)
        item = (linha, ent_t, ent_x)
        botao.configure(command=lambda i=item: self._remover(i))
        self._linhas.append(item)

    def _valores(self) -> list:
        return [{"titulo": t.get(), "texto": x.get()} for _l, t, x in self._linhas]

    def _recriar(self, modelos: list) -> None:
        for linha, _t, _x in self._linhas:
            linha.destroy()
        self._linhas = []
        for m in modelos:
            self._nova_linha(m["titulo"], m["texto"])
        self._atualizar_botao_novo()

    def _atualizar_botao_novo(self) -> None:
        self.btn_novo.configure(
            state="normal" if len(self._linhas) < regras.MAX_MODELOS else "disabled")

    def _adicionar(self) -> None:
        if len(self._linhas) < regras.MAX_MODELOS:
            self._nova_linha()
            self._atualizar_botao_novo()

    def _remover(self, item) -> None:
        if item in self._linhas:
            self._linhas.remove(item)
            item[0].destroy()
            self._atualizar_botao_novo()

    def _restaurar(self) -> None:
        self._recriar(regras.padrao())
        self.lbl_erro.configure(text="")

    def _salvar(self) -> None:
        brutos = self._valores()
        preenchidos = [m for m in brutos if m["titulo"].strip() or m["texto"].strip()]
        for m in preenchidos:
            if not m["titulo"].strip() or not m["texto"].strip():
                self.lbl_erro.configure(text="Preencha o título e o texto de cada modelo "
                                             "(ou remova a linha).")
                return
        validos = regras.validar_modelos(preenchidos)
        if len(validos) < len(preenchidos):
            self.lbl_erro.configure(text="Há títulos repetidos. Use um título diferente em cada modelo.")
            return
        self._ao_salvar(validos)
        self.destroy()


class ModelosMixin:
    def _montar_modelos(self) -> None:
        """(Re)cria os botões de modelo dentro de self._frm_modelos."""
        for filho in self._frm_modelos.winfo_children():
            filho.destroy()
        modelos = self.prefs.modelos_descricao
        ctk.CTkLabel(self._frm_modelos, text="Modelos:", font=fonte(12, "bold"),
                     text_color=T.TEXTO_SUAVE).pack(anchor="w")
        for inicio in range(0, len(modelos), POR_LINHA):
            linha = ctk.CTkFrame(self._frm_modelos, fg_color="transparent")
            linha.pack(fill="x", pady=(3, 0))
            for m in modelos[inicio:inicio + POR_LINHA]:
                ctk.CTkButton(
                    linha, text=m["titulo"], height=30, corner_radius=15, font=fonte(12, "bold"),
                    fg_color=T.TEAL_CLARO, text_color=T.TEAL_ESCURO, hover_color=T.BORDA,
                    command=lambda t=m["texto"]: self._usar_modelo(t),
                ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            self._frm_modelos, text="Editar modelos", height=26, width=120, font=fonte(12),
            fg_color="transparent", text_color=T.TEXTO_SUAVE, hover_color=T.FUNDO,
            command=self.gerenciar_modelos).pack(anchor="w", pady=(2, 0))

    def _usar_modelo(self, texto: str) -> None:
        novo = regras.texto_com_modelo(self._texto(self.txt_desc), texto, MAX_DESCRICAO)
        if novo is None:
            self.toast.mostrar(f"O texto passaria de {MAX_DESCRICAO} caracteres.", "aviso")
            return
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", novo)
        self._atualizar_contador()
        try:
            self.txt_desc.focus_set()
        except Exception:
            pass

    def gerenciar_modelos(self) -> None:
        DialogoModelos(self, self.prefs.modelos_descricao, self._salvar_modelos)

    def _salvar_modelos(self, modelos: list) -> None:
        self.prefs.modelos_descricao = modelos
        if not self.prefs.salvar():
            self.toast.mostrar("Não foi possível gravar os modelos (pasta sem permissão?).",
                               "erro", 6000)
        self._montar_modelos()
        self.toast.mostrar("Modelos salvos.", "sucesso", 2500)
