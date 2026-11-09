"""
resumo.py
---------
Página "Resumo do dia": o que precisa de atenção hoje (retornos de hoje ou
atrasados, urgentes pendentes e pendentes antigos), com acesso direto a cada
registro. É a tela inicial quando há algo pendente de atenção.
"""

from datetime import date, datetime, timedelta

import customtkinter as ctk

from anotacoes import theme as T
from anotacoes.nucleo.database import STATUS_PENDENTE
from anotacoes.interface.icons import icone
from anotacoes.nucleo.util import (
    DIAS,
    MESES,
    formatar_lembrete,
    plural,
    resumir,
    saudacao,
    situacao_retorno,
)
from anotacoes.interface.widgets import CartaoNumero, alinhar_esquerda, fonte

DIAS_ANTIGO = 7          # pendente há mais de N dias = "antigo"
MAX_ITENS_RESUMO = 8


class ResumoMixin:
    """Requer: self._card, self._cabecalho, self.db, self.mostrar_pagina,
    self.ver_detalhes(registro_id), self.filtro_status, self.atualizar_historico."""

    def _criar_pagina_resumo(self, pai) -> ctk.CTkFrame:
        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self.lbl_saudacao = ctk.CTkLabel(
            pagina, text="", font=fonte(26, "bold"), text_color=T.TEXTO, anchor="w")
        self.lbl_saudacao.pack(anchor="w", padx=34, pady=(30, 0))
        self.lbl_saudacao_data = ctk.CTkLabel(
            pagina, text="", font=fonte(14), text_color=T.TEXTO_SUAVE, anchor="w")
        self.lbl_saudacao_data.pack(anchor="w", padx=34, pady=(2, 18))

        cartoes = ctk.CTkFrame(pagina, fg_color="transparent")
        cartoes.pack(fill="x", padx=34, pady=(0, 18))
        for i in range(3):
            cartoes.grid_columnconfigure(i, weight=1, uniform="resumo")
        self.res_c_ret = CartaoNumero(cartoes, "Retornos a fazer", T.VERMELHO, T.VERMELHO_CLARO, "warning")
        self.res_c_urg = CartaoNumero(cartoes, "Urgentes pendentes", T.AMBAR, T.AMBAR_CLARO, "clock")
        self.res_c_ant = CartaoNumero(
            cartoes, f"Pendentes há mais de {DIAS_ANTIGO} dias", T.TEAL, T.TEAL_CLARO, "list")
        self.res_c_ret.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.res_c_urg.grid(row=0, column=1, sticky="ew", padx=8)
        self.res_c_ant.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        # Botões presos à base; a lista é a parte que encolhe.
        botoes = ctk.CTkFrame(pagina, fg_color="transparent")
        botoes.pack(side="bottom", fill="x", padx=34, pady=(0, 30))
        ctk.CTkButton(
            botoes, text="Novo registro", width=170, height=44, corner_radius=10,
            image=icone("plus", T.SOBRE_COR, 18), compound="left",
            font=fonte(14, "bold"), fg_color=T.TEAL, hover_color=T.TEAL_ESCURO,
            text_color=T.SOBRE_COR, command=lambda: self.mostrar_pagina("novo"),
        ).pack(side="left")
        ctk.CTkButton(
            botoes, text="Ver pendentes no histórico", width=230, height=44,
            corner_radius=10, font=fonte(14, "bold"), fg_color="transparent",
            text_color=T.TEAL, border_width=2, border_color=T.TEAL,
            hover_color=T.TEAL_CLARO, command=self._resumo_ver_pendentes,
        ).pack(side="left", padx=(10, 0))

        card = self._card(pagina)
        card.pack(fill="both", expand=True, padx=34, pady=(0, 16))
        interno = ctk.CTkFrame(card, fg_color="transparent")
        interno.pack(fill="both", expand=True, padx=26, pady=20)
        ctk.CTkLabel(interno, text="Para ver agora", font=fonte(17, "bold"),
                     text_color=T.TEXTO, anchor="w").pack(anchor="w", pady=(0, 6))
        self.lista_resumo = ctk.CTkFrame(interno, fg_color="transparent")
        self.lista_resumo.pack(fill="both", expand=True)
        return pagina

    def _resumo_ver_pendentes(self) -> None:
        self.filtro_status.set("Pendentes")
        self.mostrar_pagina("historico")

    # ------------------------------------------------------------------
    def itens_do_resumo(self):
        """(itens, n_retornos, n_urgentes, n_antigos). Cada item é
        (registro, [motivos]) sem repetir registros, na ordem de importância."""
        hoje = date.today()
        retornos = sorted(self.db.listar(so_retornos=True), key=lambda r: r[6])
        urgentes = self.db.listar(status=STATUS_PENDENTE, so_urgentes=True)
        antigos = self.db.listar(
            status=STATUS_PENDENTE, ate=(hoje - timedelta(days=DIAS_ANTIGO)).isoformat())
        itens, motivos = {}, {}
        ordem = []
        for grupo in (retornos, urgentes, antigos):
            for reg in grupo:
                if reg[0] not in itens:
                    itens[reg[0]] = reg
                    ordem.append(reg[0])
                    motivos[reg[0]] = []
        for reg in retornos:
            situacao = situacao_retorno(reg[6], reg[5], hoje)
            motivos[reg[0]].append(
                "Retorno atrasado (" + formatar_lembrete(reg[6])[:5] + ")"
                if situacao == "atrasado" else "Retorno hoje")
        for reg in urgentes:
            motivos[reg[0]].append("Urgente")
        for reg in antigos:
            dias = (hoje - datetime.strptime(reg[1][:10], "%Y-%m-%d").date()).days
            motivos[reg[0]].append(f"Pendente há {plural(dias, 'dia', 'dias')}")
        return ([(itens[i], motivos[i]) for i in ordem],
                len(retornos), len(urgentes), len(antigos))

    def atualizar_resumo(self) -> None:
        if not hasattr(self, "lista_resumo"):
            return
        agora = datetime.now()
        self.lbl_saudacao.configure(text=saudacao(agora.hour) + "!")
        self.lbl_saudacao_data.configure(
            text=f"{DIAS[agora.weekday()].capitalize()}, {agora.day} de "
                 f"{MESES[agora.month - 1]}. Veja o que precisa de atenção.")
        itens, n_ret, n_urg, n_ant = self.itens_do_resumo()
        self.res_c_ret.definir(n_ret)
        self.res_c_urg.definir(n_urg)
        self.res_c_ant.definir(n_ant)

        for filho in self.lista_resumo.winfo_children():
            filho.destroy()
        if not itens:
            ctk.CTkLabel(self.lista_resumo, text="", image=icone("check_circle", T.VERDE, 44)
                         ).pack(pady=(26, 6))
            ctk.CTkLabel(self.lista_resumo, text="Nada pendente de atenção",
                         font=fonte(17, "bold"), text_color=T.TEXTO).pack()
            ctk.CTkLabel(self.lista_resumo,
                         text="Sem retornos, urgências ou pendências antigas. Bom trabalho!",
                         font=fonte(13), text_color=T.TEXTO_SUAVE).pack()
            return
        for reg, motivos in itens[:MAX_ITENS_RESUMO]:
            rid, _data, nome, contato, descricao = reg[0], reg[1], reg[2], reg[3], reg[4]
            alerta = any(m.startswith(("Retorno", "Urgente")) for m in motivos)
            linha = ctk.CTkFrame(self.lista_resumo, fg_color="transparent")
            linha.pack(fill="x", pady=4)
            ctk.CTkButton(
                linha, text="Abrir", width=84, height=34, corner_radius=8,
                font=fonte(13, "bold"), fg_color="transparent", text_color=T.TEAL,
                border_width=2, border_color=T.TEAL, hover_color=T.TEAL_CLARO,
                command=lambda i=rid: self.ver_detalhes(i),
            ).pack(side="right", padx=(10, 0))
            ctk.CTkFrame(linha, width=10, height=10, corner_radius=5,
                         fg_color=T.VERMELHO if alerta else T.AMBAR
                         ).pack(side="left", padx=(0, 12), anchor="n", pady=7)
            textos = ctk.CTkFrame(linha, fg_color="transparent")
            textos.pack(side="left", fill="x", expand=True)
            alinhar_esquerda(ctk.CTkLabel(
                textos, text=resumir(nome, 40), font=fonte(14, "bold"),
                text_color=T.TEXTO, anchor="w")).pack(anchor="w")
            alinhar_esquerda(ctk.CTkLabel(
                textos,
                text=" • ".join([" / ".join(motivos), resumir(contato or "sem contato", 22),
                                 resumir(descricao, 46)]),
                font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w")).pack(anchor="w")
        restantes = len(itens) - MAX_ITENS_RESUMO
        if restantes > 0:
            ctk.CTkLabel(
                self.lista_resumo,
                text=f"e mais {plural(restantes, 'registro', 'registros')} no Histórico.",
                font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w",
            ).pack(anchor="w", pady=(8, 0))

    def ha_algo_para_ver(self) -> bool:
        return bool(self.db.contar_retornos() or self.db.contar_urgentes()
                    or self.db.listar(
                        status=STATUS_PENDENTE,
                        ate=(date.today() - timedelta(days=DIAS_ANTIGO)).isoformat(),
                        limite=1))
