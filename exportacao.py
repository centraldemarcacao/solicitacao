"""
exportacao.py
-------------
Exportar a lista para CSV (Excel) e imprimir. Usa os registros que estão na
tabela do Histórico (já filtrados e ordenados); se houver linhas selecionadas,
usa somente elas.
"""

import os
from tkinter import filedialog

import exportar
from util import plural


class ExportacaoMixin:
    """Requer: self.tabela, self._registros_exibidos, self.toast, self._descricao_filtro."""

    def _registros_para_saida(self):
        """(registros, texto) — as linhas selecionadas ou, sem seleção, todas as exibidas."""
        todos = self._registros_exibidos
        marcados = set(self.tabela.selecionados())
        if marcados:
            return [r for r in todos if str(r[0]) in marcados], "selecionados"
        return list(todos), "exibidos"

    def exportar_csv(self) -> None:
        registros, quais = self._registros_para_saida()
        if not registros:
            self.toast.mostrar("Não há registros para exportar.", "aviso")
            return
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Exportar para Excel (CSV)", defaultextension=".csv",
            initialfile=exportar.nome_sugerido("solicitacoes", ".csv"),
            filetypes=[("Planilha CSV (abre no Excel)", "*.csv")],
        )
        if not caminho:
            return
        try:
            total = exportar.exportar_csv(registros, caminho)
        except OSError as exc:
            self.toast.mostrar(f"Não foi possível salvar o arquivo: {exc}", "erro", 7000)
            return
        self.toast.mostrar(
            f"{plural(total, 'registro exportado', 'registros exportados')} "
            f"para {os.path.basename(caminho)}.", "sucesso", 5000)

    def imprimir_lista(self) -> None:
        registros, quais = self._registros_para_saida()
        if not registros:
            self.toast.mostrar("Não há registros para imprimir.", "aviso")
            return
        caminho = exportar.caminho_temporario_impressao()
        try:
            exportar.gerar_html_impressao(registros, self._descricao_filtro(), caminho)
            if hasattr(os, "startfile"):
                os.startfile(caminho)
            else:
                import webbrowser
                webbrowser.open("file://" + caminho)
        except Exception as exc:
            self.toast.mostrar(f"Não foi possível preparar a impressão: {exc}", "erro", 7000)
            return
        self.toast.mostrar(
            f"Lista com {plural(len(registros), 'registro', 'registros')} aberta no "
            "navegador para impressão.", "info", 5000)
