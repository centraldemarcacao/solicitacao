"""
preferencias.py
---------------
Preferências do usuário (tema, tamanho da janela, ordenação e filtros),
guardadas em dados/preferencias.json. Nunca impedem o programa de abrir:
arquivo ausente, vazio ou corrompido volta aos padrões.
"""

import json
import os


class Preferencias:
    def __init__(self, caminho: str) -> None:
        self.caminho = caminho
        self.dados = self._ler()

    def _ler(self) -> dict:
        try:
            with open(self.caminho, encoding="utf-8") as arq:
                dados = json.load(arq)
            return dados if isinstance(dados, dict) else {}
        except (OSError, ValueError):
            return {}

    def get(self, chave: str, padrao=None):
        return self.dados.get(chave, padrao)

    def definir(self, **valores) -> None:
        self.dados.update(valores)

    def salvar(self) -> bool:
        """Grava com segurança (arquivo temporário + troca). False se não foi possível."""
        temporario = self.caminho + ".tmp"
        try:
            with open(temporario, "w", encoding="utf-8") as arq:
                json.dump(self.dados, arq, ensure_ascii=False, indent=2)
            os.replace(temporario, self.caminho)
            return True
        except OSError:
            try:
                os.remove(temporario)
            except OSError:
                pass
            return False
