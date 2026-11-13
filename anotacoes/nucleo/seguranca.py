"""
seguranca.py
------------
PIN (ou senha) de acesso, bloqueio por inatividade e criptografia dos backups.
Sem interface (veja interface/mixins/bloqueio.py).

O QUE PROTEGE
  * O PIN impede que outra pessoa USE o programa aberto (a tela fica bloqueada).
  * Os backups são gravados criptografados (AES-256-GCM) com a mesma senha.

O QUE NÃO PROTEGE
  * O banco "em uso" (anotacoes_hospitalares.db, na pasta de dados) continua legível para quem tiver acesso à
    pasta do programa. Para isso, use também a proteção do Windows (conta de usuário
    com senha, BitLocker). O PIN é uma barreira contra o acesso casual.
  * "Esqueci o PIN": quem tem acesso à pasta pode apagar `seguranca.json` e o programa
    volta a abrir sem PIN. Os backups criptografados, porém, só abrem com a senha usada
    ao criá-los: guarde-a.

Detalhes: o PIN é guardado só como hash (scrypt com sal aleatório); a chave de cada
backup é derivada da senha com scrypt e um sal próprio do arquivo, então o backup abre
em qualquer computador que conheça a senha.
"""

import logging
import hashlib
import hmac
import os
import secrets
from typing import Optional

from anotacoes.nucleo.preferencias import Preferencias

log = logging.getLogger(__name__)

NOME_ARQUIVO = "seguranca.json"
EXTENSAO_CRIPTOGRAFADO = ".dbx"
MAGIA = b"LCCBK1"                         # cabeçalho dos backups criptografados
TAM_SAL, TAM_NONCE = 16, 12
_N, _R, _P = 2 ** 15, 8, 1               # custo do scrypt (~0,1 s)
_MAXMEM = 128 * 1024 * 1024

MIN_CARACTERES, MAX_CARACTERES = 4, 64
OPCOES_BLOQUEIO = (1, 2, 5, 10, 15, 30)  # minutos sem uso até bloquear
BLOQUEIO_PADRAO = 5


class ErroCriptografia(ValueError):
    """Arquivo ilegível ou não criptografado por este programa."""


class SenhaIncorreta(ErroCriptografia):
    pass


# ----------------------------------------------------------------------
# Derivação e validação
# ----------------------------------------------------------------------
def _derivar(segredo: str, sal: bytes) -> bytes:
    return hashlib.scrypt(segredo.encode("utf-8"), salt=sal, n=_N, r=_R, p=_P,
                          maxmem=_MAXMEM, dklen=32)


def validar_segredo(texto: str) -> Optional[str]:
    """None se o PIN/senha é aceitável; senão, a mensagem de erro."""
    if not isinstance(texto, str) or len(texto) < MIN_CARACTERES:
        return f"Use pelo menos {MIN_CARACTERES} caracteres."
    if len(texto) > MAX_CARACTERES:
        return f"Use no máximo {MAX_CARACTERES} caracteres."
    return None


def segredo_fraco(texto: str) -> bool:
    """True se é curto demais para proteger bem os backups (menos de 8 caracteres)."""
    return len(texto) < 8


# ----------------------------------------------------------------------
# Criptografia de arquivos (backups)
# ----------------------------------------------------------------------
def criptografia_disponivel() -> bool:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
        return True
    except Exception:
        return False


def criptografar(dados: bytes, segredo: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    sal, nonce = secrets.token_bytes(TAM_SAL), secrets.token_bytes(TAM_NONCE)
    cifrado = AESGCM(_derivar(segredo, sal)).encrypt(nonce, dados, MAGIA)
    return MAGIA + sal + nonce + cifrado


def descriptografar(blob: bytes, segredo: str) -> bytes:
    if not blob.startswith(MAGIA) or len(blob) < len(MAGIA) + TAM_SAL + TAM_NONCE + 16:
        raise ErroCriptografia("O arquivo não é um backup criptografado deste programa.")
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    inicio = len(MAGIA)
    sal = blob[inicio:inicio + TAM_SAL]
    nonce = blob[inicio + TAM_SAL:inicio + TAM_SAL + TAM_NONCE]
    cifrado = blob[inicio + TAM_SAL + TAM_NONCE:]
    try:
        return AESGCM(_derivar(segredo, sal)).decrypt(nonce, cifrado, MAGIA)
    except InvalidTag:
        raise SenhaIncorreta("Senha incorreta (ou o backup está danificado).") from None


def arquivo_criptografado(caminho: str) -> bool:
    try:
        with open(caminho, "rb") as arq:
            return arq.read(len(MAGIA)) == MAGIA
    except OSError:
        return False


def _gravar_atomico(destino: str, dados: bytes) -> None:
    provisorio = destino + ".tmp"
    try:
        with open(provisorio, "wb") as arq:
            arq.write(dados)
        os.replace(provisorio, destino)
    except BaseException:
        try:
            os.remove(provisorio)
        except OSError:
            log.debug("Falha ignorada em _gravar_atomico()", exc_info=True)
        raise


def criptografar_arquivo(origem: str, destino: str, segredo: str) -> None:
    with open(origem, "rb") as arq:
        dados = arq.read()
    _gravar_atomico(destino, criptografar(dados, segredo))


def descriptografar_arquivo(origem: str, destino: str, segredo: str) -> None:
    with open(origem, "rb") as arq:
        blob = arq.read()
    _gravar_atomico(destino, descriptografar(blob, segredo))


# ----------------------------------------------------------------------
# Configuração (seguranca.json, na pasta de dados)
# ----------------------------------------------------------------------
class Seguranca:
    def __init__(self, caminho: str) -> None:
        self._cfg = Preferencias(caminho)

    @property
    def ativa(self) -> bool:
        return bool(self._cfg.get("hash") and self._cfg.get("sal"))

    def ativar(self, segredo: str, criptografar_backups: bool = True,
               bloqueio_minutos: Optional[int] = None) -> bool:
        """Define (ou troca) o PIN/senha. Retorna False se não foi possível gravar."""
        erro = validar_segredo(segredo)
        if erro:
            raise ValueError(erro)
        sal = secrets.token_bytes(TAM_SAL)
        minutos = bloqueio_minutos if bloqueio_minutos is not None else self.bloqueio_minutos
        self._cfg.definir(
            versao=1, sal=sal.hex(), hash=_derivar(segredo, sal).hex(),
            criptografar_backups=bool(criptografar_backups and criptografia_disponivel()),
            bloqueio_minutos=minutos if minutos in OPCOES_BLOQUEIO else BLOQUEIO_PADRAO)
        return self._cfg.salvar()

    def verificar(self, segredo: str) -> bool:
        if not self.ativa or not isinstance(segredo, str):
            return False
        try:
            esperado = bytes.fromhex(self._cfg.get("hash"))
            calculado = _derivar(segredo, bytes.fromhex(self._cfg.get("sal")))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(esperado, calculado)

    def desativar(self) -> bool:
        for chave in ("sal", "hash", "criptografar_backups"):
            self._cfg.dados.pop(chave, None)
        return self._cfg.salvar()

    @property
    def criptografar_backups(self) -> bool:
        return (self.ativa and self._cfg.get("criptografar_backups") is True
                and criptografia_disponivel())

    def definir_criptografar_backups(self, ativo: bool) -> bool:
        self._cfg.definir(criptografar_backups=bool(ativo and criptografia_disponivel()))
        return self._cfg.salvar()

    @property
    def bloqueio_minutos(self) -> int:
        valor = self._cfg.get("bloqueio_minutos", BLOQUEIO_PADRAO)
        return valor if valor in OPCOES_BLOQUEIO else BLOQUEIO_PADRAO

    def definir_bloqueio_minutos(self, minutos: int) -> bool:
        self._cfg.definir(bloqueio_minutos=minutos if minutos in OPCOES_BLOQUEIO
                          else BLOQUEIO_PADRAO)
        return self._cfg.salvar()


class LimiteTentativas:
    """Espera crescente após erros de PIN (só em memória; reabrir o programa zera,
    o que é aceitável para uma barreira contra o acesso casual)."""

    ESPERAS = ((3, 5), (5, 30), (8, 120))     # (a partir de N erros, segundos de espera)

    def __init__(self, relogio=None) -> None:
        import time
        self._agora = relogio or time.monotonic
        self.erros = 0
        self._libera_em = 0.0

    def segundos_restantes(self) -> int:
        return max(0, int(round(self._libera_em - self._agora())))

    def errou(self) -> None:
        self.erros += 1
        espera = 0
        for a_partir, segundos in self.ESPERAS:
            if self.erros >= a_partir:
                espera = segundos
        self._libera_em = self._agora() + espera

    def acertou(self) -> None:
        self.erros = 0
        self._libera_em = 0.0
