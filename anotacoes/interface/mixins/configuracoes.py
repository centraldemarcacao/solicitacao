"""
configuracoes.py
----------------
Página "Configurações" (engrenagem no rodapé do menu ou Ctrl + ,):

  - Segurança: PIN, bloqueio por inatividade e criptografia dos backups
    (veja mixins/bloqueio.py e nucleo/seguranca.py).
  - Diagnóstico: versão, pastas, estado dos recursos e teste de conexão com o GitHub
    (atualizações) e o Supabase (nuvem). Os testes rodam em segundo plano.
"""

import os
import queue
import threading
from tkinter import filedialog

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.icons import icone
from anotacoes.interface.widgets import alinhar_esquerda, fonte
from anotacoes.nucleo import certificados, diagnostico, inicializacao, seguranca

ABAS = ("Segurança", "Diagnóstico")
ROTULOS_BLOQUEIO = {m: (f"{m} minuto" if m == 1 else f"{m} minutos")
                    for m in seguranca.OPCOES_BLOQUEIO}
_ICONE_ESTADO = {diagnostico.OK: ("check_circle", "VERDE"), diagnostico.AVISO: ("warning", "AMBAR"),
                 diagnostico.ERRO: ("warning", "VERMELHO"), diagnostico.PULADO: ("clock", "TEXTO_SUAVE")}


class ConfiguracoesMixin:
    """Requer: self.db, self.seguranca, self.toast, self.after, self._card, self._cabecalho,
    self.bloquear, self.abrir_dialogo_pin, self.alternar_criptografia_backups,
    self.definir_bloqueio_minutos, self._nuvem_cfg, self.nuvem_conectada."""

    # ==================================================================
    # Página
    # ==================================================================
    def _criar_pagina_config(self, pai) -> ctk.CTkFrame:
        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self._cabecalho(pagina, "Configurações",
                        "Segurança dos dados e diagnóstico do programa.")
        card = self._card(pagina)
        card.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        self._fila_diag = queue.Queue()
        self._diag_rodando = False

        self.abas_config = ctk.CTkSegmentedButton(
            card, values=list(ABAS), height=40, font=fonte(13, "bold"),
            selected_color=T.SEG_SELECIONADO, selected_hover_color=T.SEG_SELECIONADO,
            unselected_color=T.TEAL_CLARO, unselected_hover_color=T.TEAL_BORDA,
            text_color=T.TEXTO, fg_color=T.TEAL_CLARO, command=self._trocar_aba_config)
        self.abas_config.set(ABAS[0])
        self.abas_config.pack(anchor="w", padx=24, pady=(20, 10))

        self._aba_seguranca = ctk.CTkFrame(card, fg_color="transparent")
        self._aba_diagnostico = ctk.CTkFrame(card, fg_color="transparent")
        self._montar_aba_seguranca(self._aba_seguranca)
        self._montar_aba_diagnostico(self._aba_diagnostico)
        self._aba_seguranca.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        return pagina

    def _trocar_aba_config(self, aba: str) -> None:
        self._aba_seguranca.pack_forget()
        self._aba_diagnostico.pack_forget()
        alvo = self._aba_seguranca if aba == ABAS[0] else self._aba_diagnostico
        alvo.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        self.atualizar_config()

    def atualizar_config(self) -> None:
        """Atualiza os dados mostrados nas duas abas (chamado ao abrir a página)."""
        if not hasattr(self, "lbl_pin_estado"):
            return
        try:
            self._atualizar_aba_seguranca()
            self._atualizar_aba_diagnostico()
        except Exception:
            pass   # a página pode estar sendo recriada (troca de tema)

    # ==================================================================
    # Aba Segurança
    # ==================================================================
    @staticmethod
    def _botao(pai, texto, comando, destaque=False, **kw):
        if destaque:
            return ctk.CTkButton(pai, text=texto, height=40, corner_radius=10, font=fonte(13, "bold"),
                                 fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
                                 command=comando, **kw)
        return ctk.CTkButton(pai, text=texto, height=40, corner_radius=10, font=fonte(13, "bold"),
                             fg_color="transparent", text_color=T.TEXTO, border_width=2,
                             border_color=T.BORDA_FORTE, hover_color=T.FUNDO, command=comando, **kw)

    def _montar_aba_seguranca(self, aba) -> None:
        ctk.CTkLabel(aba, text="Proteção por PIN", font=fonte(16, "bold"), text_color=T.TEXTO,
                     anchor="w").pack(anchor="w")
        self.lbl_pin_estado = ctk.CTkLabel(aba, text="", font=fonte(14, "bold"), anchor="w")
        self.lbl_pin_estado.pack(anchor="w", pady=(4, 0))
        alinhar_esquerda(ctk.CTkLabel(
            aba, text="O PIN bloqueia a tela ao abrir e depois de um tempo sem uso, e é a senha "
                      "dos backups criptografados. O arquivo do banco em uso continua legível para "
                      "quem tiver acesso à pasta do programa: use também a senha do Windows.",
            font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=780,
        )).pack(anchor="w", pady=(4, 12))

        botoes = ctk.CTkFrame(aba, fg_color="transparent")
        botoes.pack(anchor="w")
        self.btn_pin_ativar = self._botao(botoes, "Ativar PIN", lambda: self.abrir_dialogo_pin("criar"),
                                          destaque=True)
        self.btn_pin_alterar = self._botao(botoes, "Alterar PIN", lambda: self.abrir_dialogo_pin("alterar"))
        self.btn_pin_remover = self._botao(botoes, "Remover PIN", lambda: self.abrir_dialogo_pin("desativar"))
        self.btn_pin_bloquear = self._botao(botoes, "Bloquear agora", self.bloquear)
        self._botoes_pin = (self.btn_pin_ativar, self.btn_pin_alterar, self.btn_pin_remover,
                            self.btn_pin_bloquear)

        self.grp_pin_opcoes = ctk.CTkFrame(aba, fg_color="transparent")
        linha = ctk.CTkFrame(self.grp_pin_opcoes, fg_color="transparent")
        linha.pack(anchor="w", pady=(18, 0))
        ctk.CTkLabel(linha, text="Bloquear depois de", font=fonte(14), text_color=T.TEXTO).pack(side="left")
        self.menu_bloqueio = ctk.CTkOptionMenu(
            linha, values=list(ROTULOS_BLOQUEIO.values()), width=140, height=38, font=fonte(13),
            dropdown_font=fonte(13), fg_color=T.TEAL_CLARO, text_color=T.TEXTO,
            button_color=T.TEAL, button_hover_color=T.TEAL_ESCURO,
            dropdown_fg_color=T.SUPERFICIE, dropdown_text_color=T.TEXTO,
            dropdown_hover_color=T.TEAL_CLARO, command=self._ao_escolher_bloqueio)
        self.menu_bloqueio.pack(side="left", padx=10)
        ctk.CTkLabel(linha, text="sem uso", font=fonte(14), text_color=T.TEXTO).pack(side="left")
        self.chk_backup_cripto = ctk.CTkCheckBox(
            self.grp_pin_opcoes, text="Criptografar os backups (AES-256) com o PIN",
            font=fonte(14), text_color=T.TEXTO, fg_color=T.TEAL, hover_color=T.TEAL_ESCURO,
            border_color=T.BORDA_FORTE, checkmark_color=T.SOBRE_COR,
            command=lambda: self.alternar_criptografia_backups(bool(self.chk_backup_cripto.get())))
        self.chk_backup_cripto.pack(anchor="w", pady=(16, 0))
        self.lbl_cripto_info = ctk.CTkLabel(self.grp_pin_opcoes, text="", font=fonte(12),
                                            text_color=T.TEXTO_SUAVE, anchor="w", wraplength=780)
        self.lbl_cripto_info.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            aba, text="Esqueceu o PIN? Veja docs/seguranca.md. Sem a senha, backups criptografados "
                      "não podem ser abertos.", font=fonte(12), text_color=T.TEXTO_SUAVE,
            anchor="w").pack(side="bottom", anchor="w")

    def _atualizar_aba_seguranca(self) -> None:
        ativa = self.seguranca.ativa
        self.lbl_pin_estado.configure(text="Ativada" if ativa else "Desativada",
                                      text_color=T.VERDE if ativa else T.TEXTO)
        for botao in self._botoes_pin:
            botao.pack_forget()
        if ativa:
            for botao in (self.btn_pin_alterar, self.btn_pin_remover, self.btn_pin_bloquear):
                botao.pack(side="left", padx=(0, 10))
            self.grp_pin_opcoes.pack(anchor="w", fill="x")
        else:
            self.btn_pin_ativar.pack(side="left")
            self.grp_pin_opcoes.pack_forget()
        self.menu_bloqueio.set(ROTULOS_BLOQUEIO[self.seguranca.bloqueio_minutos])
        disponivel = seguranca.criptografia_disponivel()
        (self.chk_backup_cripto.select if self.seguranca.criptografar_backups
         else self.chk_backup_cripto.deselect)()
        self.chk_backup_cripto.configure(state="normal" if disponivel else "disabled")
        self.lbl_cripto_info.configure(
            text="Backups novos saem criptografados (.dbx); só abrem com a senha usada ao criá-los."
            if self.seguranca.criptografar_backups else
            "Backups sem criptografia podem ser lidos por quem copiar a pasta de backups."
            if disponivel else "A criptografia não está disponível neste computador.")

    def _ao_escolher_bloqueio(self, rotulo: str) -> None:
        minutos = next((m for m, r in ROTULOS_BLOQUEIO.items() if r == rotulo), None)
        if minutos:
            self.definir_bloqueio_minutos(minutos)

    # ==================================================================
    # Aba Diagnóstico
    # ==================================================================
    def _montar_aba_diagnostico(self, aba) -> None:
        self.quadro_info = ctk.CTkFrame(aba, fg_color="transparent")
        self.quadro_info.pack(fill="x")
        barra = ctk.CTkFrame(aba, fg_color="transparent")
        barra.pack(fill="x", pady=(14, 8))
        self.btn_testar = self._botao(barra, "Testar conexão", self.testar_conexoes, destaque=True)
        self.btn_testar.pack(side="left")
        self._botao(barra, "Importar certificado da rede", self.importar_certificado_rede).pack(
            side="left", padx=(10, 0))
        self.lbl_testando = ctk.CTkLabel(barra, text="", font=fonte(13), text_color=T.TEXTO_SUAVE)
        self.lbl_testando.pack(side="left", padx=14)
        self.quadro_testes = ctk.CTkFrame(aba, fg_color="transparent")
        self.quadro_testes.pack(fill="x")

    def _atualizar_aba_diagnostico(self) -> None:
        for filho in self.quadro_info.winfo_children():
            filho.destroy()
        inicio = inicializacao.ativo() if inicializacao.suportado() else None
        linhas = diagnostico.linhas_informacao(
            T.VERSAO, self.db.caminho, self.db.pasta_backups(), self.seguranca.ativa,
            inicio, seguranca.criptografia_disponivel())
        self.quadro_info.grid_columnconfigure(1, weight=1)
        for i, (rotulo, valor) in enumerate(linhas):
            ctk.CTkLabel(self.quadro_info, text=rotulo, font=fonte(13, "bold"), text_color=T.TEXTO,
                         anchor="w", width=190).grid(row=i, column=0, sticky="w", pady=1)
            ctk.CTkLabel(self.quadro_info, text=valor, font=fonte(13), text_color=T.TEXTO_SUAVE,
                         anchor="w", wraplength=560).grid(
                row=i, column=1, sticky="w", padx=(10, 0), pady=1)

    def importar_certificado_rede(self) -> None:
        """Para redes que inspecionam a conexão segura: o certificado raiz da instituição
        (fornecido pela TI) passa a ser aceito. A verificação continua ligada."""
        caminho = filedialog.askopenfilename(
            parent=self, title="Escolher o certificado raiz da rede",
            filetypes=[("Certificados", "*.pem *.crt *.cer"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            certificados.importar_certificado(caminho, os.path.dirname(self.db.caminho))
        except ValueError as exc:
            self.toast.mostrar(str(exc), "erro", 6000)
            return
        self.toast.mostrar("Certificado importado. Clique em \"Testar conexão\" para conferir.",
                           "sucesso", 5000)

    # --- Teste de conexão (em segundo plano) -------------------------------------
    def testar_conexoes(self) -> None:
        if self._diag_rodando:
            return
        self._diag_rodando = True
        self.btn_testar.configure(state="disabled")
        self.lbl_testando.configure(text="Testando...")
        for filho in self.quadro_testes.winfo_children():
            filho.destroy()
        repositorio = T.REPOSITORIO_GITHUB
        url, chave = self._nuvem_cfg.get("url"), self._nuvem_cfg.get("chave")

        def tarefa():
            try:
                self._fila_diag.put(diagnostico.testar_github(repositorio))
                self._fila_diag.put(diagnostico.testar_supabase(url, chave))
            except Exception as exc:      # nunca deixa o botão preso
                self._fila_diag.put(diagnostico.Resultado("Teste", diagnostico.ERRO, str(exc)))
            self._fila_diag.put(None)

        threading.Thread(target=tarefa, daemon=True).start()
        self.after(200, self._sondar_diagnostico)

    def _sondar_diagnostico(self) -> None:
        terminou = False
        try:
            while True:
                item = self._fila_diag.get_nowait()
                if item is None:
                    terminou = True
                    break
                self._mostrar_resultado(item)
        except queue.Empty:
            pass
        if not terminou:
            self.after(200, self._sondar_diagnostico)
            return
        self._diag_rodando = False
        self.btn_testar.configure(state="normal")
        self.lbl_testando.configure(text="")

    def _mostrar_resultado(self, r) -> None:
        nome_icone, nome_cor = _ICONE_ESTADO.get(r.estado, _ICONE_ESTADO[diagnostico.ERRO])
        cor = getattr(T, nome_cor)
        linha = ctk.CTkFrame(self.quadro_testes, fg_color="transparent")
        linha.pack(fill="x", pady=3)
        ctk.CTkLabel(linha, text="", image=icone(nome_icone, cor, 20)).pack(side="left", anchor="n",
                                                                          padx=(0, 10))
        textos = ctk.CTkFrame(linha, fg_color="transparent")
        textos.pack(side="left", fill="x", expand=True)
        tempo = f"  ({r.ms} ms)" if r.ms and r.estado in (diagnostico.OK, diagnostico.AVISO) else ""
        ctk.CTkLabel(textos, text=r.nome + tempo, font=fonte(14, "bold"), text_color=T.TEXTO,
                     anchor="w").pack(anchor="w")
        alinhar_esquerda(ctk.CTkLabel(textos, text=r.mensagem, font=fonte(13), text_color=cor,
                                      anchor="w", wraplength=700)).pack(anchor="w")
