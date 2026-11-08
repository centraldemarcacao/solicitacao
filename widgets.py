"""
widgets.py
----------
Componentes visuais reutilizáveis (CustomTkinter):

  - ItemNavegacao       item do menu lateral com faixa de destaque
  - CartaoNumero        cartão de indicador (título + número grande)
  - CaixaBusca          campo de busca com ícone e destaque de foco
  - Pilula              etiqueta arredondada (ex.: status)
  - Notificacao         aviso temporário (sucesso, erro, atenção)
  - TabelaRegistros     tabela com cores por linha e seleção suave
  - DialogoConfirmacao  janela modal de confirmação (ex.: exclusão)
"""

from tkinter import ttk

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
            self, text=texto, image=icone(nome_icone, T.NAV_TEXTO, 20),
            compound="left", anchor="w", height=42, corner_radius=10,
            border_spacing=12, fg_color="transparent", hover_color=T.NAVY_HOVER,
            text_color=T.NAV_TEXTO, font=fonte(14, "bold"), command=comando,
        )
        self._botao.pack(side="left", fill="x", expand=True, padx=(10, 14))

    def definir_texto(self, texto: str) -> None:
        self._botao.configure(text=texto)

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
            pai, width=largura, height=44, fg_color=T.SUPERFICIE,
            corner_radius=10, border_width=2, border_color=T.BORDA,
        )
        self.pack_propagate(False)
        ctk.CTkLabel(self, text="", image=icone("search", T.TEXTO_SUAVE, 18)).pack(
            side="left", padx=(14, 4)
        )
        self.entry = ctk.CTkEntry(
            self, height=38, border_width=0, fg_color=T.SUPERFICIE,
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

    # tipo -> (nome da cor no tema, ícone); a cor é lida na hora de mostrar
    ESTILOS = {
        "sucesso": ("VERDE", "check_circle"),
        "erro": ("VERMELHO", "warning"),
        "aviso": ("AMBAR", "warning"),
        "info": ("TEAL", "check_circle"),
    }

    def __init__(self, pai) -> None:
        super().__init__(pai, fg_color=T.VERDE, corner_radius=12)
        self._rotulo = ctk.CTkLabel(
            self, text="", compound="left", text_color=T.SOBRE_COR,
            font=fonte(14, "bold"),
        )
        self._rotulo.pack(padx=22, pady=13)
        self._tarefa = None

    def mostrar(self, mensagem: str, tipo: str = "sucesso", ms: int = 3500) -> None:
        nome_cor, nome_icone = self.ESTILOS.get(tipo, self.ESTILOS["info"])
        self.configure(fg_color=getattr(T, nome_cor))
        self._rotulo.configure(text="  " + mensagem, image=icone(nome_icone, T.SOBRE_COR, 22))
        self.place(relx=0.5, rely=1.0, anchor="s", y=-28)
        self.lift()
        if self._tarefa is not None:
            self.after_cancel(self._tarefa)
        self._tarefa = self.after(ms, self._ocultar)

    def _ocultar(self) -> None:
        self.place_forget()
        self._tarefa = None


class TabelaRegistros(ctk.CTkFrame):
    """Tabela (ttk.Treeview) com cores por linha e seleção suave.

    Cada linha tem UMA só etiqueta de cor: a "base" (ex.: pendente, atendida,
    neutra) ou "selecionada". Assim a cor não depende de como cada versão do
    Tk resolve conflitos entre a cor da etiqueta e a cor de seleção do estilo.

    colunas: lista de (chave, título, largura, estica).
    px: função que converte tamanho lógico em pixels reais (escala da tela).
    """

    def __init__(self, pai, colunas, px, ao_selecionar=None, ao_duplo_clique=None,
                 ao_ordenar=None) -> None:
        super().__init__(
            pai, fg_color=T.SUPERFICIE, corner_radius=0,
            border_width=1, border_color=T.BORDA,
        )
        self._ao_selecionar = ao_selecionar
        self._ao_duplo_clique = ao_duplo_clique
        self._titulos = {c[0]: c[1] for c in colunas}
        self._tag_base = {}
        self._sel_aplicada = set()
        self._estilizar(px)
        self._cabecalho_px = px(44)     # altura aproximada da linha de títulos
        self._altura_icone = px(250)    # altura mínima para mostrar o ícone grande

        self.tree = ttk.Treeview(
            self, columns=tuple(c[0] for c in colunas), show="headings",
            style="Hosp.Treeview", selectmode="extended",
        )
        for chave, titulo, largura, estica in colunas:
            if ao_ordenar:
                self.tree.heading(chave, text=titulo, anchor="w",
                                  command=lambda c=chave: ao_ordenar(c))
            else:
                self.tree.heading(chave, text=titulo, anchor="w")
            self.tree.column(chave, width=largura, minwidth=90, anchor="w", stretch=estica)
        for tag, fundo in (("pendente", T.AMBAR_CLARO), ("atendida", T.VERDE_CLARO),
                           ("neutra", T.SUPERFICIE), ("vencida", T.VERMELHO_CLARO),
                           ("selecionada", T.SELECAO)):
            self.tree.tag_configure(tag, background=fundo, foreground=T.TEXTO)

        barra = ttk.Scrollbar(self, orient="vertical", style="Hosp.Vertical.TScrollbar",
                              command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        barra.pack(side="right", fill="y", pady=1, padx=(0, 1))

        # Estado vazio (sobreposto à tabela)
        # Cobre só o corpo da tabela (nunca a linha de títulos) e, em janelas
        # baixas, esconde o ícone para o texto não ser cortado.
        self.vazio = ctk.CTkFrame(self, fg_color=T.SUPERFICIE, corner_radius=0)
        miolo = ctk.CTkFrame(self.vazio, fg_color="transparent")
        miolo.place(relx=0.5, rely=0.42, anchor="center")
        self._icone_vazio = ctk.CTkLabel(
            miolo, text="", image=icone("clipboard", T.BORDA_FORTE, 64))
        self._icone_vazio.pack()
        self._vazio_titulo = ctk.CTkLabel(
            miolo, text="", font=fonte(17, "bold"), text_color=T.TEXTO,
        )
        self._vazio_titulo.pack(pady=(8, 0))
        self._vazio_texto = ctk.CTkLabel(
            miolo, text="", font=fonte(13), text_color=T.TEXTO_SUAVE,
        )
        self._vazio_texto.pack()
        self._icone_visivel = True
        self.bind("<Configure>", self._ajustar_vazio)

        self.tree.bind("<<TreeviewSelect>>", self._selecionou)
        self.tree.bind("<Double-1>", self._duplo_clique)

    @staticmethod
    def _estilizar(px) -> None:
        # Widgets ttk não seguem a escala do CustomTkinter: usamos pixels reais
        # (tamanho negativo = pixels), proporcionais à escala da interface.
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure(
            "Hosp.Treeview", background=T.SUPERFICIE, fieldbackground=T.SUPERFICIE,
            foreground=T.TEXTO, rowheight=px(40), font=(T.FONTE, -px(14)),
            borderwidth=0,
        )
        estilo.layout("Hosp.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        estilo.configure(
            "Hosp.Treeview.Heading", background=T.NAVY, foreground=T.BRANCO,
            font=(T.FONTE, -px(14), "bold"), relief="flat", padding=(px(10), px(9)),
        )
        estilo.map("Hosp.Treeview.Heading", background=[("active", T.NAVY_ATIVO)])
        # Corrige o Tk 8.6.9 (Python 3.9), onde as cores de 'tag' ignoravam a seleção
        sem_tags = [
            e for e in estilo.map("Hosp.Treeview", query_opt="background")
            if e[:2] != ("!disabled", "!selected")
        ]
        # Seleção suave, com o texto escuro mantido (leitura fácil, nada chamativo).
        estilo.map(
            "Hosp.Treeview",
            background=[("selected", T.SELECAO)] + sem_tags,
            foreground=[("selected", T.TEXTO)],
        )
        estilo.configure(
            "Hosp.Vertical.TScrollbar", background=T.BORDA_FORTE, troughcolor=T.FUNDO,
            bordercolor=T.FUNDO, arrowcolor=T.TEXTO_SUAVE, relief="flat",
        )

    # --- Conteúdo ------------------------------------------------------
    def preencher(self, linhas) -> None:
        """linhas: lista de (iid, valores, tag_base). Mantém a seleção atual
        das linhas que continuam existindo."""
        anterior = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        self._tag_base = {}
        self._sel_aplicada = set()  # linhas recém-inseridas começam sem seleção
        for iid, valores, tag in linhas:
            self._tag_base[iid] = tag
            self.tree.insert("", "end", iid=iid, tags=(tag,), values=valores)
        manter = [i for i in anterior if self.tree.exists(i)]
        if manter:
            self.tree.selection_set(manter)
        self._sincronizar()

    def definir_ordenacao(self, chave: str, decrescente: bool) -> None:
        """Mostra a seta ▲/▼ no título da coluna ordenada."""
        for col, titulo in self._titulos.items():
            seta = (" ▼" if decrescente else " ▲") if col == chave else ""
            self.tree.heading(col, text=titulo + seta)

    def selecionados(self) -> list:
        return list(self.tree.selection())

    def mostrar_vazio(self, titulo: str, texto: str) -> None:
        self._vazio_titulo.configure(text=titulo)
        self._vazio_texto.configure(text=texto)
        self.vazio.place(x=1, y=self._cabecalho_px, relwidth=1, relheight=1)
        self.vazio.lift()

    def _ajustar_vazio(self, evento=None) -> None:
        """Mostra o ícone grande só quando o corpo da tabela é alto o bastante."""
        altura = getattr(evento, "height", 0) or self.winfo_height()
        cabe = altura - self._cabecalho_px >= self._altura_icone
        if cabe != self._icone_visivel:
            self._icone_visivel = cabe
            if cabe:
                self._icone_vazio.pack(before=self._vazio_titulo)
            else:
                self._icone_vazio.pack_forget()

    def esconder_vazio(self) -> None:
        self.vazio.place_forget()

    # --- Seleção -------------------------------------------------------
    def _sincronizar(self) -> None:
        """Pinta de 'selecionada' as linhas escolhidas e devolve às demais a cor base."""
        atual = set(self.tree.selection())
        for iid in atual ^ self._sel_aplicada:
            if not self.tree.exists(iid):
                continue
            tag = "selecionada" if iid in atual else self._tag_base.get(iid, "neutra")
            self.tree.item(iid, tags=(tag,))
        self._sel_aplicada = atual

    def _selecionou(self, _evento=None) -> None:
        self._sincronizar()
        if self._ao_selecionar:
            self._ao_selecionar()

    def _duplo_clique(self, evento) -> None:
        iid = self.tree.identify_row(evento.y)
        if iid:
            self.tree.selection_set(iid)
            if self._ao_duplo_clique:
                self._ao_duplo_clique(iid)


class DialogoConfirmacao(ctk.CTkToplevel):
    """Janela modal de confirmação. Use `DialogoConfirmacao.perguntar(...)`."""

    def __init__(self, pai, titulo: str, destaque: str, mensagem: str,
                 texto_confirmar: str = "Excluir", nome_icone: str = "trash",
                 cor: str = None, cor_hover: str = None,
                 cor_clara: str = None) -> None:
        # Padrões lidos na hora (o tema pode ter mudado desde a importação)
        cor = cor or T.VERMELHO
        cor_hover = cor_hover or T.VERMELHO_HOVER
        cor_clara = cor_clara or T.VERMELHO_CLARO
        super().__init__(pai, fg_color=T.CARD)
        self.resultado = False
        self.title(titulo)
        self.resizable(False, False)
        centralizar(self, pai, 480, 300)

        ctk.CTkFrame(self, fg_color=cor, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=30, pady=(24, 8))

        topo = ctk.CTkFrame(corpo, fg_color="transparent")
        topo.pack(fill="x")
        circulo = ctk.CTkFrame(topo, width=56, height=56, corner_radius=28,
                               fg_color=cor_clara)
        circulo.pack(side="left")
        circulo.pack_propagate(False)
        ctk.CTkLabel(circulo, text="", image=icone(nome_icone, cor, 28)).place(
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
            text_color=cor, anchor="w", wraplength=340,
        )).pack(anchor="w")

        alinhar_esquerda(ctk.CTkLabel(
            corpo, text=mensagem, font=fonte(14), text_color=T.TEXTO_SUAVE,
            anchor="w", wraplength=410,
        )).pack(anchor="w", pady=(18, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=30, pady=(8, 24))
        ctk.CTkButton(
            botoes, text=texto_confirmar, width=130, height=42,
            font=fonte(14, "bold"), fg_color=cor, hover_color=cor_hover,
            text_color=T.SOBRE_COR, command=self._confirmar,
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
                  texto_confirmar: str = "Excluir", **estilo) -> bool:
        """`estilo` aceita nome_icone, cor, cor_hover e cor_clara."""
        dialogo = cls(pai, titulo, destaque, mensagem, texto_confirmar, **estilo)
        pai.wait_window(dialogo)
        return dialogo.resultado
