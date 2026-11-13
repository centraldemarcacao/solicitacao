"""
registro_log.py
---------------
Registro de falhas em arquivo (`erros.log`, na pasta de dados) com rotação.

Antes, falhas "silenciosas" (`except: pass`) sumiam sem deixar rastro e o arquivo
crescia sem limite. Agora cada módulo usa `log = logging.getLogger(__name__)` e este
módulo liga um único arquivo rotativo (512 KB, 3 cópias antigas: erros.log.1 ... .3).

Uso:
    from anotacoes.nucleo import registro_log
    registro_log.configurar(pasta_de_dados)     # uma vez, ao iniciar
"""

import logging
import logging.handlers
import os
from typing import Optional

NOME_ARQUIVO = "erros.log"
MAX_BYTES = 512 * 1024
COPIAS = 3
RAIZ = "anotacoes"
FORMATO = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"

_manipulador: Optional[logging.Handler] = None


def configurar(pasta: str, nivel: int = logging.INFO) -> Optional[str]:
    """Liga o registro em `pasta/erros.log`. Pode ser chamada de novo (troca o destino).

    Retorna o caminho do arquivo, ou None se a pasta não aceitar gravação (nesse caso
    o programa segue funcionando, só sem registro em arquivo).
    """
    global _manipulador
    desligar()
    caminho = os.path.join(pasta, NOME_ARQUIVO)
    try:
        os.makedirs(pasta, exist_ok=True)
        manipulador = logging.handlers.RotatingFileHandler(
            caminho, maxBytes=MAX_BYTES, backupCount=COPIAS, encoding="utf-8", delay=True)
    except OSError:
        return None
    manipulador.setFormatter(logging.Formatter(FORMATO, FORMATO_DATA))
    manipulador.setLevel(nivel)
    raiz = logging.getLogger(RAIZ)
    raiz.setLevel(nivel)
    raiz.addHandler(manipulador)
    logging.raiseExceptions = False     # falha ao gravar o log nunca derruba o programa
    _manipulador = manipulador
    return caminho


def desligar() -> None:
    """Fecha o arquivo de log (usado ao reconfigurar e nos testes)."""
    global _manipulador
    if _manipulador is not None:
        logging.getLogger(RAIZ).removeHandler(_manipulador)
        try:
            _manipulador.close()
        except Exception:        # noqa: BLE001 - fechar o log não pode falhar para ninguém
            pass
        _manipulador = None
