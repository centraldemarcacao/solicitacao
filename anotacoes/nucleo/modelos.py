"""
modelos.py
----------
Modelos de descrição: frases prontas para pedidos frequentes ("Solicita água."), inseridas
com um clique no formulário. Sem interface. Ficam em preferencias.json (`modelos_descricao`).
"""

from typing import Any, List, Optional

MAX_MODELOS = 10
MAX_TITULO = 24
MAX_TEXTO = 300

MODELOS_PADRAO = (
    {"titulo": "Água", "texto": "Solicita água."},
    {"titulo": "Travesseiro", "texto": "Solicita travesseiro."},
    {"titulo": "Cobertor", "texto": "Solicita cobertor."},
    {"titulo": "Acompanhante", "texto": "Solicita acompanhante."},
    {"titulo": "Retornar ligação", "texto": "Solicita retorno de ligação."},
)


def padrao() -> List[dict]:
    return [dict(m) for m in MODELOS_PADRAO]


def validar_modelos(dados: Any) -> List[dict]:
    """Lista de {"titulo", "texto"} aceitável. Ausente/inválido (não é lista) -> padrão;
    lista vazia é respeitada (o usuário apagou todos). Itens ruins são descartados."""
    if not isinstance(dados, list):
        return padrao()
    saida, vistos = [], set()
    for item in dados:
        if not isinstance(item, dict):
            continue
        titulo, texto = item.get("titulo"), item.get("texto")
        if not isinstance(titulo, str) or not isinstance(texto, str):
            continue
        titulo, texto = " ".join(titulo.split())[:MAX_TITULO], texto.strip()[:MAX_TEXTO]
        if not titulo or not texto or titulo.lower() in vistos:
            continue
        vistos.add(titulo.lower())
        saida.append({"titulo": titulo, "texto": texto})
        if len(saida) >= MAX_MODELOS:
            break
    return saida


def texto_com_modelo(atual: str, modelo: str, limite: int) -> Optional[str]:
    """Descrição resultante ao inserir `modelo` (em nova linha, se já há texto).
    None se passar de `limite` caracteres."""
    atual = (atual or "").strip()
    novo = modelo if not atual else f"{atual}\n{modelo}"
    return novo if len(novo) <= limite else None
