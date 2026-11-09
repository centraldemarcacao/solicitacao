"""
exportar.py
-----------
Exportação da lista de registros: CSV (abre direto no Excel) e página HTML
pronta para imprimir. Somente biblioteca padrão.
"""

import csv
import html
import os
import tempfile
from datetime import datetime

from anotacoes import theme as T
from anotacoes.nucleo.identidade import titulo_completo
from anotacoes.nucleo.util import formatar_data, formatar_lembrete, plural

CABECALHO = ("Nº", "Data/Hora", "Nome", "Contato", "Descrição", "Status", "Retorno",
             "Prioridade")


def _linha(reg) -> tuple:
    rid, data_hora, nome, contato, descricao, status, lembrete, prioridade = reg
    return (rid, formatar_data(data_hora), nome, contato or "", descricao,
            status, formatar_lembrete(lembrete), prioridade)


def _seguro_para_planilha(valor):
    """Evita que o Excel interprete texto como fórmula (=, +, -, @)."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor
    return valor


def exportar_csv(registros, caminho: str) -> int:
    """Grava CSV (UTF-8 com BOM, separador ';' — padrão do Excel em português)."""
    with open(caminho, "w", encoding="utf-8-sig", newline="") as arq:
        escritor = csv.writer(arq, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        escritor.writerow(CABECALHO)
        for reg in registros:
            escritor.writerow([_seguro_para_planilha(c) for c in _linha(reg)])
    return len(registros)


def nome_sugerido(prefixo: str, extensao: str) -> str:
    return f"{prefixo}_{datetime.now():%Y-%m-%d_%H%M}{extensao}"


_ESTILO = """
body{font-family:'Segoe UI',Arial,sans-serif;color:#13293D;margin:28px}
h1{font-size:20px;margin:0 0 2px;color:#0B2A43}
p.sub{margin:0 0 16px;color:#52677A;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{background:#0B2A43;color:#fff;text-align:left;padding:7px 8px}
td{border-bottom:1px solid #D3DEE6;padding:7px 8px;vertical-align:top}
td.desc{white-space:pre-wrap}
tr{page-break-inside:avoid}
.urgente{color:#B42318;font-weight:700}.pendente{color:#B45309;font-weight:600}.atendida{color:#17744E;font-weight:600}
@media print{body{margin:10mm}th{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def gerar_html_impressao(registros, filtro_descricao: str, caminho: str) -> int:
    """Cria a página de impressão (abre a caixa de impressão ao carregar)."""
    esc = html.escape
    linhas = []
    for reg in registros:
        rid, data, nome, contato, desc, status, retorno, prioridade = _linha(reg)
        classe = "atendida" if status == "Atendida" else "pendente"
        linhas.append(
            f"<tr><td>{rid}</td><td>{esc(data)}</td><td>{esc(nome)}</td>"
            f"<td>{esc(contato)}</td><td class='desc'>{esc(desc)}</td>"
            f"<td class='{classe}'>{esc(status)}</td><td>{esc(retorno)}</td>"
            f"<td class='{'urgente' if prioridade == 'Urgente' else ''}'>{esc(prioridade)}</td></tr>"
        )
    cab = "".join(f"<th>{esc(c)}</th>" for c in CABECALHO)
    texto = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        f"<title>{esc(T.SUBTITULO or T.NOME_INSTITUICAO)}</title><style>{_ESTILO}</style></head><body>"
        f"<h1>{esc(titulo_completo())}</h1>"
        f"<p class='sub'>{esc(filtro_descricao)} • {plural(len(registros), 'registro', 'registros')} • "
        f"emitido em {datetime.now():%d/%m/%Y %H:%M}</p>"
        f"<table><thead><tr>{cab}</tr></thead><tbody>{''.join(linhas)}</tbody></table>"
        "<script>window.onload=function(){setTimeout(function(){window.print()},300)}</script>"
        "</body></html>"
    )
    with open(caminho, "w", encoding="utf-8") as arq:
        arq.write(texto)
    return len(registros)


def caminho_temporario_impressao() -> str:
    pasta = tempfile.mkdtemp(prefix="impressao_")
    return os.path.join(pasta, "lista_para_imprimir.html")
