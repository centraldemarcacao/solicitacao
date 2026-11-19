"""
prazos.py
---------
Atalhos do campo "Retornar em" (Amanhã, 3 dias, 7 dias...), configuráveis pelo usuário e
guardados em preferencias.json (`prazos_retorno`). Sem interface e sem dependências.
"""

import re


# --- atalhos de "Retornar em" (configuráveis) ------------------------------
PRAZOS_PADRAO = (1, 3, 7)     # amanhã, 3 dias, 7 dias
MAX_PRAZOS = 4                # quantos atalhos cabem na linha do formulário
MAX_DIAS_PRAZO = 365


def validar_prazos(dados) -> list:
    """Lista de dias (inteiros de 1 a 365, sem repetir, em ordem crescente, no máximo
    MAX_PRAZOS). Ausente, inválida ou vazia volta ao padrão."""
    if not isinstance(dados, (list, tuple)):
        return list(PRAZOS_PADRAO)
    dias = {d for d in dados if isinstance(d, int) and not isinstance(d, bool)
            and 1 <= d <= MAX_DIAS_PRAZO}
    return sorted(dias)[:MAX_PRAZOS] or list(PRAZOS_PADRAO)


def interpretar_prazos(texto: str) -> list:
    """'1, 3, 7' (ou separados por espaço/ponto e vírgula) -> [1, 3, 7].
    Levanta ValueError com a mensagem para o usuário se algo estiver errado."""
    partes = [p for p in re.split(r"[,;\s]+", (texto or "").strip()) if p]
    if not partes:
        raise ValueError("Informe ao menos um prazo, em dias (ex.: 1, 3, 7).")
    dias = []
    for parte in partes:
        if not parte.isdigit():
            raise ValueError(f"\"{parte}\" não é um número de dias. Use algo como 1, 3, 7.")
        dia = int(parte)
        if not 1 <= dia <= MAX_DIAS_PRAZO:
            raise ValueError(f"Cada prazo deve ficar entre 1 e {MAX_DIAS_PRAZO} dias.")
        dias.append(dia)
    unicos = sorted(set(dias))
    if len(unicos) > MAX_PRAZOS:
        raise ValueError(f"Use no máximo {MAX_PRAZOS} prazos.")
    return unicos


def prazos_para_texto(prazos) -> str:
    return ", ".join(str(d) for d in validar_prazos(prazos))


def rotulo_prazo(dias: int) -> str:
    """Texto do botão de atalho: 1 -> 'Amanhã'; 3 -> '3 dias'."""
    return "Amanhã" if dias == 1 else f"{dias} dias"
