"""
gui.py
------
Janela principal do sistema de registro de solicitações (CustomTkinter).

Estrutura:
  - Barra lateral: marca, menu, relógio e atalho para a pasta de dados.
  - Página "Novo registro": formulário com validação + resumo e últimos registros.
  - Página "Histórico": indicadores, busca, filtro, tabela e ações
    (marcar como atendida/pendente, ver detalhes, excluir).

Logotipo oficial (opcional): salve como "logo.png" ao lado do programa.
Cores, nome da instituição e fonte: veja theme.py.
"""

import os
import sys
import tkinter as tk
import traceback
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

import theme as T
from database import (
    MAX_CONTATO,
    MAX_DESCRICAO,
    MAX_NOME,
    STATUS_ATENDIDA,
    STATUS_PENDENTE,
    Database,
)
from icons import icone
from icons import imagem as imagem_icone
from widgets import (
    CaixaBusca,
    CartaoNumero,
    DialogoConfirmacao,
    ItemNavegacao,
    Notificacao,
    Pilula,
    alinhar_esquerda,
    centralizar,
    fonte,
    tornar_modal,
)

PAG_NOVO = "novo"
PAG_HIST = "historico"

FILTROS_STATUS = {
    "Todos": None,
    "Pendentes": STATUS_PENDENTE,
    "Atendidas": STATUS_ATENDIDA,
}

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


# ----------------------------------------------------------------------
# Funções auxiliares de texto e arquivos
# ----------------------------------------------------------------------
def plural(n: int, singular: str, plural_: str) -> str:
    """plural(1, 'registro', 'registros') -> '1 registro'."""
    return f"{n} {singular if n == 1 else plural_}"


def formatar_data(valor: str) -> str:
    """'2026-11-04 18:45:00' -> '04/11/2026 18:45'."""
    try:
        return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return valor or ""


def data_curta(valor: str) -> str:
    """'2026-11-04 18:45:00' -> '04/11 18:45'."""
    try:
        return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return valor or ""


def resumir(texto: str, limite: int) -> str:
    """Junta quebras de linha e corta com reticências."""
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def localizar_arquivo(nome: str):
    """Procura um arquivo ao lado do .exe, dentro do pacote ou do código-fonte."""
    pastas = []
    if getattr(sys, "frozen", False):
        pastas.append(os.path.dirname(sys.executable))
        if hasattr(sys, "_MEIPASS"):
            pastas.append(sys._MEIPASS)
    pastas.append(os.path.dirname(os.path.abspath(__file__)))
    for pasta in pastas:
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho):
            return caminho
    return None


def cores_status(status: str):
    """(fundo, texto) da etiqueta de status."""
    if status == STATUS_ATENDIDA:
        return T.VERDE_CLARO, T.VERDE
    return T.AMBAR_CLARO, T.AMBAR


# ======================================================================
# Janela principal
# ======================================================================
class App(ctk.CTk):
    def __init__(self) -> None:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title(f"{T.NOME_INSTITUICAO} — Solicitações de pacientes")
        self.geometry("1240x780")
        self.minsize(1080, 700)
        self.configure(fg_color=T.FUNDO)

        icone_janela = localizar_arquivo("icone.ico")
        if icone_janela:
            try:
                self.iconbitmap(icone_janela)
            except tk.TclError:
                pass  # ícone indisponível neste sistema: segue sem ele

        self._com_erro = set()      # campos do formulário com erro
        self._rotulos_erro = {}     # campo -> rótulo da mensagem de erro
        self._total_exibido = 0

        try:
            self.db = Database()
        except Exception as exc:
            messagebox.showerror(
                "Não foi possível iniciar",
                "O banco de dados não pôde ser aberto ou criado.\n\n"
                f"Detalhe: {exc}\n\n"
                "Verifique se a pasta do programa permite gravação.",
            )
            self.destroy()
            raise SystemExit(1)

        self.report_callback_exception = self._erro_inesperado

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._montar_barra_lateral()
        self._montar_area()

        self.bind("<Control-s>", lambda _e: self._atalho_salvar())
        self.mostrar_pagina(PAG_NOVO)
        self.atualizar_tudo()
        self._atualizar_relogio()

    # ==================================================================
    # Barra lateral
    # ==================================================================
    def _montar_barra_lateral(self) -> None:
        barra = ctk.CTkFrame(self, width=272, fg_color=T.NAVY, corner_radius=0)
        barra.grid(row=0, column=0, sticky="nsew")
        barra.pack_propagate(False)

        # --- Marca ---------------------------------------------------
        marca = ctk.CTkFrame(barra, fg_color="transparent")
        marca.pack(fill="x", padx=22, pady=(30, 6))
        self._montar_logo(marca)
        textos = ctk.CTkFrame(marca, fg_color="transparent")
        textos.pack(side="left", padx=(12, 0))
        alinhar_esquerda(ctk.CTkLabel(
            textos, text=T.NOME_INSTITUICAO, font=fonte(16, "bold"),
            text_color=T.BRANCO, anchor="w", wraplength=170,
        )).pack(anchor="w")
        ctk.CTkLabel(
            textos, text=T.SUBTITULO, font=fonte(12),
            text_color=T.NAV_SUAVE, anchor="w",
        ).pack(anchor="w")

        ctk.CTkFrame(barra, height=1, fg_color=T.NAV_LINHA, corner_radius=0).pack(
            fill="x", padx=22, pady=(20, 18)
        )

        # --- Menu ----------------------------------------------------
        ctk.CTkLabel(
            barra, text="MENU", font=fonte(11, "bold"),
            text_color=T.NAV_SUAVE, anchor="w",
        ).pack(fill="x", padx=28, pady=(0, 8))

        self.nav = {}
        for chave, texto, nome_icone in (
            (PAG_NOVO, "Novo registro", "plus"),
            (PAG_HIST, "Histórico", "list"),
        ):
            item = ItemNavegacao(barra, texto, nome_icone,
                                 lambda c=chave: self.mostrar_pagina(c))
            item.pack(fill="x", padx=(8, 0), pady=3)
            self.nav[chave] = item

        # --- Rodapé (empilhado de baixo para cima) -------------------
        ctk.CTkLabel(
            barra, text=f"Dados salvos apenas neste computador  •  v{T.VERSAO}",
            font=fonte(11), text_color=T.NAV_SUAVE, wraplength=220, anchor="w",
        ).pack(side="bottom", anchor="w", padx=24, pady=(0, 20))

        ctk.CTkButton(
            barra, text="Abrir pasta dos dados", height=38, font=fonte(13, "bold"),
            fg_color="transparent", text_color=T.NAV_TEXTO, border_width=1,
            border_color=T.NAV_LINHA, hover_color=T.NAVY_HOVER,
            command=self.abrir_pasta_dados,
        ).pack(side="bottom", fill="x", padx=22, pady=(0, 14))

        relogio = ctk.CTkFrame(barra, fg_color=T.NAVY_HOVER, corner_radius=14)
        relogio.pack(side="bottom", fill="x", padx=22, pady=(0, 14))
        self.lbl_hora = ctk.CTkLabel(
            relogio, text="--:--", font=fonte(30, "bold"),
            text_color=T.BRANCO, anchor="w",
        )
        self.lbl_hora.pack(anchor="w", padx=18, pady=(12, 0))
        self.lbl_data = ctk.CTkLabel(
            relogio, text="", font=fonte(13), text_color=T.NAV_SUAVE, anchor="w",
        )
        self.lbl_data.pack(anchor="w", padx=18, pady=(0, 12))

    def _montar_logo(self, pai) -> None:
        """Usa logo.png (se existir) sobre placa branca; senão, a marca própria."""
        caminho = localizar_arquivo("logo.png")
        if caminho:
            try:
                from PIL import Image

                img = Image.open(caminho)
                altura = 40
                largura = max(1, int(img.width * altura / img.height))
                logo = ctk.CTkImage(light_image=img, size=(largura, altura))
                placa = ctk.CTkFrame(pai, fg_color=T.BRANCO, corner_radius=10)
                placa.pack(side="left")
                ctk.CTkLabel(placa, text="", image=logo).pack(padx=8, pady=6)
                return
            except Exception:
                pass  # arquivo inválido: usa a marca própria
        ctk.CTkLabel(pai, text="", image=icone("logo", T.BRANCO, 48)).pack(side="left")

    # ==================================================================
    # Área de conteúdo
    # ==================================================================
    def _montar_area(self) -> None:
        self.area = ctk.CTkFrame(self, fg_color=T.FUNDO, corner_radius=0)
        self.area.grid(row=0, column=1, sticky="nsew")

        self.paginas = {
            PAG_NOVO: self._criar_pagina_novo(self.area),
            PAG_HIST: self._criar_pagina_historico(self.area),
        }
        self.toast = Notificacao(self.area)

    def mostrar_pagina(self, chave: str) -> None:
        for k, pagina in self.paginas.items():
            if k == chave:
                pagina.pack(fill="both", expand=True)
            else:
                pagina.pack_forget()
        for k, item in self.nav.items():
            item.marcar(k == chave)
        if chave == PAG_HIST:
            self.atualizar_historico()
        else:
            self.ent_nome.focus_set()

    @staticmethod
    def _card(pai) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            pai, fg_color=T.CARD, corner_radius=16,
            border_width=1, border_color=T.BORDA,
        )

    @staticmethod
    def _cabecalho(pai, titulo: str, subtitulo: str) -> None:
        quadro = ctk.CTkFrame(pai, fg_color="transparent")
        quadro.pack(fill="x", padx=34, pady=(30, 18))
        ctk.CTkLabel(
            quadro, text=titulo, font=fonte(28, "bold"),
            text_color=T.TEXTO, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            quadro, text=subtitulo, font=fonte(14),
            text_color=T.TEXTO_SUAVE, anchor="w",
        ).pack(anchor="w", pady=(2, 0))

    # ==================================================================
    # Página 1 — Novo registro
    # ==================================================================
    def _criar_pagina_novo(self, pai) -> ctk.CTkFrame:
        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self._cabecalho(
            pagina, "Novo registro",
            "Registre rapidamente uma solicitação de paciente.",
        )

        corpo = ctk.CTkFrame(pagina, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        corpo.grid_columnconfigure(0, weight=3)
        corpo.grid_columnconfigure(1, weight=2, minsize=330)
        corpo.grid_rowconfigure(0, weight=1)

        formulario = self._card(corpo)
        formulario.grid(row=0, column=0, sticky="nsew", padx=(0, 22))
        lateral = ctk.CTkFrame(corpo, fg_color="transparent")
        lateral.grid(row=0, column=1, sticky="nsew")

        self._montar_formulario(formulario)
        self._montar_lateral(lateral)
        return pagina

    # --- Formulário ---------------------------------------------------
    def _montar_formulario(self, card) -> None:
        f = ctk.CTkFrame(card, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=34, pady=28)

        ctk.CTkLabel(
            f, text="Dados da solicitação", font=fonte(20, "bold"),
            text_color=T.TEXTO, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            f, text="Os campos marcados com * são obrigatórios.",
            font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w",
        ).pack(anchor="w", pady=(2, 16))

        # Nome do paciente
        self._rotulo(f, "Nome do paciente *")
        self.ent_nome = self._entrada(f, "Ex.: Maria da Silva")
        self.ent_nome.pack(fill="x", pady=(6, 0))
        self.err_nome = self._rotulo_erro(f)
        self._registrar_campo(self.ent_nome, self.err_nome)

        # Contato
        self._rotulo(f, "Contato (telefone, ramal ou e-mail)")
        self.ent_contato = self._entrada(
            f, "Ex.: (84) 99999-0000  •  Ramal 2045  •  nome@email.com"
        )
        self.ent_contato.pack(fill="x", pady=(6, 0))
        self.err_contato = self._rotulo_erro(f)
        self._registrar_campo(self.ent_contato, self.err_contato)

        # Descrição
        linha = ctk.CTkFrame(f, fg_color="transparent")
        linha.pack(fill="x")
        self._rotulo(linha, "Descrição da solicitação *", lado="left")
        self.lbl_contador = ctk.CTkLabel(
            linha, text=f"0 / {MAX_DESCRICAO}", font=fonte(12),
            text_color=T.TEXTO_SUAVE,
        )
        self.lbl_contador.pack(side="right")

        self.txt_desc = ctk.CTkTextbox(
            f, height=150, font=fonte(15), wrap="word",
            border_width=2, border_color=T.BORDA, corner_radius=10,
            fg_color=T.BRANCO, text_color=T.TEXTO,
        )
        self.txt_desc.pack(fill="both", expand=True, pady=(6, 0))
        self.err_desc = self._rotulo_erro(f)
        self._registrar_campo(self.txt_desc, self.err_desc)
        self.txt_desc.bind("<KeyRelease>", lambda _e: self._atualizar_contador())

        # Botões
        botoes = ctk.CTkFrame(f, fg_color="transparent")
        botoes.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(
            botoes, text="Salvar registro", height=48, width=200, corner_radius=10,
            image=icone("check", T.BRANCO, 20), compound="left",
            font=fonte(16, "bold"), fg_color=T.VERDE, hover_color=T.VERDE_HOVER,
            command=self.salvar_registro,
        ).pack(side="left")
        ctk.CTkButton(
            botoes, text="Limpar campos", height=48, width=160, corner_radius=10,
            font=fonte(15), fg_color="transparent", text_color=T.TEXTO_SUAVE,
            border_width=2, border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
            command=self.limpar_formulario,
        ).pack(side="left", padx=12)
        ctk.CTkLabel(
            botoes, text="Atalho: Ctrl + S", font=fonte(12),
            text_color=T.TEXTO_SUAVE,
        ).pack(side="right")

    @staticmethod
    def _rotulo(pai, texto: str, lado: str = "top") -> None:
        rotulo = ctk.CTkLabel(
            pai, text=texto, font=fonte(14, "bold"),
            text_color=T.TEXTO, anchor="w",
        )
        if lado == "left":
            rotulo.pack(side="left")
        else:
            rotulo.pack(anchor="w")

    @staticmethod
    def _entrada(pai, dica: str) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            pai, height=46, font=fonte(15), placeholder_text=dica,
            placeholder_text_color=T.PLACEHOLDER, corner_radius=10,
            border_width=2, border_color=T.BORDA,
            fg_color=T.BRANCO, text_color=T.TEXTO,
        )

    @staticmethod
    def _rotulo_erro(pai) -> ctk.CTkLabel:
        """Mensagem de erro com altura reservada (o layout não 'pula')."""
        rotulo = ctk.CTkLabel(
            pai, text="", height=22, font=fonte(12, "bold"),
            text_color=T.VERMELHO, anchor="w",
        )
        rotulo.pack(fill="x", pady=(2, 6))
        return rotulo

    # --- Foco, erros e contador ---------------------------------------
    def _registrar_campo(self, campo, rotulo) -> None:
        self._rotulos_erro[campo] = rotulo
        campo.bind("<FocusIn>", lambda _e, c=campo: c.configure(border_color=T.TEAL))
        campo.bind(
            "<FocusOut>",
            lambda _e, c=campo: c.configure(
                border_color=T.VERMELHO if c in self._com_erro else T.BORDA
            ),
        )
        campo.bind("<KeyRelease>", lambda _e, c=campo: self._digitando(c))

    @staticmethod
    def _texto(campo) -> str:
        if isinstance(campo, ctk.CTkTextbox):
            return campo.get("1.0", "end").strip()
        return campo.get().strip()

    def _digitando(self, campo) -> None:
        """Ao digitar num campo com erro, remove o alerta."""
        if campo in self._com_erro and self._texto(campo):
            self._limpar_erro(campo)

    def _marcar_erro(self, campo, mensagem: str) -> None:
        self._com_erro.add(campo)
        campo.configure(border_color=T.VERMELHO)
        self._rotulos_erro[campo].configure(text=mensagem)

    def _limpar_erro(self, campo) -> None:
        self._com_erro.discard(campo)
        campo.configure(border_color=T.TEAL)
        self._rotulos_erro[campo].configure(text="")

    def _limpar_todos_erros(self) -> None:
        for campo in list(self._rotulos_erro):
            self._com_erro.discard(campo)
            campo.configure(border_color=T.BORDA)
            self._rotulos_erro[campo].configure(text="")

    def _atualizar_contador(self) -> None:
        tamanho = len(self._texto(self.txt_desc))
        self.lbl_contador.configure(
            text=f"{tamanho} / {MAX_DESCRICAO}",
            text_color=T.VERMELHO if tamanho > MAX_DESCRICAO else T.TEXTO_SUAVE,
        )
        self._digitando(self.txt_desc)

    def _atalho_salvar(self) -> None:
        if self.paginas[PAG_NOVO].winfo_ismapped():
            self.salvar_registro()

    # --- Ações do formulário ------------------------------------------
    def salvar_registro(self) -> None:
        nome = self._texto(self.ent_nome)
        contato = self._texto(self.ent_contato)
        descricao = self._texto(self.txt_desc)

        self._limpar_todos_erros()
        problemas = []        # (campo, mensagem)
        obrigatorio_vazio = False

        if not nome:
            problemas.append((self.ent_nome, "Informe o nome do paciente."))
            obrigatorio_vazio = True
        elif len(nome) > MAX_NOME:
            problemas.append((self.ent_nome, f"Use no máximo {MAX_NOME} caracteres."))

        if len(contato) > MAX_CONTATO:
            problemas.append((self.ent_contato, f"Use no máximo {MAX_CONTATO} caracteres."))

        if not descricao:
            problemas.append((self.txt_desc, "Descreva a solicitação."))
            obrigatorio_vazio = True
        elif len(descricao) > MAX_DESCRICAO:
            problemas.append(
                (self.txt_desc, f"Use no máximo {MAX_DESCRICAO} caracteres.")
            )

        if problemas:
            for campo, mensagem in problemas:
                self._marcar_erro(campo, mensagem)
            problemas[0][0].focus_set()
            self.toast.mostrar(
                "Preencha os campos obrigatórios." if obrigatorio_vazio
                else "Corrija os campos destacados.",
                "erro",
            )
            return

        try:
            self.db.inserir(nome, contato, descricao)
        except Exception as exc:
            self.toast.mostrar(f"Não foi possível salvar: {exc}", "erro", 6000)
            return

        self.limpar_formulario()
        self.atualizar_tudo()
        self.toast.mostrar("Registro salvo com sucesso.", "sucesso")
        self.ent_nome.focus_set()

    def limpar_formulario(self) -> None:
        self.ent_nome.delete(0, "end")
        self.ent_contato.delete(0, "end")
        self.txt_desc.delete("1.0", "end")
        self._limpar_todos_erros()
        self._atualizar_contador()

    # --- Coluna lateral: resumo e últimos registros -------------------
    def _montar_lateral(self, lateral) -> None:
        resumo = self._card(lateral)
        resumo.pack(fill="x")
        r = ctk.CTkFrame(resumo, fg_color="transparent")
        r.pack(fill="x", padx=26, pady=22)
        ctk.CTkLabel(
            r, text="Resumo", font=fonte(17, "bold"),
            text_color=T.TEXTO, anchor="w",
        ).pack(anchor="w", pady=(0, 10))
        self.res_hoje = self._linha_resumo(r, "Registradas hoje", T.TEAL)
        self.res_pend = self._linha_resumo(r, "Pendentes", T.AMBAR)
        self.res_aten = self._linha_resumo(r, "Atendidas", T.VERDE)

        recentes = self._card(lateral)
        recentes.pack(fill="both", expand=True, pady=(22, 0))
        interno = ctk.CTkFrame(recentes, fg_color="transparent")
        interno.pack(fill="both", expand=True, padx=26, pady=22)
        ctk.CTkLabel(
            interno, text="Últimos registros", font=fonte(17, "bold"),
            text_color=T.TEXTO, anchor="w",
        ).pack(anchor="w", pady=(0, 8))
        self.lista_recentes = ctk.CTkFrame(interno, fg_color="transparent")
        self.lista_recentes.pack(fill="both", expand=True)

    @staticmethod
    def _linha_resumo(pai, texto: str, cor: str) -> ctk.CTkLabel:
        linha = ctk.CTkFrame(pai, fg_color="transparent")
        linha.pack(fill="x", pady=4)
        ctk.CTkFrame(linha, width=10, height=10, corner_radius=5, fg_color=cor).pack(
            side="left", padx=(0, 12)
        )
        ctk.CTkLabel(
            linha, text=texto, font=fonte(14), text_color=T.TEXTO_SUAVE, anchor="w",
        ).pack(side="left")
        numero = ctk.CTkLabel(
            linha, text="0", font=fonte(22, "bold"), text_color=T.TEXTO,
        )
        numero.pack(side="right")
        return numero

    def atualizar_lateral(self) -> None:
        contagem = self.db.contar_por_status()
        self.res_hoje.configure(text=str(self.db.contar_hoje()))
        self.res_pend.configure(text=str(contagem[STATUS_PENDENTE]))
        self.res_aten.configure(text=str(contagem[STATUS_ATENDIDA]))

        for filho in self.lista_recentes.winfo_children():
            filho.destroy()

        registros = self.db.listar(limite=5)
        if not registros:
            ctk.CTkLabel(
                self.lista_recentes, text="Nenhuma solicitação registrada ainda.",
                font=fonte(14), text_color=T.TEXTO_SUAVE, anchor="w",
            ).pack(anchor="w", pady=10)
            return

        for _rid, data_hora, nome, _contato, descricao, status in registros:
            fundo, cor_texto = cores_status(status)
            linha = ctk.CTkFrame(self.lista_recentes, fg_color="transparent")
            linha.pack(fill="x", pady=6)
            ctk.CTkFrame(
                linha, width=10, height=10, corner_radius=5, fg_color=cor_texto
            ).pack(side="left", padx=(0, 12), anchor="n", pady=6)
            textos = ctk.CTkFrame(linha, fg_color="transparent")
            textos.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                textos, text=resumir(nome, 30), font=fonte(14, "bold"),
                text_color=T.TEXTO, anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                textos, text=f"{data_curta(data_hora)}  •  {resumir(descricao, 32)}",
                font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w",
            ).pack(anchor="w")

    # ==================================================================
    # Página 2 — Histórico
    # ==================================================================
    def _criar_pagina_historico(self, pai) -> ctk.CTkFrame:
        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self._cabecalho(
            pagina, "Histórico de registros",
            "Consulte, filtre e atualize as solicitações registradas.",
        )

        # --- Indicadores ---------------------------------------------
        cartoes = ctk.CTkFrame(pagina, fg_color="transparent")
        cartoes.pack(fill="x", padx=34, pady=(0, 18))
        for i in range(3):
            cartoes.grid_columnconfigure(i, weight=1, uniform="cartao")
        self.cartao_total = CartaoNumero(cartoes, "Total de registros", T.TEAL, T.TEAL_CLARO, "list")
        self.cartao_pend = CartaoNumero(cartoes, "Pendentes", T.AMBAR, T.AMBAR_CLARO, "clock")
        self.cartao_aten = CartaoNumero(cartoes, "Atendidas", T.VERDE, T.VERDE_CLARO, "check")
        self.cartao_total.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.cartao_pend.grid(row=0, column=1, sticky="ew", padx=10)
        self.cartao_aten.grid(row=0, column=2, sticky="ew", padx=(10, 0))

        # --- Cartão da tabela ----------------------------------------
        card = self._card(pagina)
        card.pack(fill="both", expand=True, padx=34, pady=(0, 30))

        linha1 = ctk.CTkFrame(card, fg_color="transparent")
        linha1.pack(fill="x", padx=22, pady=(20, 12))
        self.busca = CaixaBusca(linha1, "Buscar por nome ou contato...", self.atualizar_historico)
        self.busca.pack(side="left")
        self.filtro_status = ctk.CTkSegmentedButton(
            linha1, values=list(FILTROS_STATUS), height=40, font=fonte(13, "bold"),
            selected_color=T.TEAL, selected_hover_color=T.TEAL_ESCURO,
            unselected_color=T.TEAL_CLARO, unselected_hover_color=T.TEAL_BORDA,
            text_color=T.TEXTO, fg_color=T.TEAL_CLARO,
            command=lambda _valor: self.atualizar_historico(),
        )
        self.filtro_status.set("Todos")
        self.filtro_status.pack(side="right")

        linha2 = ctk.CTkFrame(card, fg_color="transparent")
        linha2.pack(fill="x", padx=22, pady=(0, 14))
        ctk.CTkButton(
            linha2, text="Marcar como atendida", height=40, corner_radius=10,
            image=icone("check", T.BRANCO, 18), compound="left",
            font=fonte(13, "bold"), fg_color=T.VERDE, hover_color=T.VERDE_HOVER,
            command=lambda: self.alterar_status(STATUS_ATENDIDA),
        ).pack(side="left")
        ctk.CTkButton(
            linha2, text="Marcar como pendente", height=40, corner_radius=10,
            image=icone("clock", T.BRANCO, 18), compound="left",
            font=fonte(13, "bold"), fg_color=T.AMBAR, hover_color=T.AMBAR_HOVER,
            command=lambda: self.alterar_status(STATUS_PENDENTE),
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            linha2, text="Ver detalhes", height=40, corner_radius=10,
            image=icone("eye", T.TEAL, 18), compound="left",
            font=fonte(13, "bold"), fg_color="transparent", text_color=T.TEAL,
            border_width=2, border_color=T.TEAL, hover_color=T.TEAL_CLARO,
            command=self.ver_detalhes,
        ).pack(side="left")
        ctk.CTkButton(
            linha2, text="Excluir", height=40, width=120, corner_radius=10,
            image=icone("trash", T.VERMELHO, 18), compound="left",
            font=fonte(13, "bold"), fg_color="transparent", text_color=T.VERMELHO,
            border_width=2, border_color=T.VERMELHO, hover_color=T.VERMELHO_CLARO,
            command=self.excluir_selecionados,
        ).pack(side="right")

        self._montar_tabela(card)

        rodape = ctk.CTkFrame(card, fg_color="transparent")
        rodape.pack(fill="x", padx=24, pady=(0, 16))
        self.lbl_contagem = ctk.CTkLabel(
            rodape, text="", font=fonte(12, "bold"),
            text_color=T.TEXTO_SUAVE, anchor="w",
        )
        self.lbl_contagem.pack(side="left")
        ctk.CTkLabel(
            rodape,
            text="Duplo clique: ver detalhes   •   Delete: excluir   •   Clique direito: mais opções",
            font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="e",
        ).pack(side="right")
        return pagina

    def _montar_tabela(self, card) -> None:
        corpo = ctk.CTkFrame(card, fg_color=T.BRANCO, corner_radius=0,
                             border_width=1, border_color=T.BORDA)
        corpo.pack(fill="both", expand=True, padx=22, pady=(0, 12))

        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        fator = max(1.0, self.winfo_fpixels("1i") / 96.0)  # escala do Windows (125%, 150%...)
        estilo.configure(
            "Hosp.Treeview", background=T.BRANCO, fieldbackground=T.BRANCO,
            foreground=T.TEXTO, rowheight=int(42 * fator), font=(T.FONTE, 11),
            borderwidth=0,
        )
        estilo.layout("Hosp.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        estilo.configure(
            "Hosp.Treeview.Heading", background=T.NAVY, foreground=T.BRANCO,
            font=(T.FONTE, 11, "bold"), relief="flat", padding=(10, 10),
        )
        estilo.map("Hosp.Treeview.Heading", background=[("active", T.NAVY_ATIVO)])
        # Corrige o Tk 8.6.9 (Python 3.9), onde as cores de 'tag' ignoravam a seleção
        sem_tags = [
            e for e in estilo.map("Hosp.Treeview", query_opt="background")
            if e[:2] != ("!disabled", "!selected")
        ]
        estilo.map(
            "Hosp.Treeview",
            background=[("selected", T.TEAL)] + sem_tags,
            foreground=[("selected", T.BRANCO)],
        )
        estilo.configure(
            "Hosp.Vertical.TScrollbar", background=T.BORDA_FORTE, troughcolor=T.FUNDO,
            bordercolor=T.FUNDO, arrowcolor=T.TEXTO_SUAVE, relief="flat",
        )

        colunas = ("data_hora", "nome", "contato", "descricao", "status")
        self.tabela = ttk.Treeview(
            corpo, columns=colunas, show="headings",
            style="Hosp.Treeview", selectmode="extended",
        )
        cabecalhos = {
            "data_hora": ("Data/Hora", 150),
            "nome": ("Paciente", 210),
            "contato": ("Contato", 170),
            "descricao": ("Descrição", 340),
            "status": ("Status", 110),
        }
        for coluna, (titulo, largura) in cabecalhos.items():
            self.tabela.heading(coluna, text=titulo, anchor="w")
            self.tabela.column(coluna, width=largura, minwidth=90, anchor="w",
                               stretch=(coluna == "descricao"))
        self.tabela.tag_configure("pendente", background=T.AMBAR_CLARO)
        self.tabela.tag_configure("atendida", background=T.VERDE_CLARO)

        barra = ttk.Scrollbar(corpo, orient="vertical", style="Hosp.Vertical.TScrollbar",
                              command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        barra.pack(side="right", fill="y", pady=1, padx=(0, 1))

        # Estado vazio (sobreposto à tabela)
        self.vazio = ctk.CTkFrame(corpo, fg_color=T.BRANCO, corner_radius=0)
        ctk.CTkLabel(self.vazio, text="", image=icone("clipboard", T.BORDA_FORTE, 64)).pack()
        self.lbl_vazio_titulo = ctk.CTkLabel(
            self.vazio, text="", font=fonte(17, "bold"), text_color=T.TEXTO,
        )
        self.lbl_vazio_titulo.pack(pady=(8, 0))
        self.lbl_vazio_texto = ctk.CTkLabel(
            self.vazio, text="", font=fonte(13), text_color=T.TEXTO_SUAVE,
        )
        self.lbl_vazio_texto.pack()

        # Interações
        self.tabela.bind("<<TreeviewSelect>>", lambda _e: self._atualizar_rodape())
        self.tabela.bind("<Double-1>", self._duplo_clique)
        self.tabela.bind("<Return>", lambda _e: self.ver_detalhes())
        self.tabela.bind("<Delete>", lambda _e: self.excluir_selecionados())
        self.tabela.bind("<Button-3>", self._abrir_menu_contexto)

        self.menu_contexto = tk.Menu(self, tearoff=0, font=(T.FONTE, 11))
        self.menu_contexto.add_command(label="Ver detalhes", command=self.ver_detalhes)
        self.menu_contexto.add_separator()
        self.menu_contexto.add_command(
            label="Marcar como atendida",
            command=lambda: self.alterar_status(STATUS_ATENDIDA),
        )
        self.menu_contexto.add_command(
            label="Marcar como pendente",
            command=lambda: self.alterar_status(STATUS_PENDENTE),
        )
        self.menu_contexto.add_separator()
        self.menu_contexto.add_command(label="Excluir", command=self.excluir_selecionados)

    # --- Atualização da tabela e indicadores ---------------------------
    def atualizar_historico(self) -> None:
        if not hasattr(self, "tabela"):
            return  # interface ainda em construção

        selecao_anterior = set(self.tabela.selection())
        self.tabela.delete(*self.tabela.get_children())

        filtro = self.busca.get()
        status = FILTROS_STATUS.get(self.filtro_status.get())
        registros = self.db.listar(filtro, status)

        for rid, data_hora, nome, contato, descricao, st in registros:
            self.tabela.insert(
                "", "end", iid=str(rid),
                tags=("atendida" if st == STATUS_ATENDIDA else "pendente",),
                values=(formatar_data(data_hora), nome, contato,
                        " ".join(descricao.split()), st),
            )

        manter = [i for i in selecao_anterior if self.tabela.exists(i)]
        if manter:
            self.tabela.selection_set(manter)

        self._total_exibido = len(registros)
        if registros:
            self.vazio.place_forget()
        else:
            if filtro or status:
                self.lbl_vazio_titulo.configure(text="Nenhum registro encontrado")
                self.lbl_vazio_texto.configure(text="Tente outro nome, contato ou filtro.")
            else:
                self.lbl_vazio_titulo.configure(text="Nenhuma solicitação registrada ainda")
                self.lbl_vazio_texto.configure(
                    text="Use “Novo registro” no menu para criar a primeira."
                )
            self.vazio.place(relx=0.5, rely=0.5, anchor="center")
            self.vazio.lift()

        contagem = self.db.contar_por_status()
        pend, aten = contagem[STATUS_PENDENTE], contagem[STATUS_ATENDIDA]
        self.cartao_total.definir(pend + aten)
        self.cartao_pend.definir(pend)
        self.cartao_aten.definir(aten)
        self._atualizar_rodape()

    def _atualizar_rodape(self) -> None:
        texto = plural(self._total_exibido, "registro exibido", "registros exibidos")
        selecionados = len(self.tabela.selection())
        if selecionados:
            texto += f"   •   {plural(selecionados, 'selecionado', 'selecionados')}"
        self.lbl_contagem.configure(text=texto)

    def atualizar_tudo(self) -> None:
        self.atualizar_historico()
        self.atualizar_lateral()

    # --- Ações sobre registros ------------------------------------------
    def _ids_selecionados(self) -> list:
        return [int(i) for i in self.tabela.selection()]

    def _definir_status(self, ids: list, novo_status: str) -> None:
        for rid in ids:
            self.db.atualizar_status(rid, novo_status)
        self.atualizar_tudo()
        atendida = novo_status == STATUS_ATENDIDA
        texto = plural(len(ids), "registro marcado", "registros marcados")
        self.toast.mostrar(
            f"{texto} como {'atendido' if atendida else 'pendente'}."
            if len(ids) == 1
            else f"{texto} como {'atendidos' if atendida else 'pendentes'}.",
            "sucesso" if atendida else "aviso",
        )

    def alterar_status(self, novo_status: str) -> None:
        ids = self._ids_selecionados()
        if not ids:
            self.toast.mostrar("Selecione ao menos um registro na tabela.", "aviso")
            return
        self._definir_status(ids, novo_status)

    def excluir_selecionados(self) -> None:
        ids = self._ids_selecionados()
        if not ids:
            self.toast.mostrar("Selecione ao menos um registro para excluir.", "aviso")
            return

        if len(ids) == 1:
            reg = self.db.obter(ids[0])
            destaque = reg[2] if reg else "Registro selecionado"
            titulo = "Excluir solicitação?"
        else:
            destaque = f"{len(ids)} solicitações selecionadas"
            titulo = "Excluir solicitações?"

        confirmou = DialogoConfirmacao.perguntar(
            self, titulo, destaque,
            "Esta ação é definitiva: os dados excluídos não poderão ser recuperados.",
            "Excluir",
        )
        if not confirmou:
            return

        try:
            removidos = self.db.excluir_varios(ids)
        except Exception as exc:
            self.toast.mostrar(f"Não foi possível excluir: {exc}", "erro", 6000)
            return

        self.atualizar_tudo()
        self.toast.mostrar(
            f"{plural(removidos, 'registro excluído', 'registros excluídos')}.", "erro"
        )

    def _duplo_clique(self, evento) -> None:
        iid = self.tabela.identify_row(evento.y)
        if iid:
            self.tabela.selection_set(iid)
            self.ver_detalhes()

    def _abrir_menu_contexto(self, evento) -> None:
        iid = self.tabela.identify_row(evento.y)
        if not iid:
            return
        if iid not in self.tabela.selection():
            self.tabela.selection_set(iid)
        try:
            self.menu_contexto.tk_popup(evento.x_root, evento.y_root)
        finally:
            self.menu_contexto.grab_release()

    # --- Janela de detalhes ---------------------------------------------
    def ver_detalhes(self) -> None:
        ids = self._ids_selecionados()
        if not ids:
            self.toast.mostrar("Selecione um registro para ver os detalhes.", "aviso")
            return
        reg = self.db.obter(ids[0])
        if not reg:
            return
        rid, data_hora, nome, contato, descricao, status = reg

        janela = ctk.CTkToplevel(self, fg_color=T.FUNDO)
        janela.title(f"Solicitação nº {rid}")
        janela.resizable(False, False)
        centralizar(janela, self, 640, 580)

        banda = ctk.CTkFrame(janela, fg_color=T.NAVY, corner_radius=0)
        banda.pack(fill="x")
        interno = ctk.CTkFrame(banda, fg_color="transparent")
        interno.pack(fill="x", padx=28, pady=(22, 20))
        fundo, cor_texto = cores_status(status)
        Pilula(interno, status, fundo, cor_texto).pack(side="right", anchor="n")
        alinhar_esquerda(ctk.CTkLabel(
            interno, text=nome, font=fonte(22, "bold"), text_color=T.BRANCO,
            anchor="w", wraplength=440,
        )).pack(side="left", anchor="w")
        ctk.CTkFrame(janela, fg_color=T.TEAL_ACENTO, height=4, corner_radius=0).pack(fill="x")

        meta = ctk.CTkFrame(janela, fg_color="transparent")
        meta.pack(fill="x", padx=28, pady=(20, 4))
        for i in range(3):
            meta.grid_columnconfigure(i, weight=1, uniform="meta")
        for coluna, (titulo, valor) in enumerate((
            ("DATA E HORA", formatar_data(data_hora)),
            ("CONTATO", contato or "Não informado"),
            ("Nº DO REGISTRO", f"{rid}"),
        )):
            bloco = ctk.CTkFrame(meta, fg_color="transparent")
            bloco.grid(row=0, column=coluna, sticky="w")
            ctk.CTkLabel(bloco, text=titulo, font=fonte(11, "bold"),
                         text_color=T.TEXTO_SUAVE, anchor="w").pack(anchor="w")
            alinhar_esquerda(ctk.CTkLabel(
                bloco, text=valor, font=fonte(14, "bold"), text_color=T.TEXTO,
                anchor="w", wraplength=170,
            )).pack(anchor="w")

        ctk.CTkLabel(
            janela, text="DESCRIÇÃO DA SOLICITAÇÃO", font=fonte(11, "bold"),
            text_color=T.TEXTO_SUAVE, anchor="w",
        ).pack(fill="x", padx=28, pady=(16, 6))
        caixa = ctk.CTkTextbox(
            janela, font=fonte(15), fg_color=T.BRANCO, text_color=T.TEXTO,
            border_width=1, border_color=T.BORDA, corner_radius=10, wrap="word",
        )
        caixa.pack(fill="both", expand=True, padx=28, pady=(0, 16))
        caixa.insert("1.0", descricao)
        caixa.configure(state="disabled")

        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(fill="x", padx=28, pady=(0, 24))
        novo = STATUS_PENDENTE if status == STATUS_ATENDIDA else STATUS_ATENDIDA
        ctk.CTkButton(
            botoes, height=42, corner_radius=10, font=fonte(14, "bold"),
            text="Marcar como pendente" if novo == STATUS_PENDENTE else "Marcar como atendida",
            image=icone("clock" if novo == STATUS_PENDENTE else "check", T.BRANCO, 18),
            compound="left",
            fg_color=T.AMBAR if novo == STATUS_PENDENTE else T.VERDE,
            hover_color=T.AMBAR_HOVER if novo == STATUS_PENDENTE else T.VERDE_HOVER,
            command=lambda: (janela.destroy(), self._definir_status([rid], novo)),
        ).pack(side="left")
        ctk.CTkButton(
            botoes, text="Fechar", width=120, height=42, corner_radius=10,
            font=fonte(14, "bold"), fg_color="transparent", text_color=T.TEXTO,
            border_width=2, border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
            command=janela.destroy,
        ).pack(side="right")

        tornar_modal(janela, self)

    # ==================================================================
    # Utilidades
    # ==================================================================
    def _atualizar_relogio(self) -> None:
        agora = datetime.now()
        self.lbl_hora.configure(text=agora.strftime("%H:%M"))
        self.lbl_data.configure(
            text=f"{DIAS[agora.weekday()]}, {agora.day} de {MESES[agora.month - 1]}"
        )
        self.after(20000, self._atualizar_relogio)

    def abrir_pasta_dados(self) -> None:
        pasta = os.path.dirname(self.db.caminho)
        try:
            if not hasattr(os, "startfile"):
                raise OSError("recurso disponível somente no Windows")
            os.startfile(pasta)
        except Exception:
            self.toast.mostrar(f"Pasta dos dados: {pasta}", "info", 8000)

    def _erro_inesperado(self, exc, valor, tb) -> None:
        """Erros não tratados: grava em erros.log e avisa sem fechar o programa."""
        try:
            pasta = os.path.dirname(self.db.caminho)
            with open(os.path.join(pasta, "erros.log"), "a", encoding="utf-8") as arq:
                arq.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}]\n")
                arq.write("".join(traceback.format_exception(exc, valor, tb)) + "\n")
        except Exception:
            pass
        try:
            self.toast.mostrar(
                "Ocorreu um erro inesperado. Detalhes gravados em erros.log.", "erro", 7000
            )
        except Exception:
            pass
