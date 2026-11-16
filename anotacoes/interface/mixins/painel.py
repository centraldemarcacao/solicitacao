"""
painel.py
---------
Página "Painel" (painel de controle), com dois acessos:

  * "Meu painel"     — todo usuário: só os PRÓPRIOS números (calculados neste computador).
  * "Administração"  — só administradores: contas da nuvem, ativar/desativar acesso, papéis
                       e números agregados por usuário. Nenhum texto de paciente aparece.

Segurança: quem é administrador é decidido pelo SERVIDOR (função `painel_meu_papel`); a aba
de administração só aparece depois dessa confirmação (sem internet ou em caso de erro, ela
fica oculta) e cada ação é validada de novo no servidor (`painel_exigir_admin`).
"""

import logging
import queue
import threading
from datetime import datetime

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.interface.widgets import (CartaoNumero, DialogoConfirmacao, Pilula,
                                         TabelaRegistros, alinhar_esquerda, fonte)
from anotacoes.nuvem import painel
from anotacoes.nuvem.cliente import NuvemErro
from anotacoes.nuvem.sql import SQL_PAINEL
from anotacoes.nucleo.util import plural

log = logging.getLogger(__name__)

ABA_MEU = "Meu painel"
ABA_ADMIN = "Administração"
DIAS_GRAFICO = 14
ALTURA_BARRAS = 110


class PainelMixin:
    """Requer: self.db, self.toast, self.after, self._card, self._cabecalho, self._botao,
    self._px, self._nuvem_cfg, self._sync_trava, self.nuvem_conectada(), self._cliente_nuvem()."""

    # ==================================================================
    # Página
    # ==================================================================
    def _criar_pagina_painel(self, pai) -> ctk.CTkFrame:
        self._painel_fila = queue.Queue()
        self._painel_rodando = False
        self._painel_papel = None          # None = não confirmado pelo servidor
        self._painel_usuarios = {}
        self._painel_erro = ""

        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self._cabecalho(pagina, "Painel de controle",
                        "Seus números e, para administradores, a gestão das contas da nuvem.")
        card = self._card(pagina)
        card.pack(fill="both", expand=True, padx=34, pady=(0, 30))

        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.pack(fill="x", padx=24, pady=(20, 6))
        self.abas_painel = ctk.CTkSegmentedButton(
            topo, values=[ABA_MEU], height=40, font=fonte(13, "bold"),
            selected_color=T.SEG_SELECIONADO, selected_hover_color=T.SEG_SELECIONADO,
            unselected_color=T.TEAL_CLARO, unselected_hover_color=T.TEAL_BORDA,
            text_color=T.TEXTO, fg_color=T.TEAL_CLARO, command=self._trocar_aba_painel)
        self.abas_painel.set(ABA_MEU)
        self.abas_painel.pack(side="left")
        self.pil_painel_papel = Pilula(topo, "Somente neste computador", T.TEAL_CLARO, T.TEXTO, 12)
        self.pil_painel_papel.pack(side="right")

        self._aba_meu = ctk.CTkFrame(card, fg_color="transparent")
        self._aba_admin = ctk.CTkFrame(card, fg_color="transparent")
        self._montar_aba_meu(self._aba_meu)
        self._montar_aba_admin(self._aba_admin)
        self._aba_meu.pack(fill="both", expand=True, padx=24, pady=(6, 18))
        return pagina

    def _trocar_aba_painel(self, aba: str) -> None:
        self._aba_meu.pack_forget()
        self._aba_admin.pack_forget()
        alvo = self._aba_admin if aba == ABA_ADMIN and self._painel_papel == painel.PAPEL_ADMIN \
            else self._aba_meu
        alvo.pack(fill="both", expand=True, padx=24, pady=(6, 18))

    def abrir_painel(self) -> None:
        """Chamado ao abrir a página: números locais na hora; papel e contas via nuvem."""
        self.atualizar_painel_local()
        self._aplicar_papel()
        if self.nuvem_conectada():
            self._painel_executar()

    # ==================================================================
    # Aba "Meu painel" (local)
    # ==================================================================
    def _montar_aba_meu(self, aba) -> None:
        self.lbl_painel_origem = ctk.CTkLabel(
            aba, text="", font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w", wraplength=780)
        self.lbl_painel_origem.pack(anchor="w", pady=(0, 10))

        grade = ctk.CTkFrame(aba, fg_color="transparent")
        grade.pack(fill="x")
        for i in range(3):
            grade.grid_columnconfigure(i, weight=1, uniform="painel")
        especificacoes = (
            ("total", "Registros", T.TEAL, T.TEAL_CLARO, "list"),
            ("pendentes", "Pendentes", T.AMBAR, T.AMBAR_CLARO, "clock"),
            ("atendidas", "Atendidas", T.VERDE, T.VERDE_CLARO, "check_circle"),
            ("urgentes", "Urgentes pendentes", T.VERMELHO, T.VERMELHO_CLARO, "warning"),
            ("retornos", "Retornos a fazer", T.AMBAR, T.AMBAR_CLARO, "bell"),
            ("hoje", "Registrados hoje", T.TEAL, T.TEAL_CLARO, "plus"),
        )
        self._painel_cartoes = {}
        for i, (chave, titulo, cor, tinte, nome_icone) in enumerate(especificacoes):
            cartao = CartaoNumero(grade, titulo, cor, tinte, nome_icone)
            cartao.grid(row=i // 3, column=i % 3, sticky="ew",
                        padx=(0 if i % 3 == 0 else 6, 0 if i % 3 == 2 else 6),
                        pady=(0 if i < 3 else 10, 0))
            self._painel_cartoes[chave] = cartao

        prog = ctk.CTkFrame(aba, fg_color="transparent")
        prog.pack(fill="x", pady=(16, 0))
        self.lbl_painel_prog = ctk.CTkLabel(prog, text="", font=fonte(13, "bold"),
                                            text_color=T.TEXTO, anchor="w")
        self.lbl_painel_prog.pack(anchor="w")
        self.barra_painel = ctk.CTkProgressBar(prog, height=12, corner_radius=6,
                                               fg_color=T.BORDA, progress_color=T.VERDE)
        self.barra_painel.pack(fill="x", pady=(6, 0))
        self.barra_painel.set(0)

        ctk.CTkLabel(aba, text=f"Registros por dia (últimos {DIAS_GRAFICO} dias)",
                     font=fonte(13, "bold"), text_color=T.TEXTO, anchor="w").pack(
            anchor="w", pady=(18, 4))
        self._painel_grafico = ctk.CTkFrame(aba, fg_color="transparent")
        self._painel_grafico.pack(fill="x")

    def atualizar_painel_local(self) -> None:
        """Recalcula os números deste computador (só contagens)."""
        if not hasattr(self, "_painel_cartoes"):
            return
        try:
            ind = self.db.indicadores(DIAS_GRAFICO)
            for chave, cartao in self._painel_cartoes.items():
                cartao.definir(ind[chave])
            total = ind["total"]
            pct = (ind["atendidas"] / total) if total else 0
            self.lbl_painel_prog.configure(
                text=f"{round(pct * 100)}% das solicitações já foram atendidas "
                     f"({ind['atendidas']} de {total})")
            self.barra_painel.set(pct)
            self._desenhar_grafico(ind["por_dia"])
        except Exception:
            log.warning("Falha ao atualizar o painel local", exc_info=True)

    def _desenhar_grafico(self, por_dia) -> None:
        for filho in self._painel_grafico.winfo_children():
            filho.destroy()
        maior = max((n for _d, n in por_dia), default=0) or 1
        hoje = datetime.now().strftime("%Y-%m-%d")
        for i, (dia, n) in enumerate(por_dia):
            self._painel_grafico.grid_columnconfigure(i, weight=1, uniform="barras")
            coluna = ctk.CTkFrame(self._painel_grafico, fg_color="transparent")
            coluna.grid(row=0, column=i, sticky="nsew", padx=2)
            ctk.CTkLabel(coluna, text=dia[8:10], font=fonte(11),
                         text_color=T.TEXTO_SUAVE).pack(side="bottom")
            altura = max(3, round(ALTURA_BARRAS * n / maior)) if n else 3
            ctk.CTkFrame(coluna, height=altura, corner_radius=4,
                         fg_color=T.TEAL if dia == hoje else (T.TEAL_BORDA if n else T.BORDA)
                         ).pack(side="bottom", fill="x", padx=4, pady=(0, 3))
            ctk.CTkLabel(coluna, text=str(n) if n else "", font=fonte(11, "bold"),
                         text_color=T.TEXTO).pack(side="bottom")
            ctk.CTkFrame(coluna, height=ALTURA_BARRAS - altura, fg_color="transparent").pack(
                side="top")

    # ==================================================================
    # Aba "Administração"
    # ==================================================================
    def _montar_aba_admin(self, aba) -> None:
        grade = ctk.CTkFrame(aba, fg_color="transparent")
        grade.pack(fill="x")
        for i in range(4):
            grade.grid_columnconfigure(i, weight=1, uniform="adm")
        self._admin_cartoes = {}
        for i, (chave, titulo, cor, tinte, nome_icone) in enumerate((
                ("usuarios", "Contas", T.TEAL, T.TEAL_CLARO, "grid"),
                ("ativos", "Com acesso", T.VERDE, T.VERDE_CLARO, "check_circle"),
                ("registros", "Registros (todos)", T.TEAL, T.TEAL_CLARO, "list"),
                ("pendentes", "Pendentes (todos)", T.AMBAR, T.AMBAR_CLARO, "clock"))):
            cartao = CartaoNumero(grade, titulo, cor, tinte, nome_icone)
            cartao.grid(row=0, column=i, sticky="ew",
                        padx=(0 if i == 0 else 5, 0 if i == 3 else 5))
            self._admin_cartoes[chave] = cartao

        barra = ctk.CTkFrame(aba, fg_color="transparent")
        barra.pack(fill="x", pady=(14, 8))
        self.btn_painel_atualizar = self._botao(
            barra, "Atualizar", self._painel_executar, width=110)
        self.btn_painel_atualizar.pack(side="left")
        self.btn_painel_acesso = self._botao(
            barra, "Ativar / desativar acesso", self._alternar_acesso, destaque=True, width=190)
        self.btn_painel_acesso.pack(side="left", padx=(10, 0))
        self.btn_painel_papel = self._botao(
            barra, "Alterar papel", self._alternar_papel, width=130)
        self.btn_painel_papel.pack(side="left", padx=(10, 0))
        self.btn_painel_sql = self._botao(
            barra, "Copiar SQL do painel", self._copiar_sql_painel, width=170)
        self.btn_painel_sql.pack(side="right")

        self.lbl_painel_estado = ctk.CTkLabel(aba, text="", font=fonte(12), anchor="w",
                                              text_color=T.TEXTO_SUAVE, wraplength=780)
        self.lbl_painel_estado.pack(anchor="w", pady=(0, 6))

        self.tabela_painel = TabelaRegistros(
            aba,
            [("email", "E-mail", 230, True), ("papel", "Papel", 110, False),
             ("estado", "Acesso", 90, False), ("registros", "Registros", 85, False),
             ("pendentes", "Pendentes", 90, False), ("atendidas", "Atendidas", 90, False),
             ("ultimo", "Último acesso", 140, False)],
            self._px, ao_selecionar=self._atualizar_botoes_painel)
        self.tabela_painel.pack(fill="both", expand=True)

        ctk.CTkLabel(aba, text="Últimas ações de administração", font=fonte(13, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w", pady=(12, 2))
        self.lbl_painel_auditoria = alinhar_esquerda(ctk.CTkLabel(
            aba, text="", font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w",
            wraplength=780))
        self.lbl_painel_auditoria.pack(anchor="w")

    def _aplicar_papel(self) -> None:
        """Mostra ou esconde a aba de administração conforme o papel confirmado."""
        admin = self._painel_papel == painel.PAPEL_ADMIN
        self.abas_painel.configure(values=[ABA_MEU, ABA_ADMIN] if admin else [ABA_MEU])
        if not admin:
            self.abas_painel.set(ABA_MEU)
            self._trocar_aba_painel(ABA_MEU)
        if not self.nuvem_conectada():
            self.pil_painel_papel.definir("Somente neste computador", T.TEAL_CLARO, T.TEXTO)
            self.lbl_painel_origem.configure(
                text="Estes números são calculados neste computador. Conecte-se à Nuvem para "
                     "que o servidor confirme o seu papel.")
        elif admin:
            self.pil_painel_papel.definir("Administrador", T.AMBAR_CLARO, T.TEXTO)
            self.lbl_painel_origem.configure(
                text="Estes são os seus números (deste computador). A aba Administração mostra "
                     "apenas contagens, nunca o texto dos atendimentos.")
        elif self._painel_papel == painel.PAPEL_USUARIO:
            self.pil_painel_papel.definir("Usuário", T.VERDE_CLARO, T.TEXTO)
            self.lbl_painel_origem.configure(text="Você vê somente os seus próprios números.")
        else:
            self.pil_painel_papel.definir("Verificando…" if self._painel_rodando
                                          else "Papel não confirmado", T.TEAL_CLARO, T.TEXTO)
            self.lbl_painel_origem.configure(
                text=self._painel_erro or "Confirmando o seu papel no servidor…")

    def _selecionado_painel(self):
        ids = self.tabela_painel.selecionados()
        return self._painel_usuarios.get(ids[0]) if len(ids) == 1 else None

    def _eh_voce(self, usuario) -> bool:
        return usuario.email.lower() == str(self._nuvem_cfg.get("email") or "").lower()

    def _atualizar_botoes_painel(self) -> None:
        u = self._selecionado_painel()
        pode = u is not None and not self._eh_voce(u) and not self._painel_rodando
        for botao in (self.btn_painel_acesso, self.btn_painel_papel):
            botao.configure(state="normal" if pode else "disabled")
        if u is not None:
            self.btn_painel_acesso.configure(
                text="Desativar acesso" if u.ativo else "Ativar acesso")
            self.btn_painel_papel.configure(
                text="Tornar usuário" if u.eh_admin else "Tornar administrador")
        else:
            self.btn_painel_acesso.configure(text="Ativar / desativar acesso")
            self.btn_painel_papel.configure(text="Alterar papel")
        self.btn_painel_atualizar.configure(state="disabled" if self._painel_rodando else "normal")

    def _copiar_sql_painel(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(SQL_PAINEL)
        self.toast.mostrar("SQL do painel copiado. Cole no SQL Editor do Supabase e clique em Run.",
                           "sucesso", 6000)

    # --- Ações do administrador -----------------------------------------
    def _alternar_acesso(self) -> None:
        u = self._selecionado_painel()
        if u is None or self._eh_voce(u):
            return
        novo = not u.ativo
        if not DialogoConfirmacao.perguntar(
                self, "Ativar acesso" if novo else "Desativar acesso", u.email,
                "Esta conta poderá entrar e sincronizar novamente." if novo else
                "Esta conta não conseguirá mais entrar. Quem já está conectado perde o acesso "
                "assim que a sessão renovar (em até cerca de 1 hora). Os dados são mantidos.",
                texto_confirmar="Ativar" if novo else "Desativar",
                nome_icone="check_circle" if novo else "warning",
                **({"cor": T.TEAL, "cor_hover": T.TEAL_ESCURO, "cor_clara": T.TEAL_CLARO}
                   if novo else {})):
            return
        self._painel_executar(lambda c: painel.definir_acesso(c, u.id, novo),
                              "Acesso ativado." if novo else "Acesso desativado.")

    def _alternar_papel(self) -> None:
        u = self._selecionado_painel()
        if u is None or self._eh_voce(u):
            return
        novo = painel.PAPEL_USUARIO if u.eh_admin else painel.PAPEL_ADMIN
        if not DialogoConfirmacao.perguntar(
                self, "Alterar papel", u.email,
                f"O papel passará a ser “{painel.ROTULO_PAPEL[novo]}”. "
                + ("Administradores veem contas e números agregados de todos."
                   if novo == painel.PAPEL_ADMIN else
                   "A conta deixará de acessar a administração."),
                texto_confirmar="Confirmar", nome_icone="grid",
                cor=T.TEAL, cor_hover=T.TEAL_ESCURO, cor_clara=T.TEAL_CLARO):
            return
        self._painel_executar(lambda c: painel.definir_papel(c, u.id, novo),
                              "Papel atualizado.")

    # ==================================================================
    # Rede (segundo plano)
    # ==================================================================
    def _painel_executar(self, acao=None, aviso: str = "") -> None:
        """Executa `acao` (opcional) e recarrega papel, contas e auditoria, fora da tela."""
        if self._painel_rodando or not self.nuvem_conectada():
            return
        self._painel_rodando = True
        self._painel_erro = ""
        self._aplicar_papel()
        self._atualizar_botoes_painel()

        def trabalho():
            try:
                with self._sync_trava:
                    cliente = self._cliente_nuvem()
                    if acao is not None:
                        acao(cliente)
                    papel = painel.meu_papel(cliente)
                    usuarios, auditoria = [], []
                    if papel == painel.PAPEL_ADMIN:
                        usuarios = painel.listar_usuarios(cliente)
                        auditoria = painel.listar_auditoria(cliente, 8)
                self._painel_fila.put(("ok", aviso, (papel, usuarios, auditoria)))
            except NuvemErro as exc:
                self._painel_fila.put(("erro", str(exc), exc.precisa_login))
            except Exception as exc:  # noqa: BLE001 - nada pode derrubar a thread em silêncio
                log.warning("Falha inesperada no painel", exc_info=True)
                self._painel_fila.put(("erro", f"Falha inesperada: {exc}", False))

        threading.Thread(target=trabalho, daemon=True).start()
        self.after(300, self._sondar_painel)

    def _sondar_painel(self) -> None:
        try:
            tipo, a, b = self._painel_fila.get_nowait()
        except queue.Empty:
            self.after(300, self._sondar_painel)
            return
        self._painel_rodando = False
        if tipo == "ok":
            papel, usuarios, auditoria = b
            self._painel_papel = papel
            self._preencher_admin(usuarios, auditoria)
            if a:
                self.toast.mostrar(a, "sucesso")
        else:
            # Falha fecha a porta: sem confirmação do servidor, nada de administração.
            self._painel_papel = None
            self._painel_erro = a
            self.toast.mostrar(a, "erro", 6000)
        self._aplicar_papel()
        self._atualizar_botoes_painel()

    def _preencher_admin(self, usuarios, auditoria) -> None:
        self._painel_usuarios = {u.id: u for u in usuarios}
        soma = painel.totais(usuarios)
        for chave, cartao in self._admin_cartoes.items():
            cartao.definir(soma[chave])
        self.tabela_painel.preencher([
            (u.id, (u.email + ("  (você)" if self._eh_voce(u) else ""),
                    painel.ROTULO_PAPEL[u.papel], "Ativo" if u.ativo else "Desativado",
                    u.registros, u.pendentes, u.atendidas, u.ultimo_acesso),
             "atendida" if u.ativo else "vencida")
            for u in usuarios])
        if usuarios:
            self.tabela_painel.esconder_vazio()
        else:
            self.tabela_painel.mostrar_vazio("Sem contas", "Nenhuma conta encontrada.")
        self.lbl_painel_estado.configure(
            text=f"{plural(soma['usuarios'], 'conta', 'contas')}, "
                 f"{soma['admins']} administrador(es). Atualizado às "
                 f"{datetime.now().strftime('%H:%M')}.")
        self.lbl_painel_auditoria.configure(
            text="\n".join(f"{a.quando}  ·  {painel.descrever_acao(a)}" for a in auditoria)
            or "Nenhuma ação registrada ainda.")
