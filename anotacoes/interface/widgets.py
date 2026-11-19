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
  - MenuPopup           menu suspenso (clique direito, Exportar) com ícones e atalhos
"""

import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Optional

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.icons import icone

log = logging.getLogger(__name__)


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
        log.debug("Falha ignorada em alinhar_esquerda()", exc_info=True)
    return rotulo


# ----------------------------------------------------------------------
# Utilidades de janela
# ----------------------------------------------------------------------
def limites_da_tela(janela, x: int, y: int) -> tuple:
    """Área útil (esq, topo, dir, base) do monitor que contém o ponto (x, y).

    No Windows consulta o monitor real (barra de tarefas descontada), o que
    funciona com vários monitores, inclusive à esquerda/acima do principal
    (coordenadas negativas). Sem isso, usa a área virtual do Tk e, por fim,
    a tela principal."""
    try:
        import ctypes
        from ctypes import wintypes

        class _Info(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
        usuario = ctypes.windll.user32
        usuario.MonitorFromPoint.restype = wintypes.HANDLE
        monitor = usuario.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2)
        info = _Info()
        info.cbSize = ctypes.sizeof(_Info)
        if monitor and usuario.GetMonitorInfoW(monitor, ctypes.byref(info)):
            r = info.rcWork
            return (r.left, r.top, r.right, r.bottom)
    except Exception:
        log.debug("Monitor real indisponível; usando a área virtual", exc_info=True)
    try:
        esq, topo = janela.winfo_vrootx(), janela.winfo_vrooty()
        larg, alt = janela.winfo_vrootwidth(), janela.winfo_vrootheight()
        if larg > 0 and alt > 0:
            return (esq, topo, esq + larg, topo + alt - 48)
    except Exception:
        log.debug("Área virtual indisponível", exc_info=True)
    return (0, 0, janela.winfo_screenwidth(), janela.winfo_screenheight() - 48)


def ajustar_ao_monitor(janela, x: int, y: int, w: int, h: int, margem: int = 8,
                       abrir_para_cima: bool = False, x0=None, y0=None) -> tuple:
    """Devolve (x, y) mantendo a janela w×h dentro do monitor do ponto (x, y).
    `x0`/`y0`: canto desejado da janela (padrão: o próprio ponto)."""
    esq, topo, dir_, base = limites_da_tela(janela, x, y)
    x = x if x0 is None else x0
    y = y if y0 is None else y0
    if x + w > dir_ - margem:
        x = dir_ - w - margem
    if x < esq + margem:
        x = esq + margem
    if y + h > base - 4:
        y = y - h if abrir_para_cima else base - h - 4
    if y < topo + 4:
        y = topo + 4
    return int(x), int(y)


def _pai_visivel(pai) -> bool:
    """A janela principal está na tela (não minimizada, oculta nem fora da área visível)?"""
    try:
        if str(pai.state()) in ("iconic", "withdrawn"):
            return False
    except Exception:
        log.debug("Estado da janela principal indisponível", exc_info=True)
    try:
        return pai.winfo_width() > 50 and pai.winfo_rootx() > -10000
    except Exception:
        return False


def centralizar(janela, pai, largura: int, altura: int) -> None:
    """Abre `janela` no centro da janela principal (considera a escala do Windows).

    Se a principal estiver minimizada/oculta (ex.: alerta de pausa), centraliza no
    monitor onde está o mouse. Só define a posição inicial: a janela continua livre
    para ser arrastada para onde a pessoa quiser."""
    try:
        pai.update_idletasks()
        try:
            fator = janela._get_window_scaling()
        except Exception:
            fator = 1.0
        w, h = int(largura * fator), int(altura * fator)
        if _pai_visivel(pai):
            cx = pai.winfo_rootx() + pai.winfo_width() // 2
            cy = pai.winfo_rooty() + pai.winfo_height() // 2
        else:
            try:
                cx, cy = pai.winfo_pointerx(), pai.winfo_pointery()
            except Exception:
                cx, cy = pai.winfo_screenwidth() // 2, pai.winfo_screenheight() // 2
            esq, topo, dir_, base = limites_da_tela(pai, cx, cy)
            cx, cy = (esq + dir_) // 2, (topo + base) // 2
        x, y = ajustar_ao_monitor(janela, cx, cy, w, h, margem=0,
                                  x0=cx - w // 2, y0=cy - h // 2)
        janela.geometry(f"{largura}x{altura}+{x}+{y}")
    except Exception:
        janela.geometry(f"{largura}x{altura}")


def tornar_modal(janela, pai, foco=None) -> None:
    """Deixa a janela modal (bloqueia a principal) e fecha com Esc."""
    try:
        janela.transient(pai)
    except Exception:
        log.debug("Falha ignorada em tornar_modal()", exc_info=True)

    def _ativar():
        try:
            janela.grab_set()
            (foco or janela).focus_force()
        except Exception:
            log.debug("Falha ignorada em _ativar()", exc_info=True)

    janela.after(150, _ativar)
    janela.bind("<Escape>", lambda _e: janela.destroy())


# ----------------------------------------------------------------------
# Componentes
# ----------------------------------------------------------------------
class ItemNavegacao(ctk.CTkFrame):
    """Botão do menu lateral. Quando ativo, ganha fundo e uma faixa colorida."""

    def __init__(self, pai, texto: str, nome_icone: str, comando) -> None:
        super().__init__(pai, fg_color="transparent", corner_radius=0)
        # height=1: sem isso o CustomTkinter pede 200 px de altura e cada item do menu
        # ocupa a barra inteira (o último item, "Backup", sumia da tela).
        self._faixa = ctk.CTkFrame(self, width=4, height=1, fg_color="transparent",
                                   corner_radius=2)
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
        ctk.CTkFrame(self, width=6, height=1, fg_color=cor, corner_radius=3).pack(
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


class FluxoBotoes(ctk.CTkFrame):
    """Itens lado a lado que quebram de linha sozinhos conforme a largura disponível
    (ao ampliar ou encolher a janela, eles se reorganizam). `ao_mudar_linhas()` é chamado
    quando a quantidade de linhas muda.

    Itens "móveis" (`adicionar(item, movel=True, ao_clicar=...)`) podem ser arrastados com o
    mouse para outra posição; ao soltar, `ao_reordenar(ordem)` recebe a nova ordem (lista dos
    `chave` dos itens móveis). Um clique sem arrastar chama `ao_clicar`."""

    LIMIAR_ARRASTO = 6      # pixels de movimento para contar como arrasto (e não clique)

    def __init__(self, pai, espaco: int = 6, ao_mudar_linhas=None, ao_reordenar=None) -> None:
        super().__init__(pai, fg_color="transparent")
        self._itens = []
        self._moveis = {}            # item -> (chave, ao_clicar)
        self._espaco = espaco
        self._largura = 0
        self._linhas = 0
        self._ao_mudar = ao_mudar_linhas
        self._ao_reordenar = ao_reordenar
        self._pressionado = None     # (item, x_inicial, y_inicial)
        self._arrastando = None
        self.bind("<Configure>", self._configurou)

    def adicionar(self, botao, movel: bool = False, chave=None, ao_clicar=None, partes=()) -> None:
        self._itens.append(botao)
        if movel:
            self._moveis[botao] = (chave, ao_clicar)
            for parte in (botao, *partes):
                parte.bind("<ButtonPress-1>", lambda e, b=botao: self._pressionou(b, e), add="+")
                parte.bind("<B1-Motion>", self._moveu, add="+")
                parte.bind("<ButtonRelease-1>", self._soltou, add="+")
        self._reordenar(self._largura)

    # --- arrastar ------------------------------------------------------
    def _pressionou(self, item, evento) -> None:
        self._pressionado = (item, evento.x_root, evento.y_root)
        self._arrastando = None

    def _item_em(self, x: int, y: int):
        """Item móvel sob o ponto (coordenadas da tela), ou o mais próximo na mesma linha."""
        melhor, dist = None, None
        for item in self._moveis:
            try:
                esq, topo = item.winfo_rootx(), item.winfo_rooty()
                dir_, base = esq + item.winfo_width(), topo + item.winfo_height()
            except Exception:
                continue
            if esq <= x <= dir_ and topo <= y <= base:
                return item
            if topo - 4 <= y <= base + 4:
                d = min(abs(x - esq), abs(x - dir_))
                if dist is None or d < dist:
                    melhor, dist = item, d
        return melhor

    def _moveu(self, evento) -> None:
        if self._pressionado is None:
            return
        item, x0, y0 = self._pressionado
        if self._arrastando is None:
            if abs(evento.x_root - x0) + abs(evento.y_root - y0) < self.LIMIAR_ARRASTO:
                return
            self._arrastando = item
            try:
                self.configure(cursor="fleur")
            except Exception:
                log.debug("Cursor de arrasto indisponível", exc_info=True)
        alvo = self._item_em(evento.x_root, evento.y_root)
        if alvo is not None and alvo is not item and alvo in self._moveis:
            self.mover(item, self._itens.index(alvo))

    def mover(self, item, indice: int) -> None:
        """Coloca `item` na posição `indice` da lista e refaz as linhas."""
        self._itens.remove(item)
        self._itens.insert(indice, item)
        self._reordenar(self._largura)

    def _soltou(self, _evento) -> None:
        pressionado, arrastou = self._pressionado, self._arrastando
        self._pressionado = self._arrastando = None
        try:
            self.configure(cursor="")
        except Exception:
            log.debug("Cursor de arrasto indisponível", exc_info=True)
        if pressionado is None:
            return
        item = pressionado[0]
        chave, ao_clicar = self._moveis.get(item, (None, None))
        if arrastou is not None:
            if self._ao_reordenar:
                self._ao_reordenar(self.ordem())
        elif ao_clicar:
            ao_clicar()

    def ordem(self) -> list:
        """Chaves dos itens móveis, na ordem atual."""
        return [self._moveis[i][0] for i in self._itens if i in self._moveis]

    # --- layout --------------------------------------------------------
    def _configurou(self, evento) -> None:
        if evento.width != self._largura:
            self._largura = evento.width
            self._reordenar(self._largura)

    def _reordenar(self, largura: int) -> None:
        """Distribui os itens em linhas que cabem em `largura` pixels (0 = ainda não medida)."""
        linha = coluna = usado = 0
        escala = 1.0
        try:
            escala = float(self._get_widget_scaling())
        except Exception:
            log.debug("Escala do widget indisponível", exc_info=True)
        folga = round(self._espaco * escala)
        util = largura - 2 * folga          # sobra de segurança: nada encosta na borda
        for botao in self._itens:
            try:
                tamanho = int(botao.winfo_reqwidth())
            except Exception:
                tamanho = round(int(botao.cget("width") or 100) * escala)
            if largura > 1 and coluna and usado + tamanho > util:
                linha, coluna, usado = linha + 1, 0, 0
            botao.grid(row=linha, column=coluna, padx=(0, self._espaco),
                       pady=(0, self._espaco), sticky="w")
            coluna += 1
            usado += tamanho + folga
        total = linha + 1 if self._itens else 0
        if total != self._linhas:
            self._linhas = total
            if self._ao_mudar:
                self._ao_mudar()


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
            font=fonte(14, "bold"), wraplength=640,
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


class DialogoNovoUsuario(ctk.CTkToplevel):
    """Janela modal para criar uma conta: e-mail, senha (ou gerar) e papel.

    Use `DialogoNovoUsuario.perguntar(pai, validar, gerar_senha)`: devolve None (cancelou) ou
    {"email", "senha", "admin", "gerada"}. `validar(email, senha)` devolve a mensagem de erro
    ou None; `gerar_senha()` devolve uma senha forte.
    """

    def __init__(self, pai, validar, gerar_senha) -> None:
        super().__init__(pai, fg_color=T.CARD)
        self.resultado = None
        self._validar, self._gerar = validar, gerar_senha
        self._gerada = False
        self.title("Novo usuário")
        self.resizable(False, False)
        centralizar(self, pai, 500, 520)

        ctk.CTkFrame(self, fg_color=T.TEAL, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=30, pady=(22, 6))
        ctk.CTkLabel(corpo, text="Novo usuário", font=fonte(20, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w")
        alinhar_esquerda(ctk.CTkLabel(
            corpo, text="A conta nasce já confirmada e pode entrar na hora. Entregue a senha à "
                        "pessoa por um meio seguro; ela não é guardada em lugar nenhum.",
            font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=440,
        )).pack(anchor="w", pady=(4, 12))

        def campo(texto, dica, mascarar=False):
            ctk.CTkLabel(corpo, text=texto, font=fonte(13, "bold"), text_color=T.TEXTO,
                         anchor="w").pack(anchor="w", pady=(6, 2))
            entrada = ctk.CTkEntry(
                corpo, height=42, font=fonte(14), placeholder_text=dica,
                placeholder_text_color=T.PLACEHOLDER, corner_radius=10, border_width=2,
                border_color=T.BORDA, fg_color=T.SUPERFICIE, text_color=T.TEXTO,
                show="•" if mascarar else "")
            entrada.pack(fill="x")
            return entrada

        self.ent_email = campo("E-mail", "pessoa@hospital.org")
        self.ent_senha = campo("Senha (mínimo 8 caracteres)", "Digite ou clique em Gerar", True)
        linha = ctk.CTkFrame(corpo, fg_color="transparent")
        linha.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(
            linha, text="Gerar senha forte", width=150, height=34, font=fonte(12, "bold"),
            fg_color="transparent", text_color=T.TEAL, border_width=2, border_color=T.TEAL,
            hover_color=T.TEAL_CLARO, command=self._gerar_senha).pack(side="left")
        self.chk_mostrar = ctk.CTkCheckBox(
            linha, text="Mostrar senha", font=fonte(12), text_color=T.TEXTO,
            fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, border_color=T.BORDA_FORTE,
            checkmark_color=T.SOBRE_COR, checkbox_width=20, checkbox_height=20,
            corner_radius=5, border_width=2, command=self._alternar_mostrar)
        self.chk_mostrar.pack(side="right")
        self.chk_admin = ctk.CTkCheckBox(
            corpo, text="Administrador (vê e gerencia todas as contas)", font=fonte(13),
            text_color=T.TEXTO, fg_color=T.AMBAR, hover_color=T.AMBAR,
            border_color=T.BORDA_FORTE, checkmark_color=T.SOBRE_COR,
            checkbox_width=22, checkbox_height=22, corner_radius=6, border_width=2)
        self.chk_admin.pack(anchor="w", pady=(14, 0))
        self.lbl_erro = ctk.CTkLabel(corpo, text="", height=22, font=fonte(12, "bold"),
                                     text_color=T.VERMELHO, anchor="w", wraplength=440)
        self.lbl_erro.pack(fill="x", pady=(8, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=30, pady=(6, 24))
        ctk.CTkButton(
            botoes, text="Criar usuário", width=150, height=42, font=fonte(14, "bold"),
            fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
            command=self._confirmar).pack(side="right")
        ctk.CTkButton(
            botoes, text="Cancelar", width=120, height=42, font=fonte(14, "bold"),
            fg_color="transparent", text_color=T.TEXTO, border_width=2,
            border_color=T.BORDA_FORTE, hover_color=T.FUNDO, command=self.destroy,
        ).pack(side="right", padx=(0, 12))
        tornar_modal(self, pai, foco=self.ent_email)
        self.bind("<Return>", lambda _e: self._confirmar())

    def _gerar_senha(self) -> None:
        self.ent_senha.delete(0, "end")
        self.ent_senha.insert(0, self._gerar())
        self._gerada = True
        self.chk_mostrar.select()
        self._alternar_mostrar()

    def _alternar_mostrar(self) -> None:
        self.ent_senha.configure(show="" if self.chk_mostrar.get() else "•")

    def _confirmar(self) -> None:
        email, senha = self.ent_email.get().strip(), self.ent_senha.get()
        erro = self._validar(email, senha)
        if erro:
            self.lbl_erro.configure(text=erro)
            return
        self.resultado = {"email": email, "senha": senha, "admin": bool(self.chk_admin.get()),
                          "gerada": self._gerada}
        self.destroy()

    @classmethod
    def perguntar(cls, pai, validar, gerar_senha):
        dialogo = cls(pai, validar, gerar_senha)
        pai.wait_window(dialogo)
        return dialogo.resultado


# ----------------------------------------------------------------------
# Menu suspenso (clique direito e botão Exportar)
# ----------------------------------------------------------------------
@dataclass
class ItemMenu:
    """Uma opção do MenuPopup. `perigo` pinta de vermelho (ex.: Excluir)."""
    rotulo: str
    comando: Callable
    icone: Optional[str] = None
    atalho: Optional[str] = None
    perigo: bool = False


SEPARADOR = None      # use no meio da lista de itens para desenhar uma linha divisória


class MenuPopup(tk.Toplevel):
    """Menu suspenso no padrão visual do sistema (substitui o menu cinza nativo do Tk).

    Cartão com borda fina, ícones, dica do atalho de teclado à direita, destaque suave ao
    passar o mouse e opção perigosa em vermelho. Também funciona pelo teclado
    (setas, Enter e Esc) e fecha ao clicar fora. As cores são lidas ao abrir, então
    acompanham o tema claro/escuro.

    Use `MenuPopup.abrir(janela, x, y, itens, titulo=...)`. `x`, `y` são coordenadas de tela;
    com `ancora="dir"`, `x` é a borda DIREITA do menu (útil sob um botão no canto).
    """

    LARGURA = 272
    ALTURA_ITEM = 36          # + 2 de espaçamento vertical por item
    MARGEM = 6

    def __init__(self, pai, x: int, y: int, itens, titulo: Optional[str] = None,
                 largura: Optional[int] = None, ancora: str = "esq") -> None:
        super().__init__(pai, bg=T.BORDA_FORTE, highlightthickness=0)
        self._pai = pai
        self._fechado = False
        self._atual: Optional[int] = None
        self._acoes: list = []          # (linha, item) só das opções clicáveis
        largura = largura or self.LARGURA
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except Exception:
            log.debug("Falha ignorada em MenuPopup.__init__()", exc_info=True)

        corpo = ctk.CTkFrame(self, fg_color=T.CARD, corner_radius=0)
        corpo.pack(fill="both", expand=True, padx=1, pady=1)
        # espaçador: define a largura do menu (e a margem de cima)
        ctk.CTkFrame(corpo, width=largura - 2, height=self.MARGEM,
                     fg_color="transparent", corner_radius=0).pack()
        altura = 2 + 2 * self.MARGEM

        if titulo:
            ctk.CTkLabel(corpo, text=titulo, height=22, font=fonte(12, "bold"),
                         text_color=T.TEXTO_SUAVE, anchor="w").pack(
                             fill="x", padx=16, pady=(4, 2))
            altura += 28
            altura += self._separador(corpo)

        for item in itens:
            if item is SEPARADOR:
                altura += self._separador(corpo)
            else:
                self._criar_item(corpo, item)
                altura += self.ALTURA_ITEM + 2

        ctk.CTkFrame(corpo, height=self.MARGEM, fg_color="transparent",
                     corner_radius=0).pack(fill="x")

        self._posicionar(x, y, largura, altura, ancora)
        for tecla, acao in (("<Escape>", lambda _e: self._fechar()),
                            ("<Up>", lambda _e: self._mover(-1)),
                            ("<Down>", lambda _e: self._mover(1)),
                            ("<Return>", lambda _e: self._ativar(self._atual)),
                            ("<Button-1>", self._clique), ("<Button-3>", self._clique)):
            self.bind(tecla, acao)
        self.after(20, self._capturar)
        self.after(250, lambda: self.bind(
            "<FocusOut>", lambda _e: self.after(120, self._conferir_foco)))

    # --- construção ----------------------------------------------------
    @staticmethod
    def _separador(corpo) -> int:
        ctk.CTkFrame(corpo, height=1, fg_color=T.BORDA, corner_radius=0).pack(
            fill="x", padx=12, pady=5)
        return 11

    def _criar_item(self, corpo, item: ItemMenu) -> None:
        indice = len(self._acoes)
        cor = T.VERMELHO if item.perigo else T.TEXTO
        linha = ctk.CTkFrame(corpo, fg_color="transparent", corner_radius=6,
                             height=self.ALTURA_ITEM)
        linha.pack(fill="x", padx=self.MARGEM, pady=1)
        linha.pack_propagate(False)
        partes = [linha]
        if item.icone:
            partes.append(ctk.CTkLabel(
                linha, text="", width=24,
                image=icone(item.icone, T.VERMELHO if item.perigo else T.TEXTO_SUAVE, 18)))
            partes[-1].pack(side="left", padx=(10, 8))
        rotulo = ctk.CTkLabel(linha, text=item.rotulo, font=fonte(14), text_color=cor,
                              anchor="w")
        rotulo.pack(side="left", padx=(0 if item.icone else 14, 0))
        partes.append(rotulo)
        if item.atalho:
            dica = ctk.CTkLabel(linha, text=item.atalho, font=fonte(12),
                                text_color=T.TEXTO_SUAVE, anchor="e")
            dica.pack(side="right", padx=(8, 14))
            partes.append(dica)
        for parte in partes:
            parte.bind("<Enter>", lambda _e, i=indice: self._destacar(i))
            parte.bind("<Button-1>", lambda _e, i=indice: self._ativar(i))
        self._acoes.append((linha, item))

    def _posicionar(self, x: int, y: int, largura: int, altura: int, ancora: str) -> None:
        """Coloca o menu perto do ponto pedido, sem sair da tela (coordenadas em pixels)."""
        try:
            fator = float(self._pai._get_window_scaling())
        except Exception:
            fator = 1.0
        w, h = int(round(largura * fator)), int(round(altura * fator))
        try:
            self.update_idletasks()
            w, h = max(w, self.winfo_reqwidth()), self.winfo_reqheight()
        except Exception:
            log.debug("Medida real do menu indisponível; usando a estimada", exc_info=True)
        if ancora == "dir":
            x -= w
        # monitor do clique (não o principal); sem espaço embaixo, abre para cima
        x, y = ajustar_ao_monitor(self, int(x) + (w if ancora == "dir" else 0), int(y),
                                  w, h, abrir_para_cima=True)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # --- interação -----------------------------------------------------
    def _capturar(self, tentativas: int = 5) -> None:
        """Captura o mouse e o teclado. O Tk só aceita com a janela já visível: tenta de novo."""
        if self._fechado:
            return
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            if tentativas > 0:
                self.after(40, lambda: self._capturar(tentativas - 1))
            else:
                log.debug("Falha ignorada em MenuPopup._capturar()", exc_info=True)

    def _destacar(self, indice: Optional[int]) -> None:
        if self._fechado or indice is None or indice == self._atual:
            return
        if self._atual is not None:
            self._acoes[self._atual][0].configure(fg_color="transparent")
        self._atual = indice
        linha, item = self._acoes[indice]
        linha.configure(fg_color=T.VERMELHO_CLARO if item.perigo else T.SELECAO)

    def _mover(self, passo: int) -> None:
        if self._fechado or not self._acoes:
            return
        base = -1 if self._atual is None and passo > 0 else (0 if self._atual is None else self._atual)
        self._destacar((base + passo) % len(self._acoes))

    def _ativar(self, indice: Optional[int]) -> None:
        if self._fechado or indice is None:
            return
        comando = self._acoes[indice][1].comando
        pai = self._pai
        self._fechar()
        pai.after(10, comando)          # depois de fechar, para o foco voltar à janela

    def _clique(self, evento) -> None:
        """Clique fora do menu (o menu captura o mouse) fecha sem executar nada."""
        if self._fechado:
            return
        try:
            x0, y0 = self.winfo_rootx(), self.winfo_rooty()
            dentro = (x0 <= evento.x_root < x0 + self.winfo_width()
                      and y0 <= evento.y_root < y0 + self.winfo_height())
        except Exception:
            dentro = True
        if not dentro:
            self._fechar()

    def _conferir_foco(self) -> None:
        if self._fechado:
            return
        try:
            foco = self.focus_get()
        except Exception:       # o Tk levanta KeyError com certas listas suspensas
            foco = None
        if foco is None:
            self._fechar()

    def _fechar(self) -> None:
        if self._fechado:
            return
        self._fechado = True
        try:
            self.grab_release()
        except Exception:
            log.debug("Falha ignorada em MenuPopup._fechar()", exc_info=True)
        if getattr(self._pai, "_menu_popup", None) is self:
            self._pai._menu_popup = None
        self.destroy()

    @classmethod
    def abrir(cls, pai, x: int, y: int, itens, titulo: Optional[str] = None,
              largura: Optional[int] = None, ancora: str = "esq") -> "MenuPopup":
        """Abre o menu (fechando outro que já esteja aberto)."""
        anterior = getattr(pai, "_menu_popup", None)
        if anterior is not None:
            try:
                anterior._fechar()
            except Exception:
                log.debug("Falha ignorada em MenuPopup.abrir()", exc_info=True)
        menu = cls(pai, x, y, itens, titulo=titulo, largura=largura, ancora=ancora)
        pai._menu_popup = menu
        return menu
