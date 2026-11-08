"""
nuvem_gui.py
------------
Página "Nuvem" e a rotina de sincronização em segundo plano (veja
sincronizacao.py e nuvem.py).

  - Sincroniza ao abrir, a cada poucos minutos (ou quando há alterações
    pendentes) e ao fechar o programa.
  - A janela nunca trava: a rede roda em outra linha de execução e o
    resultado volta por uma fila.
  - Sem internet o programa segue normal; o que ficou pendente é enviado depois.
"""

import os
import queue
import threading
import time
from datetime import datetime

import customtkinter as ctk

import theme as T
from icons import icone
from nuvem import (ClienteSupabase, NuvemErro, normalizar_url, validar_chave,
                   validar_email)
from nuvem_sql import SQL_CONFIGURACAO
from preferencias import Preferencias
from sincronizacao import sincronizar, testar_conexao
from util import formatar_data, plural
from widgets import DialogoConfirmacao, fonte

INTERVALO_CICLO_MS = 45_000      # verifica pendências a cada 45 s
RENOVAR_A_CADA_S = 300           # puxa novidades da nuvem a cada 5 min
REPETIR_APOS_ERRO_S = 300        # após uma falha, só tenta de novo depois de 5 min
TIMEOUT_AO_FECHAR = 6


class NuvemMixin:
    """Requer: self.db, self.toast, self.after, self.atualizar_tudo, self._card,
    self._cabecalho, self._rotulo, self._entrada."""

    # ==================================================================
    # Estado e configuração
    # ==================================================================
    def _iniciar_nuvem(self) -> None:
        self._nuvem_cfg = Preferencias(
            os.path.join(os.path.dirname(self.db.caminho), "nuvem.json"))
        self._sync_trava = threading.Lock()
        self._sync_fila = queue.Queue()
        self._sync_rodando = False
        self._sync_erro = ""
        self._sync_ultima_tentativa = 0.0
        self._sync_ultimo_ok = 0.0
        if self.nuvem_conectada():
            self.after(2500, lambda: self.sincronizar_nuvem(manual=False))
        self.after(INTERVALO_CICLO_MS, self._ciclo_nuvem)

    def nuvem_conectada(self) -> bool:
        c = self._nuvem_cfg
        return bool(c.get("url") and c.get("chave") and c.get("refresh_token"))

    def _guardar_refresh(self, token: str) -> None:
        self._nuvem_cfg.definir(refresh_token=token)
        self._nuvem_cfg.salvar()

    def _cliente_nuvem(self, timeout: float = 20) -> ClienteSupabase:
        c = self._nuvem_cfg
        return ClienteSupabase(c.get("url"), c.get("chave"), c.get("refresh_token"),
                               ao_renovar=self._guardar_refresh, timeout=timeout)

    # ==================================================================
    # Página
    # ==================================================================
    def _criar_pagina_nuvem(self, pai) -> ctk.CTkFrame:
        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self._cabecalho(
            pagina, "Nuvem",
            "Uma cópia dos registros no Supabase, sincronizada automaticamente.")
        card = self._card(pagina)
        card.pack(fill="both", expand=True, padx=34, pady=(0, 30))

        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.pack(fill="x", padx=24, pady=(22, 4))
        self.lbl_nuvem_estado = ctk.CTkLabel(
            topo, text="", font=fonte(18, "bold"), text_color=T.TEXTO, anchor="w")
        self.lbl_nuvem_estado.pack(anchor="w")
        self.lbl_nuvem_detalhe = ctk.CTkLabel(
            topo, text="", font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w",
            wraplength=760)
        self.lbl_nuvem_detalhe.pack(anchor="w", pady=(2, 0))

        # --- Quando ainda não conectado: formulário -----------------------
        self._grp_nuvem_entrar = ctk.CTkFrame(card, fg_color="transparent")
        grade = ctk.CTkFrame(self._grp_nuvem_entrar, fg_color="transparent")
        grade.pack(fill="x", padx=24, pady=(10, 0))
        grade.grid_columnconfigure((0, 1), weight=1, uniform="nuvem")

        def campo(linha, coluna, texto, dica, ocupa=1, esconder=False):
            ctk.CTkLabel(grade, text=texto, font=fonte(13, "bold"),
                         text_color=T.TEXTO, anchor="w").grid(
                row=linha, column=coluna, columnspan=ocupa, sticky="w",
                padx=(0, 10 if coluna == 0 and ocupa == 1 else 0), pady=(8, 2))
            entrada = self._entrada(grade, dica)
            entrada.configure(height=40, font=fonte(14))
            if esconder:
                entrada.configure(show="•")
            entrada.grid(row=linha + 1, column=coluna, columnspan=ocupa, sticky="ew",
                         padx=(0, 10 if coluna == 0 and ocupa == 1 else 0))
            return entrada

        self.ent_nuvem_url = campo(0, 0, "Endereço do projeto (Project URL)",
                                   "https://xxxxxxxx.supabase.co", ocupa=2)
        self.ent_nuvem_chave = campo(2, 0, "Chave pública (anon / publishable)",
                                     "Cole aqui a chave pública — nunca a secreta", ocupa=2)
        self.ent_nuvem_email = campo(4, 0, "E-mail do usuário", "seu@email.com")
        self.ent_nuvem_senha = campo(4, 1, "Senha", "A senha não fica salva", esconder=True)
        self.ent_nuvem_senha.bind("<Return>", lambda _e: self.conectar_nuvem())
        c = self._nuvem_cfg
        for entrada, valor in ((self.ent_nuvem_url, c.get("url")),
                               (self.ent_nuvem_chave, c.get("chave")),
                               (self.ent_nuvem_email, c.get("email"))):
            if valor:
                entrada.insert(0, valor)

        botoes = ctk.CTkFrame(self._grp_nuvem_entrar, fg_color="transparent")
        botoes.pack(fill="x", padx=24, pady=(16, 0))
        self.btn_nuvem_conectar = ctk.CTkButton(
            botoes, text="Conectar e sincronizar", width=210, height=40, corner_radius=10,
            font=fonte(13, "bold"), fg_color=T.TEAL, hover_color=T.TEAL_ESCURO,
            text_color=T.SOBRE_COR, command=self.conectar_nuvem)
        self.btn_nuvem_conectar.pack(side="left")
        ctk.CTkButton(
            botoes, text="Copiar SQL de configuração", width=230, height=40,
            corner_radius=10, font=fonte(13, "bold"), fg_color="transparent",
            text_color=T.TEAL, border_width=2, border_color=T.TEAL,
            hover_color=T.TEAL_CLARO, command=self.copiar_sql_nuvem,
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            self._grp_nuvem_entrar, font=fonte(12), text_color=T.TEXTO_SUAVE,
            anchor="w", wraplength=780,
            text=("Primeira vez? 1) No Supabase, abra “SQL Editor”, cole o SQL copiado aqui e "
                  "clique em Run.  2) Em “Authentication > Users”, crie um usuário com e-mail "
                  "e senha (marque Auto Confirm User).  3) Em “Project Settings > API”, copie "
                  "a Project URL e a chave anon / publishable."),
        ).pack(anchor="w", padx=24, pady=(14, 0))

        # --- Quando conectado -----------------------------------------------
        self._grp_nuvem_conectado = ctk.CTkFrame(card, fg_color="transparent")
        linha = ctk.CTkFrame(self._grp_nuvem_conectado, fg_color="transparent")
        linha.pack(fill="x", padx=24, pady=(14, 0))
        self.btn_nuvem_sincronizar = ctk.CTkButton(
            linha, text="Sincronizar agora", width=190, height=40, corner_radius=10,
            image=icone("cloud", T.SOBRE_COR, 18), compound="left",
            font=fonte(13, "bold"), fg_color=T.TEAL, hover_color=T.TEAL_ESCURO,
            text_color=T.SOBRE_COR, command=lambda: self.sincronizar_nuvem(manual=True))
        self.btn_nuvem_sincronizar.pack(side="left")
        ctk.CTkButton(
            linha, text="Desconectar", width=140, height=40, corner_radius=10,
            font=fonte(13, "bold"), fg_color="transparent", text_color=T.VERMELHO,
            border_width=2, border_color=T.VERMELHO, hover_color=T.VERMELHO_CLARO,
            command=self.desconectar_nuvem,
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            self._grp_nuvem_conectado, font=fonte(12), text_color=T.TEXTO_SUAVE,
            anchor="w", wraplength=780,
            text=("A sincronização acontece sozinha ao abrir o programa, a cada poucos minutos "
                  "e ao fechar. Sem internet, tudo continua funcionando e o que ficou pendente "
                  "é enviado depois. Os backups locais continuam sendo feitos normalmente."),
        ).pack(anchor="w", padx=24, pady=(14, 0))
        return pagina

    def atualizar_nuvem(self) -> None:
        """Atualiza os textos e mostra o formulário ou os botões, conforme o estado."""
        if not hasattr(self, "lbl_nuvem_estado"):
            return
        try:
            conectada = self.nuvem_conectada()
            if conectada:
                self._grp_nuvem_entrar.pack_forget()
                self._grp_nuvem_conectado.pack(fill="x")
            else:
                self._grp_nuvem_conectado.pack_forget()
                self._grp_nuvem_entrar.pack(fill="x")

            if self._sync_rodando:
                estado, cor = "Sincronizando...", T.TEXTO
                detalhe = "Aguarde um instante."
            elif not conectada:
                estado, cor = "Não conectado", T.TEXTO
                detalhe = ("Hoje os dados ficam só neste computador (com backups locais). "
                           "Conecte para manter uma cópia no Supabase.")
                if self._sync_erro:
                    estado, cor, detalhe = "Não foi possível conectar", T.VERMELHO, self._sync_erro
            elif self._sync_erro:
                estado, cor, detalhe = "Conectado, com um problema", T.AMBAR, self._sync_erro
            else:
                pendentes = self.db.sync_contar_pendentes()
                ultimo = self._nuvem_cfg.get("ultimo_sync")
                partes = [self._nuvem_cfg.get("email") or ""]
                partes.append("Última sincronização: " + (formatar_data(ultimo) if ultimo else "ainda não"))
                if pendentes:
                    partes.append(plural(pendentes, "alteração aguardando envio",
                                         "alterações aguardando envio"))
                estado, cor, detalhe = "Conectado", T.VERDE, "   •   ".join(p for p in partes if p)
            self.lbl_nuvem_estado.configure(text=estado, text_color=cor)
            self.lbl_nuvem_detalhe.configure(text=detalhe)
            ocupado = "disabled" if self._sync_rodando else "normal"
            self.btn_nuvem_conectar.configure(state=ocupado)
            self.btn_nuvem_sincronizar.configure(state=ocupado)
        except Exception:
            pass  # a página pode estar sendo recriada (troca de tema)

    def copiar_sql_nuvem(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(SQL_CONFIGURACAO)
        self.toast.mostrar("SQL copiado. Cole no SQL Editor do Supabase e clique em Run.",
                           "sucesso", 6000)

    # ==================================================================
    # Conectar e desconectar
    # ==================================================================
    def conectar_nuvem(self) -> None:
        if self._sync_rodando:
            return
        try:
            url = normalizar_url(self.ent_nuvem_url.get())
            chave = validar_chave(self.ent_nuvem_chave.get())
            email = validar_email(self.ent_nuvem_email.get())
        except ValueError as exc:
            self.toast.mostrar(str(exc), "erro", 6000)
            return
        senha = self.ent_nuvem_senha.get()
        if not senha:
            self.toast.mostrar("Informe a senha do usuário.", "erro", 5000)
            return
        self._sync_rodando = True
        self._sync_erro = ""
        self.atualizar_nuvem()

        def tarefa():
            try:
                cliente = ClienteSupabase(url, chave)
                cliente.entrar(email, senha)
                testar_conexao(cliente)
                self._sync_fila.put(("conectado", True, (url, chave, email, cliente.refresh_token)))
            except NuvemErro as exc:
                self._sync_fila.put(("falha_conexao", True, str(exc)))
            except Exception as exc:
                self._sync_fila.put(("falha_conexao", True, f"Erro inesperado: {exc}"))

        threading.Thread(target=tarefa, daemon=True).start()
        self.after(300, self._sondar_sync)

    def desconectar_nuvem(self) -> None:
        if not DialogoConfirmacao.perguntar(
                self, "Desconectar da nuvem?", self._nuvem_cfg.get("email") or "Supabase",
                "O programa deixa de sincronizar. Seus registros neste computador não são "
                "alterados. A cópia que já está no Supabase continua lá (apague-a pelo "
                "painel do Supabase, se quiser).",
                "Desconectar", nome_icone="warning", cor=T.VERMELHO,
                cor_hover=T.VERMELHO_HOVER, cor_clara=T.VERMELHO_CLARO):
            return
        with self._sync_trava:
            self._nuvem_cfg.definir(refresh_token=None, ultimo_sync=None)
            self._nuvem_cfg.salvar()
            try:
                self.db.sync_resetar()
            except Exception:
                pass
        self._sync_erro = ""
        self.atualizar_nuvem()
        self.toast.mostrar("Nuvem desconectada.", "info", 4000)

    # ==================================================================
    # Sincronização em segundo plano
    # ==================================================================
    def sincronizar_nuvem(self, manual: bool = False) -> None:
        if not self.nuvem_conectada() or self._sync_rodando:
            return
        self._sync_rodando = True
        self._sync_ultima_tentativa = time.time()
        self.atualizar_nuvem()

        def tarefa():
            with self._sync_trava:
                try:
                    resultado = sincronizar(self.db, self._cliente_nuvem())
                    self._sync_fila.put(("ok", manual, resultado))
                except NuvemErro as exc:
                    self._sync_fila.put(("erro", manual, (str(exc), exc.precisa_login)))
                except Exception as exc:
                    self._sync_fila.put(("erro", manual, (f"Erro inesperado: {exc}", False)))

        threading.Thread(target=tarefa, daemon=True).start()
        self.after(300, self._sondar_sync)

    def _sondar_sync(self) -> None:
        try:
            tipo, manual, dado = self._sync_fila.get_nowait()
        except queue.Empty:
            self.after(300, self._sondar_sync)
            return
        self._sync_rodando = False

        if tipo == "conectado":
            url, chave, email, refresh = dado
            self._nuvem_cfg.definir(url=url, chave=chave, email=email,
                                    refresh_token=refresh, ultimo_sync=None)
            self._nuvem_cfg.salvar()
            self.ent_nuvem_senha.delete(0, "end")
            self.toast.mostrar("Conectado! Enviando seus registros...", "sucesso", 4000)
            self.sincronizar_nuvem(manual=True)
            return

        if tipo == "falha_conexao":
            self._sync_erro = dado
            self.atualizar_nuvem()
            self.toast.mostrar(dado, "erro", 8000)
            return

        if tipo == "erro":
            mensagem, precisa_login = dado
            self._sync_erro = mensagem
            if precisa_login:
                self._nuvem_cfg.definir(refresh_token=None)
                self._nuvem_cfg.salvar()
            self.atualizar_nuvem()
            if manual or precisa_login:
                self.toast.mostrar(mensagem, "erro", 8000)
            return

        # tipo == "ok"
        self._sync_erro = ""
        self._sync_ultimo_ok = time.time()
        self._nuvem_cfg.definir(ultimo_sync=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._nuvem_cfg.salvar()
        if dado.mudou_localmente:
            self.atualizar_tudo()
        self.atualizar_nuvem()
        partes = []
        if dado.enviados:
            partes.append(f"{plural(dado.enviados, 'enviado', 'enviados')}")
        if dado.recebidos:
            partes.append(f"{plural(dado.recebidos, 'recebido', 'recebidos')}")
        if dado.removidos:
            partes.append(f"{plural(dado.removidos, 'removido', 'removidos')}")
        if dado.erros:
            self.toast.mostrar(
                f"{plural(dado.erros, 'registro da nuvem não pôde', 'registros da nuvem não puderam')}"
                " ser aplicados.", "aviso", 7000)
        elif manual:
            self.toast.mostrar("Sincronizado" + (": " + ", ".join(partes) if partes else
                                                 ". Tudo em dia."), "sucesso", 4500)
        elif dado.recebidos or dado.removidos:
            self.toast.mostrar("Novidades recebidas da nuvem: " + ", ".join(partes),
                               "info", 4500)

    def _ciclo_nuvem(self) -> None:
        """Envia alterações pendentes e, de tempos em tempos, busca novidades."""
        try:
            if self.nuvem_conectada() and not self._sync_rodando:
                agora = time.time()
                esperou_erro = agora - self._sync_ultima_tentativa >= REPETIR_APOS_ERRO_S
                if self._sync_erro:
                    devido = esperou_erro
                else:
                    devido = (self.db.sync_contar_pendentes() > 0
                              or agora - max(self._sync_ultimo_ok,
                                             self._sync_ultima_tentativa) >= RENOVAR_A_CADA_S)
                if devido:
                    self.sincronizar_nuvem(manual=False)
        except Exception:
            pass
        self.after(INTERVALO_CICLO_MS, self._ciclo_nuvem)

    def _sincronizar_ao_fechar(self) -> None:
        """Última tentativa de envio ao fechar (curta, para não demorar)."""
        try:
            if not self.nuvem_conectada() or self.db.sync_contar_pendentes() == 0:
                return
            if not self._sync_trava.acquire(timeout=TIMEOUT_AO_FECHAR + 2):
                return
            try:
                sincronizar(self.db, self._cliente_nuvem(TIMEOUT_AO_FECHAR))
            finally:
                self._sync_trava.release()
        except Exception:
            pass  # o que não foi enviado segue pendente para a próxima vez
