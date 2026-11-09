"""
Onde ficam as coisas: pasta do programa, pasta de dados e arquivos de recursos.

  * Executável (PyInstaller): a pasta do .exe.
  * Desenvolvimento: a raiz do repositório (a pasta que contém `anotacoes/`).
"""

import os
import sys
from typing import List, Optional


def empacotado() -> bool:
    """True quando rodando como .exe gerado pelo PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def pasta_programa() -> str:
    """Pasta do .exe (ou a raiz do repositório, em desenvolvimento)."""
    if empacotado():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def localizar_arquivo(nome: str) -> Optional[str]:
    """Procura um recurso (ex.: icone.ico, logo.png): ao lado do .exe, dentro do
    pacote do PyInstaller ou em `assets/`, em desenvolvimento."""
    pastas: List[str] = [pasta_programa()]
    if hasattr(sys, "_MEIPASS"):
        pastas.append(sys._MEIPASS)
    pastas.append(os.path.join(pasta_programa(), "assets"))
    for pasta in pastas:
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho):
            return caminho
    return None
