"""
pausas.py
---------
Alertas de pausa do dia: 14:40 (NR 17), 17:00 (lanche) e 18:10 (NR 17).
Os horários e a regra de "já avisei hoje" ficam em nucleo/pausas.py.

  - A checagem roda no próprio laço do Tk (`after`, a cada segundo): é só
    uma comparação de horário, não trava a janela e dispensa thread (o Tk não
    pode ser usado fora da thread principal).
  - O aviso é uma janelinha sem bloqueio (a pessoa pode terminar o que está
    fazendo), sempre à frente das outras e com sinal sonoro.
  - Liga/desliga pelo botão de sino do relógio (menu lateral) ou Ctrl + L; a
    escolha fica salva em preferencias.json (chave "alertas_pausa").
"""

from datetime import datetime

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.icons import icone
from anotacoes.interface.widgets import alinhar_esquerda, centralizar, fonte
from anotacoes.nucleo.pausas import marcar_avisada, pausa_devida

INTERVALO_MS = 1000          # com 1 s o aviso sai em HH:MM:00 (no máximo 1 s depois)
BIPES = 3                    # quantas vezes o sinal sonoro se repete
INTERVALO_BIPES_MS = 700


def _tocar_sinal(janela) -> None:
    """Sinal sonoro do sistema (Windows); em outros sistemas, o bip do Tk."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        try:
            janela.bell()
        except Exception:
            pass


class DialogoPausa(ctk.CTkToplevel):
    """Aviso de pausa. Não é modal e não depende da janela principal estar visível."""

    def __init__(self, pai, pausa) -> None:
        super().__init__(pai, fg_color=T.CARD)
        lanche = pausa.tipo == "lanche"
        cor = T.AMBAR if lanche else T.TEAL
        cor_hover = T.AMBAR_HOVER if lanche else T.TEAL_ESCURO
        cor_clara = T.AMBAR_CLARO if lanche else T.TEAL_CLARO

        self.title(pausa.titulo)
        self.resizable(False, False)
        centralizar(self, pai, 460, 280)
        # Sem `transient`: no Windows, uma janela filha de outra minimizada
        # fica escondida, e o aviso precisa aparecer mesmo assim.
        self.attributes("-topmost", True)

        ctk.CTkFrame(self, fg_color=cor, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=30, pady=(24, 8))

        topo = ctk.CTkFrame(corpo, fg_color="transparent")
        topo.pack(fill="x")
        circulo = ctk.CTkFrame(topo, width=56, height=56, corner_radius=28, fg_color=cor_clara)
        circulo.pack(side="left")
        circulo.pack_propagate(False)
        ctk.CTkLabel(circulo, text="", image=icone("clock", cor, 28)).place(
            relx=0.5, rely=0.5, anchor="center")
        textos = ctk.CTkFrame(topo, fg_color="transparent")
        textos.pack(side="left", padx=(16, 0), fill="x", expand=True)
        ctk.CTkLabel(textos, text=pausa.titulo, font=fonte(19, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(textos, text=pausa.rotulo, font=fonte(14, "bold"),
                     text_color=cor, anchor="w").pack(anchor="w")

        alinhar_esquerda(ctk.CTkLabel(
            corpo, text=pausa.mensagem, font=fonte(14), text_color=T.TEXTO_SUAVE,
            anchor="w", wraplength=390)).pack(anchor="w", pady=(18, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=30, pady=(8, 24))
        self._ok = ctk.CTkButton(
            botoes, text="Ok, vou pausar", width=150, height=42, font=fonte(14, "bold"),
            fg_color=cor, hover_color=cor_hover, text_color=T.SOBRE_COR,
            command=self.destroy)
        self._ok.pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self.destroy())
        self._trazer_para_frente()

    def _trazer_para_frente(self) -> None:
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass


class PausasMixin:
    """Requer: self.prefs, self.toast, self.after, self._rodape_relogio."""

    # ==================================================================
    # Laço de verificação
    # ==================================================================
    def _iniciar_pausas(self) -> None:
        self._pausas_avisadas = set()   # (data, "HH:MM") já avisados
        self._dialogo_pausa = None
        self.after(INTERVALO_MS, self._ciclo_pausas)

    def _ciclo_pausas(self) -> None:
        try:
            if self.prefs.alertas_pausa:
                agora = datetime.now()
                pausa = pausa_devida(agora, self._pausas_avisadas)
                if pausa is not None:
                    # Marca antes de mostrar: se algo falhar, não repete a cada segundo.
                    marcar_avisada(self._pausas_avisadas, pausa, agora.date())
                    self._avisar_pausa(pausa)
        except Exception:
            pass   # um problema aqui nunca pode parar o laço nem a janela principal
        self.after(INTERVALO_MS, self._ciclo_pausas)

    def _avisar_pausa(self, pausa) -> None:
        anterior = self._dialogo_pausa
        if anterior is not None:
            try:
                anterior.destroy()
            except Exception:
                pass
        try:
            self._dialogo_pausa = DialogoPausa(self, pausa)
        except Exception:
            self._dialogo_pausa = None
            self.toast.mostrar(f"{pausa.rotulo} — {pausa.titulo}", "aviso", 15000)
        self._bipar(BIPES)

    def _bipar(self, restantes: int) -> None:
        if restantes <= 0:
            return
        _tocar_sinal(self)
        self.after(INTERVALO_BIPES_MS, lambda: self._bipar(restantes - 1))

    # ==================================================================
    # Liga / desliga
    # ==================================================================
    def _montar_botao_pausas(self, pai) -> None:
        """Botão de sino no canto do cartão do relógio (refeito junto com a barra lateral)."""
        self._btn_pausas = ctk.CTkButton(
            pai, text="", width=38, height=30, fg_color="transparent",
            border_width=1, border_color=T.NAV_LINHA, hover_color=T.NAVY_ATIVO,
            command=self.alternar_alertas_pausa)
        self._btn_pausas.place(relx=1.0, rely=0.5, anchor="e", x=-14)
        self._atualizar_botao_pausas()

    def _atualizar_botao_pausas(self) -> None:
        botao = getattr(self, "_btn_pausas", None)
        if botao is None:
            return
        ativo = self.prefs.alertas_pausa
        botao.configure(image=icone("bell" if ativo else "bell_off", T.NAV_TEXTO, 18))

    def alternar_alertas_pausa(self) -> None:
        self.prefs.alertas_pausa = not self.prefs.alertas_pausa
        self.prefs.salvar()
        self._atualizar_botao_pausas()
        if self.prefs.alertas_pausa:
            self.toast.mostrar("Alertas de pausa ativados (14:40, 17:00 e 18:10).", "sucesso", 3500)
        else:
            self.toast.mostrar("Alertas de pausa desativados.", "aviso", 3500)
