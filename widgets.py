"""
widgets.py
----------
Componentes visuais reutilizáveis (CustomTkinter):

  - ItemNavegacao       item do menu lateral com faixa de destaque
  - CartaoNumero        cartão de indicador (título + número grande)
  - CaixaBusca          campo de busca com ícone e destaque de foco
  - Pilula              etiqueta arredondada (ex.: status)
  - Notificacao         aviso temporário (sucesso, erro, atenção)
  - DialogoConfirmacao  janela modal de confirmação (ex.: exclusão)
"""

import customtkinter as ctk

import theme as T
from icons import icone


def fonte(tamanho: int = 14, peso: str = "normal") -> ctk.CTkFont:
    """Fonte padrão do sistema (só pode ser chamada depois de criar a janela)."""
    return ctk.CTkFont(T.FONTE, tamanho, peso)


def alinhar_esquerda(rotulo):
    """Alinha à esquerda as linhas de um CTkLabel com quebra de texto.

    (O CTkLabel não aceita `justify` no construtor; ajustamos o rótulo interno.)
    """
    try:
        rotulo._label.configure(justify="left")
    except Exception:
        pass
    return rotulo


# ----------------------------------------------------------------------
# Utilidades de janela
# ----------------------------------------------------------------------
def centralizar(janela, pai, largura: int, altura: int) -> None:
    """Posiciona `janela` no centro de `pai` (considera a escala do Windows)."""
    try:
        pai.update_idletasks()
        try:
            fator = janela._get_window_scaling()
        except Exception:
            fator = 1.0
        x = pai.winfo_rootx() + (pai.winfo_width() - int(largura * fator)) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - int(altura * fator)) // 2
        janela.geometry(f"{largura}x{altura}+{max(0, x)}+{max(0, y)}")
    except Exception:
        janela.geometry(f"{largura}x{altura}")


def tornar_modal(janela, pai, foco=None) -> None:
    """Deixa a janela modal (bloqueia a principal) e fecha com Esc."""
    try:
        janela.transient(pai)
    except Exception:
        pass

    def _ativar():
        try:
            janela.grab_set()
            (foco or janela).focus_force()
        except Exception:
            pass

    janela.after(150, _ativar)
    janela.bind("<Escape>", lambda _e: janela.destroy())


# ----------------------------------------------------------------------
# Componentes
# ----------------------------------------------------------------------
class ItemNavegacao(ctk.CTkFrame):
    """Botão do menu lateral. Quando ativo, ganha fundo e uma faixa colorida."""

    def __init__(self, pai, texto: str, nome_icone: str, comando) -> None:
        super().__init__(pai, fg_color="transparent", corner_radius=0)
        self._faixa = ctk.CTkFrame(self, width=4, fg_color="transparent", corner_radius=2)
        self._faixa.pack(side="left", fill="y", pady=4)
        self._botao = ctk.CTkButton(
            self, text=texto, image=icone(nome_icone, T.NAV_TEXTO, 22),
            compound="left", anchor="w", height=48, corner_radius=10,
            border_spacing=14, fg_color="transparent", hover_color=T.NAVY_HOVER,
            text_color=T.NAV_TEXTO, font=fonte(15, "bold"), command=comando,
        )
        self._botao.pack(side="left", fill="x", expand=True, padx=(10, 14))

    def marcar(self, ativo: bool) -> None:
        self._botao.configure(
            fg_color=T.NAVY_ATIVO if ativo else "transparent",
            hover_color=T.NAVY_ATIVO if ativo else T.NAVY_HOVER,
        )
        self._faixa.configure(fg_color=T.TEAL_ACENTO if ativo else "transparent")


class CartaoNumero(ctk.CTkFrame):
    """Indicador: faixa colorida, título, número grande e ícone em círculo."""

    def __init__(self, pai, titulo: str, cor: str, tinte: str, nome_icone: str) -> None:
        super().__init__(
            pai, fg_color=T.CARD, corner_radius=14,
            border_width=1, border_color=T.BORDA,
        )
        ctk.CTkFrame(self, width=6, fg_color=cor, corner_radius=3).pack(
            side="left", fill="y", padx=(14, 0), pady=16
        )

        textos = ctk.CTkFrame(self, fg_color="transparent")
        textos.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=14)
        ctk.CTkLabel(
            textos, text=titulo, font=fonte(13, "bold"),
            text_color=T.TEXTO_SUAVE, anchor="w",
        ).pack(anchor="w")
        self._valor = ctk.CTkLabel(
            textos, text="0", font=fonte(34, "bold"),
            text_color=T.TEXTO, anchor="w",
        )
        self._valor.pack(anchor="w")

        circulo = ctk.CTkFrame(self, width=52, height=52, corner_radius=26, fg_color=tinte)
        circulo.pack(side="right", padx=(0, 18))
        circulo.pack_propagate(False)
        ctk.CTkLabel(circulo, text="", image=icone(nome_icone, cor, 26)).place(
            relx=0.5, rely=0.5, anchor="center"
        )

    def definir(self, valor: int) -> None:
        self._valor.configure(text=str(valor))


class CaixaBusca(ctk.CTkFrame):
    """Campo de busca com ícone de lupa e contorno que muda ao receber foco."""

    def __init__(self, pai, dica: str, ao_digitar, largura: int = 380) -> None:
        super().__init__(
            pai, width=largura, height=44, fg_color=T.BRANCO,
            corner_radius=10, border_width=2, border_color=T.BORDA,
        )
        self.pack_propagate(False)
        ctk.CTkLabel(self, text="", image=icone("search", T.TEXTO_SUAVE, 18)).pack(
            side="left", padx=(14, 4)
        )
        self.entry = ctk.CTkEntry(
            self, height=38, border_width=0, fg_color=T.BRANCO,
            text_color=T.TEXTO, placeholder_text=dica,
            placeholder_text_color=T.PLACEHOLDER, font=fonte(14),
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.entry.bind("<KeyRelease>", lambda _e: ao_digitar())
        self.entry.bind("<FocusIn>", lambda _e: self.configure(border_color=T.TEAL))
        self.entry.bind("<FocusOut>", lambda _e: self.configure(border_color=T.BORDA))

    def get(self) -> str:
        return self.entry.get().strip()


class Pilula(ctk.CTkFrame):
    """Etiqueta arredondada com texto (ex.: 'Pendente')."""

    def __init__(self, pai, texto: str = "", fundo: str = T.TEAL,
                 cor_texto: str = T.BRANCO, tamanho: int = 13) -> None:
        super().__init__(pai, fg_color=fundo, corner_radius=14)
        self._rotulo = ctk.CTkLabel(
            self, text=texto, text_color=cor_texto, font=fonte(tamanho, "bold")
        )
        self._rotulo.pack(padx=14, pady=3)

    def definir(self, texto: str, fundo: str, cor_texto: str) -> None:
        self.configure(fg_color=fundo)
        self._rotulo.configure(text=texto, text_color=cor_texto)


class Notificacao(ctk.CTkFrame):
    """Aviso temporário na parte inferior da área de conteúdo."""

    ESTILOS = {
        "sucesso": (T.VERDE, "check_circle"),
        "erro": (T.VERMELHO, "warning"),
        "aviso": (T.AMBAR, "warning"),
        "info": (T.TEAL, "check_circle"),
    }

    def __init__(self, pai) -> None:
        super().__init__(pai, fg_color=T.VERDE, corner_radius=12)
        self._rotulo = ctk.CTkLabel(
            self, text="", compound="left", text_color=T.BRANCO,
            font=fonte(14, "bold"),
        )
        self._rotulo.pack(padx=22, pady=13)
        self._tarefa = None

    def mostrar(self, mensagem: str, tipo: str = "sucesso", ms: int = 3500) -> None:
        cor, nome_icone = self.ESTILOS.get(tipo, self.ESTILOS["info"])
        self.configure(fg_color=cor)
        self._rotulo.configure(text="  " + mensagem, image=icone(nome_icone, T.BRANCO, 22))
        self.place(relx=0.5, rely=1.0, anchor="s", y=-28)
        self.lift()
        if self._tarefa is not None:
            self.after_cancel(self._tarefa)
        self._tarefa = self.after(ms, self._ocultar)

    def _ocultar(self) -> None:
        self.place_forget()
        self._tarefa = None


class DialogoConfirmacao(ctk.CTkToplevel):
    """Janela modal de confirmação. Use `DialogoConfirmacao.perguntar(...)`."""

    def __init__(self, pai, titulo: str, destaque: str, mensagem: str,
                 texto_confirmar: str = "Excluir") -> None:
        super().__init__(pai, fg_color=T.BRANCO)
        self.resultado = False
        self.title(titulo)
        self.resizable(False, False)
        centralizar(self, pai, 480, 300)

        ctk.CTkFrame(self, fg_color=T.VERMELHO, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=30, pady=(24, 8))

        topo = ctk.CTkFrame(corpo, fg_color="transparent")
        topo.pack(fill="x")
        circulo = ctk.CTkFrame(topo, width=56, height=56, corner_radius=28,
                               fg_color=T.VERMELHO_CLARO)
        circulo.pack(side="left")
        circulo.pack_propagate(False)
        ctk.CTkLabel(circulo, text="", image=icone("trash", T.VERMELHO, 28)).place(
            relx=0.5, rely=0.5, anchor="center"
        )
        textos = ctk.CTkFrame(topo, fg_color="transparent")
        textos.pack(side="left", padx=(16, 0), fill="x", expand=True)
        ctk.CTkLabel(
            textos, text=titulo, font=fonte(19, "bold"),
            text_color=T.TEXTO, anchor="w",
        ).pack(anchor="w")
        alinhar_esquerda(ctk.CTkLabel(
            textos, text=destaque, font=fonte(14, "bold"),
            text_color=T.VERMELHO, anchor="w", wraplength=340,
        )).pack(anchor="w")

        alinhar_esquerda(ctk.CTkLabel(
            corpo, text=mensagem, font=fonte(14), text_color=T.TEXTO_SUAVE,
            anchor="w", wraplength=410,
        )).pack(anchor="w", pady=(18, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=30, pady=(8, 24))
        ctk.CTkButton(
            botoes, text=texto_confirmar, width=130, height=42,
            font=fonte(14, "bold"), fg_color=T.VERMELHO, hover_color=T.VERMELHO_HOVER,
            command=self._confirmar,
        ).pack(side="right")
        self._cancelar_btn = ctk.CTkButton(
            botoes, text="Cancelar", width=130, height=42, font=fonte(14, "bold"),
            fg_color="transparent", text_color=T.TEXTO, border_width=2,
            border_color=T.BORDA_FORTE, hover_color=T.FUNDO, command=self.destroy,
        )
        self._cancelar_btn.pack(side="right", padx=(0, 12))

        tornar_modal(self, pai, foco=self._cancelar_btn)
        self.bind("<Return>", lambda _e: self.destroy())  # Enter = opção segura

    def _confirmar(self) -> None:
        self.resultado = True
        self.destroy()

    @classmethod
    def perguntar(cls, pai, titulo: str, destaque: str, mensagem: str,
                  texto_confirmar: str = "Excluir") -> bool:
        dialogo = cls(pai, titulo, destaque, mensagem, texto_confirmar)
        pai.wait_window(dialogo)
        return dialogo.resultado
