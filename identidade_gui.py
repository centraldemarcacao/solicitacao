"""
identidade_gui.py
-----------------
Janela "Personalizar": nome, subtítulo e logo do programa (e, a partir do logo,
o ícone da janela). Aberta pelo botão de lápis no rodapé do menu lateral.
"""

import os
from tkinter import filedialog

import customtkinter as ctk

import perfil
import theme as T
from icons import icone
from identidade import (EXTENSOES, MAX_NOME, MAX_SUBTITULO, Identidade,
                        validar_textos)
from widgets import (DialogoConfirmacao, alinhar_esquerda, centralizar, fonte,
                     tornar_modal)


class DialogoIdentidade(ctk.CTkToplevel):
    """Janela modal. Use `DialogoIdentidade.abrir(pai, identidade)`;
    devolve True se algo foi salvo."""

    def __init__(self, pai, identidade: Identidade) -> None:
        super().__init__(pai, fg_color=T.CARD)
        self.identidade = identidade
        self.resultado = False
        self._pai = pai
        self._logo_novo = None        # caminho de uma imagem escolhida, ainda não aplicada
        self._remover_logo = False
        self.title("Personalizar")
        self.resizable(False, False)
        centralizar(self, pai, 540, 560)

        ctk.CTkFrame(self, fg_color=T.TEAL, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=30, pady=(22, 0))

        ctk.CTkLabel(corpo, text="Personalizar", font=fonte(19, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w")
        alinhar_esquerda(ctk.CTkLabel(
            corpo, font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=480,
            text="Nome e logo mostrados neste computador. Cada computador tem a sua "
                 "própria identidade.")).pack(anchor="w", pady=(2, 10))

        self.ent_nome = self._campo(corpo, "Nome", "Ex.: Liga Contra o Câncer", MAX_NOME)
        self.ent_sub = self._campo(corpo, "Subtítulo (opcional)",
                                   "Ex.: Solicitações de pacientes", MAX_SUBTITULO)
        self.ent_nome.insert(0, T.NOME_INSTITUICAO)
        self.ent_sub.insert(0, T.SUBTITULO)

        ctk.CTkLabel(corpo, text="Logo e ícone da janela", font=fonte(13, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w", pady=(12, 4))
        linha = ctk.CTkFrame(corpo, fg_color="transparent")
        linha.pack(fill="x")
        self._placa = ctk.CTkFrame(linha, fg_color=T.BRANCO, corner_radius=10,
                                   width=76, height=64)
        self._placa.pack(side="left")
        self._placa.pack_propagate(False)
        self.lbl_previa = ctk.CTkLabel(self._placa, text="")
        self.lbl_previa.place(relx=0.5, rely=0.5, anchor="center")
        botoes = ctk.CTkFrame(linha, fg_color="transparent")
        botoes.pack(side="left", padx=(14, 0))
        ctk.CTkButton(
            botoes, text="Escolher imagem...", width=170, height=36, corner_radius=10,
            font=fonte(13, "bold"), fg_color=T.TEAL, hover_color=T.TEAL_ESCURO,
            text_color=T.SOBRE_COR, command=self._escolher_imagem,
        ).pack(anchor="w")
        ctk.CTkButton(
            botoes, text="Usar logo padrão", width=170, height=32, corner_radius=10,
            font=fonte(12, "bold"), fg_color="transparent", text_color=T.TEXTO,
            border_width=1, border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
            command=self._usar_logo_padrao,
        ).pack(anchor="w", pady=(6, 0))
        alinhar_esquerda(ctk.CTkLabel(
            corpo, font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=480,
            text="Aceita PNG, JPG, BMP, GIF, WEBP ou ICO (até 10 MB). O ícone da janela e da "
                 "barra de tarefas é gerado a partir dessa imagem. O ícone do arquivo .exe "
                 "no Explorer não muda.")).pack(anchor="w", pady=(8, 0))

        self.lbl_erro = ctk.CTkLabel(corpo, text="", font=fonte(13, "bold"),
                                     text_color=T.VERMELHO, anchor="w", wraplength=480)
        self.lbl_erro.pack(anchor="w", pady=(10, 0))

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", padx=30, pady=(8, 22))
        ctk.CTkButton(
            rodape, text="Salvar", width=120, height=42, font=fonte(14, "bold"),
            fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
            command=self._salvar,
        ).pack(side="right")
        self._btn_cancelar = ctk.CTkButton(
            rodape, text="Cancelar", width=110, height=42, font=fonte(14, "bold"),
            fg_color="transparent", text_color=T.TEXTO, border_width=2,
            border_color=T.BORDA_FORTE, hover_color=T.FUNDO, command=self.destroy,
        )
        self._btn_cancelar.pack(side="right", padx=(0, 10))
        ctk.CTkButton(
            rodape, text="Restaurar padrão", width=150, height=42, font=fonte(13, "bold"),
            fg_color="transparent", text_color=T.VERMELHO, border_width=2,
            border_color=T.VERMELHO, hover_color=T.VERMELHO_CLARO,
            command=self._restaurar_padrao,
        ).pack(side="left")

        self.ent_nome.bind("<Return>", lambda _e: self._salvar())
        self.ent_sub.bind("<Return>", lambda _e: self._salvar())
        self._mostrar_previa(self.identidade.caminho_logo())
        tornar_modal(self, pai, foco=self.ent_nome)

    # ------------------------------------------------------------------
    def _campo(self, pai, rotulo: str, dica: str, limite: int):
        ctk.CTkLabel(pai, text=rotulo, font=fonte(13, "bold"), text_color=T.TEXTO,
                     anchor="w").pack(anchor="w", pady=(8, 3))
        entrada = ctk.CTkEntry(
            pai, height=40, font=fonte(14), placeholder_text=dica, fg_color=T.SUPERFICIE,
            border_color=T.BORDA_FORTE, text_color=T.TEXTO,
            placeholder_text_color=T.TEXTO_SUAVE)
        entrada.pack(fill="x")
        return entrada

    def _mostrar_previa(self, caminho) -> None:
        """Mostra a imagem na placa branca (ou o texto 'padrão' se não houver)."""
        self.lbl_previa.configure(image=None, text="")
        if not caminho:
            self.lbl_previa.configure(image=icone("logo", T.TEAL, 40))
            return
        try:
            from PIL import Image

            with Image.open(caminho) as img:
                img = img.convert("RGBA")
            altura = 44
            largura = max(1, min(64, int(img.width * altura / img.height)))
            self.lbl_previa.configure(
                image=ctk.CTkImage(light_image=img, size=(largura, altura)))
        except Exception:
            self.lbl_previa.configure(text="?", text_color=T.TEXTO_SUAVE)

    def _escolher_imagem(self) -> None:
        caminho = filedialog.askopenfilename(
            parent=self, title="Escolher imagem do logo",
            filetypes=[("Imagens", " ".join("*" + e for e in EXTENSOES)),
                       ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        if not os.path.isfile(caminho):
            self.lbl_erro.configure(text="Arquivo não encontrado.")
            return
        self._logo_novo = caminho
        self._remover_logo = False
        self.lbl_erro.configure(text="")
        self._mostrar_previa(caminho)

    def _usar_logo_padrao(self) -> None:
        self._logo_novo = None
        self._remover_logo = True
        self.lbl_erro.configure(text="")
        self._mostrar_previa(None)

    def _salvar(self) -> None:
        try:
            nome, subtitulo = validar_textos(self.ent_nome.get(), self.ent_sub.get())
            if self._logo_novo:
                self.identidade.definir_logo(self._logo_novo)
            elif self._remover_logo:
                self.identidade.remover_logo()
            self.identidade.salvar_textos(nome, subtitulo)
        except ValueError as exc:
            self.lbl_erro.configure(text=str(exc))
            return
        except OSError as exc:
            self.lbl_erro.configure(text=f"Não foi possível salvar: {exc}")
            return
        T.NOME_INSTITUICAO, T.SUBTITULO = nome, subtitulo
        self.resultado = True
        self.destroy()

    def _restaurar_padrao(self) -> None:
        if not DialogoConfirmacao.perguntar(
                self, "Restaurar o padrão?", "Nome, subtítulo e logo",
                "O programa volta ao nome e ao logo originais. Seus registros não são alterados.",
                "Restaurar", nome_icone="warning"):
            return
        try:
            self.identidade.restaurar_padrao()
        except OSError as exc:
            self.lbl_erro.configure(text=f"Não foi possível restaurar: {exc}")
            return
        self.resultado = True
        self.destroy()

    @classmethod
    def abrir(cls, pai, identidade: Identidade) -> bool:
        dialogo = cls(pai, identidade)
        pai.wait_window(dialogo)
        return dialogo.resultado


class IdentidadeMixin:
    """Requer: self._identidade, self.toast, self.title, self._marca,
    self._montar_marca, self._aplicar_icone_janela."""

    def personalizar_identidade(self) -> None:
        if DialogoIdentidade.abrir(self, self._identidade):
            self._atualizar_identidade()
            self.toast.mostrar("Identidade atualizada.", "sucesso", 3500)

    def _atualizar_identidade(self) -> None:
        """Reflete nome, subtítulo, logo e ícone novos sem reiniciar."""
        self.title(perfil.titulo_completo())
        if self._marca is not None:
            self._marca.destroy()
        self._montar_marca(self.barra_lateral)
        self._aplicar_icone_janela()
