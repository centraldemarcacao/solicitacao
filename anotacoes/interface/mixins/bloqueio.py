"""
bloqueio.py
-----------
Proteção por PIN: tela de bloqueio, bloqueio automático por inatividade e as janelas
para criar, alterar e remover o PIN. A regra (hash, criptografia) fica em
nucleo/seguranca.py; leia a nota lá sobre o que isto protege e o que não protege.

  - A tela de bloqueio é um painel que cobre a janela inteira. Enquanto ela existe,
    atalhos de teclado ficam desligados (veja AtalhosMixin) e janelas abertas
    (detalhes, edição...) ficam escondidas.
  - Os alertas de pausa continuam funcionando com o programa bloqueado.
  - Com a criptografia ligada, a senha informada ao desbloquear fica só na memória e é
    usada para gravar os backups (os automáticos esperam o desbloqueio).
"""

import os
import time
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.icons import icone
from anotacoes.interface.widgets import alinhar_esquerda, centralizar, fonte
from anotacoes.nucleo import seguranca
from anotacoes.nucleo.identidade import titulo_completo

INTERVALO_OCIOSIDADE_MS = 10_000


def _campo(pai, rotulo: str) -> ctk.CTkEntry:
    ctk.CTkLabel(pai, text=rotulo, font=fonte(13, "bold"), text_color=T.TEXTO,
                 anchor="w").pack(anchor="w", pady=(10, 4))
    entrada = ctk.CTkEntry(pai, height=42, font=fonte(15), show="•", fg_color=T.SUPERFICIE,
                           border_color=T.BORDA_FORTE, text_color=T.TEXTO)
    entrada.pack(fill="x")
    return entrada


class DialogoPin(ctk.CTkToplevel):
    """Criar, alterar ou remover o PIN. Não é modal (um aviso de pausa pode chegar).

    modo: "criar" | "alterar" | "desativar". `verificar(texto)` confere a senha atual.
    `ao_confirmar(dados)` recebe {"atual", "novo", "criptografar"} e devolve None ou uma
    mensagem de erro (a janela só fecha se for None)."""

    TITULOS = {"criar": "Ativar o PIN", "alterar": "Alterar o PIN", "desativar": "Remover o PIN"}

    def __init__(self, pai, modo: str, verificar, ao_confirmar, criptografar_padrao: bool = True) -> None:
        super().__init__(pai, fg_color=T.CARD)
        self.modo, self._verificar, self._ao_confirmar = modo, verificar, ao_confirmar
        self.title(self.TITULOS[modo])
        self.resizable(False, False)
        centralizar(self, pai, 470, {"criar": 520, "alterar": 520, "desativar": 330}[modo])
        self.transient(pai)

        ctk.CTkFrame(self, fg_color=T.TEAL, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=30, pady=(20, 0))
        ctk.CTkLabel(corpo, text=self.TITULOS[modo], font=fonte(19, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w")
        textos = {
            "criar": f"Escolha um PIN ou senha ({seguranca.MIN_CARACTERES} a "
                     f"{seguranca.MAX_CARACTERES} caracteres). Ele será pedido ao abrir o "
                     "programa e depois de um tempo sem uso. Anote-o em local seguro: "
                     "não há como recuperá-lo.",
            "alterar": "Os backups criptografados antigos continuam exigindo a senha com que "
                       "foram criados; os novos usarão a nova senha.",
            "desativar": "O programa deixa de pedir PIN. Os backups já criptografados continuam "
                         "exigindo a senha antiga para serem restaurados.",
        }
        alinhar_esquerda(ctk.CTkLabel(corpo, text=textos[modo], font=fonte(13),
                                      text_color=T.TEXTO_SUAVE, anchor="w",
                                      wraplength=400)).pack(anchor="w", pady=(4, 4))

        self.ent_atual = _campo(corpo, "PIN ou senha atual") if modo in ("alterar", "desativar") else None
        self.ent_novo = self.ent_confirma = self.chk_cripto = None
        if modo in ("criar", "alterar"):
            self.ent_novo = _campo(corpo, "Novo PIN ou senha")
            self.ent_confirma = _campo(corpo, "Repita o novo PIN ou senha")
        if modo == "criar":
            disponivel = seguranca.criptografia_disponivel()
            self.chk_cripto = ctk.CTkCheckBox(
                corpo, text="Criptografar os backups com esta senha" if disponivel
                else "Criptografia indisponível neste computador",
                font=fonte(13), text_color=T.TEXTO, fg_color=T.TEAL, hover_color=T.TEAL_ESCURO,
                border_color=T.BORDA_FORTE, checkmark_color=T.SOBRE_COR,
                state="normal" if disponivel else "disabled")
            (self.chk_cripto.select if disponivel and criptografar_padrao else self.chk_cripto.deselect)()
            self.chk_cripto.pack(anchor="w", pady=(14, 0))

        self.lbl_erro = ctk.CTkLabel(corpo, text="", font=fonte(13, "bold"),
                                     text_color=T.VERMELHO, anchor="w", wraplength=400)
        self.lbl_erro.pack(anchor="w", pady=(10, 0))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=30, pady=(8, 22))
        ctk.CTkButton(botoes, text="Confirmar", width=120, height=42, font=fonte(14, "bold"),
                      fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
                      command=self._confirmar).pack(side="right")
        ctk.CTkButton(botoes, text="Cancelar", width=110, height=42, font=fonte(14, "bold"),
                      fg_color="transparent", text_color=T.TEXTO, border_width=2,
                      border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
                      command=self.destroy).pack(side="right", padx=(0, 10))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._confirmar())
        primeiro = self.ent_atual or self.ent_novo
        self.after(150, lambda: (self.lift(), self.focus_force(), primeiro.focus_set()))

    def _confirmar(self) -> None:
        dados = {"atual": self.ent_atual.get() if self.ent_atual else "",
                 "novo": self.ent_novo.get() if self.ent_novo else "",
                 "criptografar": bool(self.chk_cripto.get()) if self.chk_cripto else False}
        erro = None
        if self.ent_atual is not None and not self._verificar(dados["atual"]):
            erro = "O PIN ou senha atual está incorreto."
        elif self.ent_novo is not None:
            erro = seguranca.validar_segredo(dados["novo"])
            if erro is None and dados["novo"] != self.ent_confirma.get():
                erro = "Os dois campos novos não são iguais."
        if erro is None:
            erro = self._ao_confirmar(dados)
        self.lbl_erro.configure(text=erro or "")
        if erro is None:
            self.destroy()


class DialogoSenhaBackup(ctk.CTkToplevel):
    """Pede a senha de um backup criptografado com outra senha. Use `perguntar`."""

    def __init__(self, pai, nome_arquivo: str) -> None:
        super().__init__(pai, fg_color=T.CARD)
        self.resultado: Optional[str] = None
        self.title("Senha do backup")
        self.resizable(False, False)
        centralizar(self, pai, 460, 300)
        ctk.CTkFrame(self, fg_color=T.TEAL, height=6, corner_radius=0).pack(fill="x")
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=30, pady=(20, 0))
        ctk.CTkLabel(corpo, text="Senha deste backup", font=fonte(19, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w")
        alinhar_esquerda(ctk.CTkLabel(
            corpo, text=f"{nome_arquivo}\nA senha atual não abre este backup. Informe a senha "
                        "usada quando ele foi criado.",
            font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=400,
        )).pack(anchor="w", pady=(4, 4))
        self.entrada = _campo(corpo, "Senha")
        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=30, pady=(14, 22))
        ctk.CTkButton(botoes, text="Restaurar", width=120, height=42, font=fonte(14, "bold"),
                      fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
                      command=self._ok).pack(side="right")
        ctk.CTkButton(botoes, text="Cancelar", width=110, height=42, font=fonte(14, "bold"),
                      fg_color="transparent", text_color=T.TEXTO, border_width=2,
                      border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
                      command=self.destroy).pack(side="right", padx=(0, 10))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._ok())
        self.transient(pai)
        self.after(150, lambda: (self.grab_set(), self.entrada.focus_set()))

    def _ok(self) -> None:
        self.resultado = self.entrada.get() or None
        self.destroy()

    @classmethod
    def perguntar(cls, pai, nome_arquivo: str) -> Optional[str]:
        dialogo = cls(pai, nome_arquivo)
        pai.wait_window(dialogo)
        return dialogo.resultado


class BloqueioMixin:
    """Requer: self.db, self.prefs, self.toast, self.after, self._ao_fechar, self.bind_all."""

    # ==================================================================
    # Início
    # ==================================================================
    def _iniciar_seguranca(self) -> None:
        """Lê a configuração e prepara os backups. Chamar ANTES do backup de abertura."""
        self.seguranca = seguranca.Seguranca(
            os.path.join(os.path.dirname(self.db.caminho), seguranca.NOME_ARQUIVO))
        self._bloqueado = False
        self._painel_bloqueio = None
        self._janelas_ocultas = []
        self._limite_pin = seguranca.LimiteTentativas()
        self.db.backup_criptografado = self.seguranca.criptografar_backups

    def _iniciar_bloqueio(self) -> None:
        """Ativa o bloqueio por inatividade e, se há PIN, já abre bloqueado. Chamar depois
        de a interface estar montada."""
        self._ultima_atividade = time.monotonic()
        for evento in ("<Motion>", "<Key>", "<ButtonPress>", "<MouseWheel>"):
            self.bind_all(evento, self._registrar_atividade, add="+")
        self.after(INTERVALO_OCIOSIDADE_MS, self._ciclo_bloqueio)
        if self.seguranca.ativa:
            self.bloquear()

    def _registrar_atividade(self, _evento=None) -> None:
        self._ultima_atividade = time.monotonic()

    def _ciclo_bloqueio(self) -> None:
        try:
            if (self.seguranca.ativa and not self._bloqueado
                    and time.monotonic() - self._ultima_atividade
                    >= self.seguranca.bloqueio_minutos * 60):
                self.bloquear()
        except Exception:
            pass
        self.after(INTERVALO_OCIOSIDADE_MS, self._ciclo_bloqueio)

    def esta_bloqueado(self) -> bool:
        return bool(getattr(self, "_bloqueado", False))

    # ==================================================================
    # Tela de bloqueio
    # ==================================================================
    def bloquear(self) -> None:
        if not self.seguranca.ativa or self._bloqueado:
            return
        self._bloqueado = True
        self._esconder_janelas()
        painel = ctk.CTkFrame(self, fg_color=T.FUNDO, corner_radius=0)
        painel.place(x=0, y=0, relwidth=1, relheight=1)
        painel.lift()
        self._painel_bloqueio = painel

        caixa = ctk.CTkFrame(painel, fg_color=T.CARD, corner_radius=18,
                             border_width=1, border_color=T.BORDA)
        caixa.place(relx=0.5, rely=0.5, anchor="center")
        miolo = ctk.CTkFrame(caixa, fg_color="transparent")
        miolo.pack(padx=44, pady=36)
        ctk.CTkLabel(miolo, text="", image=icone("logo", T.BRANCO, 56)).pack()
        ctk.CTkLabel(miolo, text="Programa bloqueado", font=fonte(22, "bold"),
                     text_color=T.TEXTO).pack(pady=(14, 2))
        ctk.CTkLabel(miolo, text=titulo_completo(), font=fonte(13),
                     text_color=T.TEXTO_SUAVE, wraplength=300).pack()
        self._ent_pin = ctk.CTkEntry(
            miolo, width=300, height=46, font=fonte(16), show="•",
            placeholder_text="PIN ou senha", placeholder_text_color=T.PLACEHOLDER,
            fg_color=T.SUPERFICIE, border_color=T.BORDA_FORTE, text_color=T.TEXTO)
        self._ent_pin.pack(pady=(22, 0))
        self._lbl_pin_erro = ctk.CTkLabel(miolo, text="", height=22, font=fonte(13, "bold"),
                                          text_color=T.VERMELHO, wraplength=300)
        self._lbl_pin_erro.pack(pady=(6, 6))
        self._btn_entrar = ctk.CTkButton(
            miolo, text="Entrar", width=300, height=44, font=fonte(15, "bold"),
            fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
            command=self._tentar_desbloquear)
        self._btn_entrar.pack()
        ctk.CTkButton(miolo, text="Fechar o programa", width=300, height=34,
                      font=fonte(13), fg_color="transparent", text_color=T.TEXTO_SUAVE,
                      hover_color=T.FUNDO, command=self._ao_fechar).pack(pady=(10, 0))
        self._ent_pin.bind("<Return>", lambda _e: self._tentar_desbloquear())
        self._ent_pin.bind("<FocusOut>", lambda _e: self.after(50, self._refocar_pin))
        self.after(120, self._refocar_pin)

    def _refocar_pin(self) -> None:
        if self._bloqueado and getattr(self, "_ent_pin", None) is not None:
            try:
                self._ent_pin.focus_set()
            except Exception:
                pass

    def _esconder_janelas(self) -> None:
        """Esconde diálogos abertos (detalhes, edição...) enquanto bloqueado. O aviso de
        pausa fica: não mostra dados e precisa continuar clicável."""
        self._janelas_ocultas = []
        for filho in list(self.winfo_children()):
            if (isinstance(filho, (ctk.CTkToplevel, tk.Toplevel))
                    and filho is not getattr(self, "_dialogo_pausa", None)):
                try:
                    filho.withdraw()
                    self._janelas_ocultas.append(filho)
                except Exception:
                    pass

    def _tentar_desbloquear(self) -> None:
        espera = self._limite_pin.segundos_restantes()
        if espera:
            self._lbl_pin_erro.configure(text=f"Aguarde {espera} s para tentar de novo.")
            return
        texto = self._ent_pin.get()
        if self.seguranca.verificar(texto):
            self._limite_pin.acertou()
            self._desbloquear(texto)
            return
        self._limite_pin.errou()
        espera = self._limite_pin.segundos_restantes()
        self._ent_pin.delete(0, "end")
        self._lbl_pin_erro.configure(
            text="PIN ou senha incorretos." + (f" Aguarde {espera} s." if espera else ""))
        self._refocar_pin()

    def _desbloquear(self, segredo: str) -> None:
        if self.seguranca.criptografar_backups:
            self.db.backup_segredo = segredo          # só na memória
            try:
                self.db.backup_automatico()           # o de abertura foi adiado
            except Exception:
                pass
        painel, self._painel_bloqueio = self._painel_bloqueio, None
        self._bloqueado = False
        self._ent_pin = None
        if painel is not None:
            painel.destroy()
        for janela in self._janelas_ocultas:
            try:
                janela.deiconify()
            except Exception:
                pass
        self._janelas_ocultas = []
        self._registrar_atividade()

    # ==================================================================
    # Configuração do PIN (usada pela página Configurações)
    # ==================================================================
    def abrir_dialogo_pin(self, modo: str) -> None:
        DialogoPin(self, modo, self.seguranca.verificar, lambda dados: self._aplicar_pin(modo, dados),
                   criptografar_padrao=self.seguranca.criptografar_backups
                   or not self.seguranca.ativa)

    def _aplicar_pin(self, modo: str, dados: dict) -> Optional[str]:
        """Devolve None se deu certo ou a mensagem de erro para a janela."""
        try:
            if modo == "desativar":
                if not self.seguranca.desativar():
                    return "Não foi possível gravar a configuração (pasta sem permissão?)."
                self.db.backup_criptografado = False
                self.db.backup_segredo = None
                self.toast.mostrar("PIN removido. Backups antigos criptografados ainda exigem "
                                   "a senha anterior.", "aviso", 7000)
            else:
                criptografar = (dados["criptografar"] if modo == "criar"
                                else self.seguranca.criptografar_backups)
                if not self.seguranca.ativar(dados["novo"], criptografar):
                    return "Não foi possível gravar a configuração (pasta sem permissão?)."
                self.db.backup_segredo = dados["novo"]
                self.db.backup_criptografado = self.seguranca.criptografar_backups
                convertidos = self._criptografar_backups_agora()
                extra = f" {convertidos} backup(s) antigo(s) criptografado(s)." if convertidos else ""
                self.toast.mostrar(("PIN ativado." if modo == "criar" else "PIN alterado.") + extra,
                                   "sucesso", 6000)
        except Exception as exc:
            return f"Não foi possível concluir: {exc}"
        self._ultima_atividade = time.monotonic()
        self.atualizar_config()
        return None

    def _criptografar_backups_agora(self) -> int:
        """Converte os backups antigos (texto aberto) e refaz o do dia. Retorna quantos."""
        if not self.db.backup_criptografado or not self.db.backup_segredo:
            return 0
        convertidos = self.db.criptografar_backups_existentes()
        try:
            self.db.backup_automatico(sobrescrever=True)
        except Exception:
            pass
        return convertidos

    def alternar_criptografia_backups(self, ativo: bool) -> None:
        if not self.seguranca.ativa:
            return
        if ativo and not self.db.backup_segredo:
            self.toast.mostrar("Desbloqueie o programa com o PIN para ligar a criptografia.", "aviso")
            self.atualizar_config()
            return
        self.seguranca.definir_criptografar_backups(ativo)
        self.db.backup_criptografado = self.seguranca.criptografar_backups
        if ativo and not self.db.backup_criptografado:
            self.toast.mostrar("A criptografia não está disponível neste computador.", "erro", 6000)
        elif ativo:
            convertidos = self._criptografar_backups_agora()
            self.toast.mostrar(f"Backups criptografados ({convertidos} antigo(s) convertido(s)).",
                               "sucesso", 5000)
        else:
            self.toast.mostrar("Novos backups sairão sem criptografia. Os já criptografados "
                               "continuam exigindo a senha.", "aviso", 7000)
        self.atualizar_config()

    def definir_bloqueio_minutos(self, minutos: int) -> None:
        self.seguranca.definir_bloqueio_minutos(minutos)
        self._registrar_atividade()
