"""
paginas.py
----------
Telas adicionais da janela principal, como "mixin" (métodos acrescentados à
classe App em gui.py):

  - Janela de edição de um registro
  - Página "Lixeira"  (restaurar ou apagar definitivamente)
  - Página "Backup"   (criar, listar e restaurar cópias de segurança)

Os métodos usam recursos definidos em gui.App (self.db, self.toast,
self._card, self._cabecalho, self._rotulo, self._entrada, ...).
"""

import os

import customtkinter as ctk

import theme as T
from database import DIAS_LIXEIRA, BACKUPS_MANTER, validar_campos
from icons import icone
from util import (
    formatar_data,
    formatar_lembrete,
    formatar_tamanho,
    interpretar_data,
    plural,
    resumir,
)
from widgets import (
    DialogoConfirmacao,
    TabelaRegistros,
    centralizar,
    fonte,
    tornar_modal,
)


class PaginasExtrasMixin:
    # ==================================================================
    # Utilidades
    # ==================================================================
    def _abrir_pasta(self, pasta: str) -> None:
        try:
            if not hasattr(os, "startfile"):
                raise OSError("recurso disponível somente no Windows")
            os.startfile(pasta)
        except Exception:
            self.toast.mostrar(f"Pasta: {pasta}", "info", 8000)

    # ==================================================================
    # Edição de um registro
    # ==================================================================
    def editar_registro(self, registro_id=None) -> None:
        """Abre a janela de edição (do registro indicado ou do selecionado)."""
        if registro_id is None:
            ids = self._ids_selecionados()
            if not ids:
                self.toast.mostrar("Selecione um registro para editar.", "aviso")
                return
            registro_id = ids[0]
        reg = self.db.obter_detalhado(registro_id)
        if not reg:
            self.toast.mostrar("Este registro não está mais disponível.", "aviso")
            self.atualizar_tudo()
            return

        janela = ctk.CTkToplevel(self, fg_color=T.CARD)
        janela.title(f"Editar solicitação nº {reg['id']}")
        janela.resizable(False, False)
        centralizar(janela, self, 640, 760)
        ctk.CTkFrame(janela, fg_color=T.TEAL, height=6, corner_radius=0).pack(fill="x")

        # Botões presos à base: em telas baixas quem encolhe é a descrição.
        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(side="bottom", fill="x", padx=32, pady=(6, 24))
        corpo = ctk.CTkFrame(janela, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=32, pady=(22, 0))

        ctk.CTkLabel(
            corpo, text="Editar solicitação", font=fonte(20, "bold"),
            text_color=T.TEXTO, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            corpo, text=f"Registro nº {reg['id']}  •  criado em {formatar_data(reg['data_hora'])}",
            font=fonte(13), text_color=T.TEXTO_SUAVE, anchor="w",
        ).pack(anchor="w", pady=(2, 14))

        self._rotulo(corpo, "Contato")
        ent_contato = self._entrada(corpo, "Ex.: (84) 99999-0000")
        ent_contato.pack(fill="x", pady=(6, 0))
        ent_contato.insert(0, reg["contato"] or "")
        err_contato = self._rotulo_erro(corpo)

        linha_nome = ctk.CTkFrame(corpo, fg_color="transparent")
        linha_nome.pack(fill="x")
        self._rotulo(linha_nome, "Nome *", lado="left")
        chk_urgente = self._caixa_urgente(linha_nome)
        chk_urgente.pack(side="right")
        if reg["prioridade"] == "Urgente":
            chk_urgente.select()
        ent_nome = self._entrada(corpo, "Ex.: Maria da Silva")
        ent_nome.pack(fill="x", pady=(6, 0))
        ent_nome.insert(0, reg["nome"])
        err_nome = self._rotulo_erro(corpo)

        self._rotulo(corpo, "Descrição da solicitação *")
        err_retorno = self._rotulo_erro(corpo, lado="bottom")
        linha_retorno, ent_retorno = self._campo_retorno(corpo)
        linha_retorno.pack(side="bottom", fill="x", pady=(0, 0))
        self._ligar_mascara_data(ent_retorno)
        ent_retorno.insert(0, formatar_lembrete(reg["lembrete"]))
        err_desc = self._rotulo_erro(corpo, lado="bottom")
        txt_desc = ctk.CTkTextbox(
            corpo, height=110, font=fonte(15), wrap="word",
            border_width=2, border_color=T.BORDA, corner_radius=10,
            fg_color=T.SUPERFICIE, text_color=T.TEXTO,
        )
        txt_desc.pack(fill="both", expand=True, pady=(6, 0))
        txt_desc.insert("1.0", reg["descricao"])

        campos = {
            "contato": (ent_contato, err_contato),
            "nome": (ent_nome, err_nome),
            "descricao": (txt_desc, err_desc),
            "retorno": (ent_retorno, err_retorno),
        }

        def limpar_erro(campo, rotulo):
            campo.configure(border_color=T.BORDA)
            rotulo.configure(text="")

        for campo, rotulo in campos.values():
            campo.bind("<KeyRelease>", lambda _e, c=campo, r=rotulo: limpar_erro(c, r))

        def salvar():
            nome = ent_nome.get().strip()
            contato = ent_contato.get().strip()
            descricao = txt_desc.get("1.0", "end").strip()
            erros = validar_campos(nome, contato, descricao)
            lembrete = None
            try:
                # mantém a data já gravada, mesmo se ela já passou; novas datas não podem ser passadas
                texto_data = ent_retorno.get().strip()
                lembrete = interpretar_data(
                    texto_data, permitir_passado=(texto_data == formatar_lembrete(reg["lembrete"])))
            except ValueError as exc:
                erros["retorno"] = str(exc)
            for chave, (campo, rotulo) in campos.items():
                campo.configure(border_color=T.VERMELHO if chave in erros else T.BORDA)
                rotulo.configure(text=erros.get(chave, ""))
            if erros:
                return
            try:
                prioridade = "Urgente" if chk_urgente.get() else "Normal"
                alterado = self.db.atualizar(
                    reg["id"], nome, contato, descricao, lembrete, prioridade)
            except Exception as exc:
                err_desc.configure(text=f"Não foi possível salvar: {exc}")
                return
            janela.destroy()
            if alterado:
                self.registrar_desfazer("edicao", {
                    "id": reg["id"], "nome": reg["nome"], "contato": reg["contato"] or "",
                    "descricao": reg["descricao"], "lembrete": reg["lembrete"],
                    "prioridade": reg["prioridade"]}, "edição")
            self.atualizar_tudo()
            if alterado:
                self.toast.mostrar("Registro atualizado. Ctrl + Z desfaz.", "sucesso", 4500)
            else:
                self.toast.mostrar("Este registro não está mais disponível.", "aviso")

        ctk.CTkButton(
            botoes, text="Salvar alterações", height=46, width=190, corner_radius=10,
            image=icone("check", T.SOBRE_COR, 20), compound="left",
            font=fonte(15, "bold"), fg_color=T.VERDE, hover_color=T.VERDE_HOVER, text_color=T.SOBRE_COR,
            command=salvar,
        ).pack(side="left")
        ctk.CTkButton(
            botoes, text="Cancelar", height=46, width=130, corner_radius=10,
            font=fonte(15), fg_color="transparent", text_color=T.TEXTO_SUAVE,
            border_width=2, border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
            command=janela.destroy,
        ).pack(side="left", padx=12)

        janela.bind("<Control-s>", lambda _e: salvar())
        tornar_modal(janela, self, foco=ent_contato)

    # ==================================================================
    # Página: Lixeira
    # ==================================================================
    def _criar_pagina_lixeira(self, pai) -> ctk.CTkFrame:
        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self._cabecalho(
            pagina, "Lixeira",
            f"Registros excluídos ficam aqui por {DIAS_LIXEIRA} dias e podem ser restaurados.",
        )
        card = self._card(pagina)
        card.pack(fill="both", expand=True, padx=34, pady=(0, 30))

        barra = ctk.CTkFrame(card, fg_color="transparent")
        barra.pack(fill="x", padx=22, pady=(20, 14))
        ctk.CTkButton(
            barra, text="Restaurar selecionados", height=40, corner_radius=10,
            image=icone("restore", T.SOBRE_COR, 18), compound="left",
            font=fonte(13, "bold"), fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
            command=self.restaurar_selecionados,
        ).pack(side="left")
        ctk.CTkButton(
            barra, text="Esvaziar lixeira", height=40, corner_radius=10,
            image=icone("trash", T.VERMELHO, 18), compound="left",
            font=fonte(13, "bold"), fg_color="transparent", text_color=T.VERMELHO,
            border_width=2, border_color=T.VERMELHO, hover_color=T.VERMELHO_CLARO,
            command=self.esvaziar_lixeira,
        ).pack(side="right")
        ctk.CTkButton(
            barra, text="Apagar definitivamente", height=40, corner_radius=10,
            font=fonte(13, "bold"), fg_color="transparent", text_color=T.VERMELHO,
            border_width=2, border_color=T.VERMELHO, hover_color=T.VERMELHO_CLARO,
            command=self.apagar_definitivamente_selecionados,
        ).pack(side="right", padx=(0, 10))

        rodape = ctk.CTkFrame(card, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=24, pady=(0, 16))
        self.lbl_contagem_lixeira = ctk.CTkLabel(
            rodape, text="", font=fonte(12, "bold"), text_color=T.TEXTO_SUAVE, anchor="w",
        )
        self.lbl_contagem_lixeira.pack(side="left")

        self.tabela_lixeira = TabelaRegistros(
            card,
            [("excluido", "Excluído em", 150, False), ("nome", "Nome", 210, False),
             ("contato", "Contato", 170, False), ("descricao", "Descrição", 330, True),
             ("status", "Status", 110, False)],
            self._px, ao_selecionar=self._atualizar_rodape_lixeira,
        )
        self.tabela_lixeira.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        return pagina

    def atualizar_lixeira(self) -> None:
        if not hasattr(self, "tabela_lixeira"):
            return
        registros = self.db.listar_lixeira()
        self.tabela_lixeira.preencher([
            (str(rid), (formatar_data(excluido), nome, contato, " ".join(desc.split()), status), "neutra")
            for rid, _dh, nome, contato, desc, status, excluido in registros
        ])
        if registros:
            self.tabela_lixeira.esconder_vazio()
        else:
            self.tabela_lixeira.mostrar_vazio(
                "A lixeira está vazia", "Os registros excluídos aparecerão aqui."
            )
        total = len(registros)
        self._total_lixeira = total
        self.nav["lixeira"].definir_texto(f"Lixeira ({total})" if total else "Lixeira")
        self._atualizar_rodape_lixeira()

    def _atualizar_rodape_lixeira(self) -> None:
        texto = plural(getattr(self, "_total_lixeira", 0), "registro na lixeira", "registros na lixeira")
        marcados = len(self.tabela_lixeira.selecionados())
        if marcados:
            texto += f"   •   {plural(marcados, 'selecionado', 'selecionados')}"
        self.lbl_contagem_lixeira.configure(text=texto)

    def _ids_lixeira(self) -> list:
        return [int(i) for i in self.tabela_lixeira.selecionados()]

    def restaurar_selecionados(self) -> None:
        ids = self._ids_lixeira()
        if not ids:
            self.toast.mostrar("Selecione ao menos um registro para restaurar.", "aviso")
            return
        n = self.db.restaurar(ids)
        self.atualizar_tudo()
        self.toast.mostrar(
            f"{plural(n, 'registro restaurado', 'registros restaurados')}.", "sucesso"
        )

    def apagar_definitivamente_selecionados(self) -> None:
        ids = self._ids_lixeira()
        if not ids:
            self.toast.mostrar("Selecione ao menos um registro para apagar.", "aviso")
            return
        destaque = (plural(len(ids), "registro selecionado", "registros selecionados"))
        if not DialogoConfirmacao.perguntar(
            self, "Apagar definitivamente?", destaque,
            "Esta ação não pode ser desfeita: os dados serão apagados de vez.",
            "Apagar",
        ):
            return
        n = self.db.apagar_definitivamente(ids)
        self.atualizar_tudo()
        self.toast.mostrar(
            f"{plural(n, 'registro apagado', 'registros apagados')} definitivamente.", "erro"
        )

    def esvaziar_lixeira(self) -> None:
        total = self.db.contar_lixeira()
        if total == 0:
            self.toast.mostrar("A lixeira já está vazia.", "info")
            return
        if not DialogoConfirmacao.perguntar(
            self, "Esvaziar a lixeira?",
            plural(total, "registro será apagado", "registros serão apagados"),
            "Esta ação não pode ser desfeita: os dados serão apagados de vez.",
            "Esvaziar",
        ):
            return
        n = self.db.esvaziar_lixeira()
        self.atualizar_tudo()
        self.toast.mostrar(f"Lixeira esvaziada ({plural(n, 'registro', 'registros')}).", "erro")

    # ==================================================================
    # Página: Backup
    # ==================================================================
    def _criar_pagina_backup(self, pai) -> ctk.CTkFrame:
        pagina = ctk.CTkFrame(pai, fg_color="transparent")
        self._cabecalho(
            pagina, "Backup",
            "Cópias de segurança dos seus registros, criadas automaticamente.",
        )
        card = self._card(pagina)
        card.pack(fill="both", expand=True, padx=34, pady=(0, 30))

        barra = ctk.CTkFrame(card, fg_color="transparent")
        barra.pack(fill="x", padx=22, pady=(20, 14))
        ctk.CTkButton(
            barra, text="Fazer backup agora", height=40, corner_radius=10,
            image=icone("database", T.SOBRE_COR, 18), compound="left",
            font=fonte(13, "bold"), fg_color=T.TEAL, hover_color=T.TEAL_ESCURO, text_color=T.SOBRE_COR,
            command=self.fazer_backup_agora,
        ).pack(side="left")
        ctk.CTkButton(
            barra, text="Restaurar selecionado", height=40, corner_radius=10,
            image=icone("restore", T.TEAL, 18), compound="left",
            font=fonte(13, "bold"), fg_color="transparent", text_color=T.TEAL,
            border_width=2, border_color=T.TEAL, hover_color=T.TEAL_CLARO,
            command=self.restaurar_backup_selecionado,
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            barra, text="Abrir pasta dos backups", height=40, corner_radius=10,
            font=fonte(13, "bold"), fg_color="transparent", text_color=T.TEXTO,
            border_width=2, border_color=T.BORDA_FORTE, hover_color=T.FUNDO,
            command=lambda: self._abrir_pasta(self.db.pasta_backups()),
        ).pack(side="right")

        rodape = ctk.CTkFrame(card, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=24, pady=(0, 16))
        self.lbl_info_backup = ctk.CTkLabel(
            rodape, text="", font=fonte(12), text_color=T.TEXTO_SUAVE, anchor="w",
            wraplength=760,
        )
        self.lbl_info_backup.pack(anchor="w")

        self._backups_por_iid = {}
        self.tabela_backup = TabelaRegistros(
            card,
            [("data", "Data/Hora", 160, False), ("arquivo", "Arquivo", 330, True),
             ("registros", "Registros", 110, False), ("tamanho", "Tamanho", 110, False)],
            self._px,
        )
        self.tabela_backup.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        return pagina

    def atualizar_backups(self) -> None:
        if not hasattr(self, "tabela_backup"):
            return
        try:
            itens = self.db.listar_backups()
        except OSError as exc:
            itens = []
            self.toast.mostrar(f"Não foi possível ler a pasta de backups: {exc}", "erro", 6000)
        self._backups_por_iid = {str(i): item for i, item in enumerate(itens)}
        self.tabela_backup.preencher([
            (str(i), (item["data"].strftime("%d/%m/%Y %H:%M"), item["nome"],
                      "—" if item["registros"] is None else str(item["registros"]),
                      formatar_tamanho(item["tamanho"])), "neutra")
            for i, item in enumerate(itens)
        ])
        if itens:
            self.tabela_backup.esconder_vazio()
        else:
            self.tabela_backup.mostrar_vazio(
                "Nenhum backup ainda", "Clique em “Fazer backup agora” para criar o primeiro."
            )
        self.lbl_info_backup.configure(
            text=(f"Uma cópia é feita automaticamente ao abrir e ao fechar o programa "
                  f"(últimas {BACKUPS_MANTER} guardadas).  Pasta: {self.db.pasta_backups()}\n"
                  "Dica: de vez em quando, copie a pasta de backups para um pendrive ou outro local.")
        )

    def fazer_backup_agora(self) -> None:
        try:
            caminho = self.db.fazer_backup()
        except Exception as exc:
            self.toast.mostrar(f"Não foi possível criar o backup: {exc}", "erro", 6000)
            return
        self.atualizar_backups()
        self.toast.mostrar(f"Backup criado: {os.path.basename(caminho)}", "sucesso", 5000)

    def restaurar_backup_selecionado(self) -> None:
        marcados = self.tabela_backup.selecionados()
        if not marcados:
            self.toast.mostrar("Selecione um backup na lista para restaurar.", "aviso")
            return
        item = self._backups_por_iid.get(marcados[0])
        if not item:
            return
        confirmou = DialogoConfirmacao.perguntar(
            self, "Restaurar este backup?", resumir(item["nome"], 40),
            "Os registros atuais serão substituídos pelo conteúdo deste backup. "
            "Antes disso, uma cópia de segurança do estado atual será criada.",
            "Restaurar", nome_icone="restore", cor=T.TEAL,
            cor_hover=T.TEAL_ESCURO, cor_clara=T.TEAL_CLARO,
        )
        if not confirmou:
            return
        try:
            seguranca = self.db.restaurar_backup(item["caminho"])
        except ValueError as exc:
            self.toast.mostrar(str(exc), "erro", 6000)
            return
        except Exception as exc:
            self.toast.mostrar(f"Não foi possível restaurar: {exc}", "erro", 6000)
            return
        self.atualizar_tudo()
        self.atualizar_backups()
        self.toast.mostrar(
            f"Backup restaurado. Cópia do estado anterior: {os.path.basename(seguranca)}",
            "sucesso", 7000,
        )
