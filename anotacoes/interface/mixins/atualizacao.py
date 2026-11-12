"""
atualizacao.py
--------------
Parte da interface responsável pela atualização automática (veja anotacoes/atualizacao/updater.py).

A consulta e o download rodam em segundo plano; a janela nunca trava.
Falhas de rede na verificação automática são silenciosas (rede institucional
pode bloquear o GitHub); na verificação manual, o motivo é mostrado.
"""

import os
import queue
import sys
import threading

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.atualizacao import updater
from anotacoes.interface.widgets import DialogoConfirmacao, centralizar, fonte, tornar_modal


class AtualizacaoMixin:
    """Requer: self.db, self.toast, self.after, self.destroy."""

    def _iniciar_atualizacao(self) -> None:
        self._fila_atualizacao = queue.Queue()
        self._atualizando = False
        self._cancelar_download = threading.Event()
        try:
            updater.limpar_restos()
        except Exception:
            pass
        if updater.ficou_pendente():
            self.after(2500, lambda: self.toast.mostrar(
                "A última atualização não foi aplicada. Baixe o .exe em Releases e copie por "
                "cima do atual (veja atualizacao.log).", "aviso", 12000))
        if T.REPOSITORIO_GITHUB:
            self.after(4000, lambda: self._verificar_atualizacao(manual=False))

    # --- Verificação ----------------------------------------------------
    def verificar_atualizacao_manual(self) -> None:
        if not T.REPOSITORIO_GITHUB:
            self.toast.mostrar("Atualização automática não configurada (anotacoes/theme.py).", "aviso", 6000)
            return
        self.toast.mostrar("Verificando atualizações...", "aviso", 2500)
        self._verificar_atualizacao(manual=True)

    def _verificar_atualizacao(self, manual: bool) -> None:
        if self._atualizando:
            return
        self._atualizando = True

        def tarefa():
            try:
                self._fila_atualizacao.put(("info", manual, updater.buscar_ultima(T.REPOSITORIO_GITHUB)))
            except Exception as exc:
                self._fila_atualizacao.put(("erro", manual, str(exc)))

        threading.Thread(target=tarefa, daemon=True).start()
        self.after(250, self._sondar_fila)

    def _sondar_fila(self) -> None:
        try:
            tipo, manual, dado = self._fila_atualizacao.get_nowait()
        except queue.Empty:
            self.after(250, self._sondar_fila)
            return
        self._atualizando = False
        if tipo == "erro":
            if manual:
                self.toast.mostrar(f"Não foi possível verificar: {dado}", "erro", 7000)
        elif dado is None or not updater.e_mais_nova(dado.versao, T.VERSAO):
            if manual:
                self.toast.mostrar(f"Você já está na versão mais recente (v{T.VERSAO}).", "sucesso")
        else:
            self._oferecer_atualizacao(dado)

    # --- Oferta e download ----------------------------------------------
    def _oferecer_atualizacao(self, info) -> None:
        if not updater.pode_atualizar_sozinho():
            self.toast.mostrar(
                f"Versão {info.versao} disponível, mas este programa não pode se "
                "atualizar sozinho (execute o .exe em uma pasta com permissão de gravação).",
                "aviso", 9000)
            return
        notas = " ".join(info.notas.split())[:220]
        mensagem = (f"Você usa a versão {T.VERSAO}. "
                    + (f"Novidades: {notas} " if notas else "")
                    + "Seus registros não serão alterados e um backup é feito antes.")
        if not DialogoConfirmacao.perguntar(
                self, "Atualização disponível", f"Versão {info.versao}", mensagem,
                "Atualizar agora", nome_icone="restore", cor=T.TEAL,
                cor_hover=T.TEAL_ESCURO, cor_clara=T.TEAL_CLARO):
            return
        self._baixar_e_aplicar(info)

    def _baixar_e_aplicar(self, info) -> None:
        self._cancelar_download.clear()
        janela = ctk.CTkToplevel(self, fg_color=T.FUNDO)
        janela.title("Atualizando")
        janela.resizable(False, False)
        centralizar(janela, self, 440, 190)
        ctk.CTkLabel(janela, text=f"Baixando a versão {info.versao}...",
                     font=fonte(16, "bold"), text_color=T.TEXTO).pack(pady=(28, 14))
        barra = ctk.CTkProgressBar(janela, width=360, progress_color=T.TEAL)
        barra.set(0)
        barra.pack()
        ctk.CTkButton(janela, text="Cancelar", width=110, height=36, font=fonte(13, "bold"),
                      fg_color="transparent", text_color=T.TEXTO, border_width=2,
                      border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
                      command=self._cancelar_download.set).pack(pady=(20, 0))
        tornar_modal(janela, self)

        pasta = os.path.dirname(sys.executable)
        fila = queue.Queue()

        def tarefa():
            try:
                caminho = updater.baixar(
                    info, pasta, progresso=lambda p: fila.put(("p", p)),
                    cancelar=self._cancelar_download)
                fila.put(("ok", caminho))
            except Exception as exc:
                fila.put(("erro", str(exc)))

        def sondar():
            final = None
            try:
                while True:
                    tipo, dado = fila.get_nowait()
                    if tipo == "p":
                        barra.set(dado)
                    else:
                        final = (tipo, dado)
                        break
            except queue.Empty:
                pass
            if final is None:
                self.after(150, sondar)
                return
            janela.destroy()
            if final[0] == "erro":
                self.toast.mostrar(f"Atualização não concluída: {final[1]}", "erro", 8000)
            else:
                self._finalizar_atualizacao(final[1])

        threading.Thread(target=tarefa, daemon=True).start()
        self.after(150, sondar)

    def _finalizar_atualizacao(self, novo: str) -> None:
        try:
            self.db.backup_automatico(sobrescrever=True)
        except Exception:
            pass
        try:
            resultado = updater.executar_troca(novo)
        except Exception as exc:
            self.toast.mostrar(f"Não foi possível aplicar a atualização: {exc}", "erro", 8000)
            return
        if resultado == "manual":
            self.toast.mostrar("Atualização aplicada. Feche o programa e abra-o novamente.",
                               "sucesso", 10000)
            return
        self.destroy()
