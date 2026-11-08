"""
perfil.py
---------
Perfil da empresa: nome e subtítulo mostrados no programa, na janela e na
página de impressão.

O programa lê o arquivo `perfil.json` que fica AO LADO do executável (ou deste
arquivo, em desenvolvimento). Sem o arquivo, vale o padrão (Liga Contra o Câncer).

Exemplo de perfil.json:
    {
      "nome": "Intesoftware Desenvolvimento",
      "subtitulo": "Anotações de clientes"
    }

Cada pasta com o programa tem os seus próprios dados (pasta `dados`), então
duas pastas com perfis diferentes nunca se misturam. A atualização automática
troca só o .exe e preserva o perfil.json.
"""

import json
import os
import sys
from typing import Optional

import theme as T

ARQUIVO = "perfil.json"
MAX_NOME = 40
MAX_SUBTITULO = 40

PADRAO = {"nome": "Liga Contra o Câncer", "subtitulo": "Solicitações de pacientes"}


def pasta_base() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _texto(valor, limite: int) -> Optional[str]:
    if not isinstance(valor, str):
        return None
    valor = " ".join(valor.split())
    if not valor:
        return None
    return valor[:limite]


def carregar(base: Optional[str] = None) -> dict:
    """Lê o perfil. Arquivo ausente, ilegível ou com campos inválidos nunca
    impede o programa de abrir: o que não servir é substituído pelo padrão."""
    perfil = dict(PADRAO)
    caminho = os.path.join(base or pasta_base(), ARQUIVO)
    try:
        with open(caminho, encoding="utf-8-sig") as arq:
            dados = json.load(arq)
    except (OSError, ValueError):
        return perfil
    if not isinstance(dados, dict):
        return perfil
    nome = _texto(dados.get("nome"), MAX_NOME)
    subtitulo = _texto(dados.get("subtitulo"), MAX_SUBTITULO)
    if nome:
        perfil["nome"] = nome
    if subtitulo:
        perfil["subtitulo"] = subtitulo
    return perfil


def aplicar(base: Optional[str] = None) -> dict:
    """Carrega o perfil e o coloca em uso (theme.NOME_INSTITUICAO / SUBTITULO)."""
    perfil = carregar(base)
    T.NOME_INSTITUICAO = perfil["nome"]
    T.SUBTITULO = perfil["subtitulo"]
    return perfil
