"""
diagnostico.py
--------------
Informações do programa e testes de conexão (GitHub e Supabase), com mensagens que
dizem O QUE fazer. Sem interface (veja interface/mixins/configuracoes.py).

Nada daqui envia ou mostra dados de pacientes.
"""

import json
import os
import platform
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional, Tuple

from anotacoes.atualizacao import updater
from anotacoes.nucleo.certificados import MENSAGEM_CERTIFICADO, contexto_ssl, erro_de_certificado

OK, AVISO, ERRO, PULADO = "ok", "aviso", "erro", "pulado"


@dataclass
class Resultado:
    nome: str
    estado: str           # OK, AVISO, ERRO ou PULADO
    mensagem: str
    ms: int = 0


def _explicar_falha(exc: BaseException) -> str:
    """Traduz uma falha de rede em uma frase com a ação sugerida."""
    if erro_de_certificado(exc):
        return MENSAGEM_CERTIFICADO
    motivo = getattr(exc, "reason", exc)
    if isinstance(motivo, socket.gaierror):
        return ("Não foi possível encontrar o servidor (DNS). Verifique a internet; "
                "a rede da instituição pode estar bloqueando o endereço.")
    if isinstance(motivo, (TimeoutError, socket.timeout)):
        return "O servidor demorou demais para responder. Tente de novo; pode ser a rede ou um bloqueio."
    if isinstance(motivo, ConnectionRefusedError):
        return "A conexão foi recusada (firewall ou proxy da instituição)."
    return f"Sem conexão ({motivo})."


def testar_github(repositorio: str, timeout: float = 8) -> Resultado:
    nome = "GitHub (atualizações)"
    inicio = time.monotonic()
    try:
        info = updater.buscar_ultima(repositorio, timeout)
    except updater.ErroAtualizacao as exc:
        causa = exc.__cause__
        msg = (_explicar_falha(causa) if causa is not None and not isinstance(causa, urllib.error.HTTPError)
               else str(exc))
        if isinstance(causa, urllib.error.HTTPError):
            msg = {403: "O GitHub limitou as consultas (tente de novo em alguns minutos).",
                   404: "Repositório ou versão não encontrados (o repositório precisa ser público)."
                   }.get(causa.code, f"O GitHub respondeu com erro {causa.code}.")
        return Resultado(nome, ERRO, msg, int((time.monotonic() - inicio) * 1000))
    ms = int((time.monotonic() - inicio) * 1000)
    if info is None:
        return Resultado(nome, AVISO, "Conectado, mas não há versão publicada com .exe e SHA256.txt.", ms)
    return Resultado(nome, OK, f"Conectado. Última versão publicada: {info.versao}.", ms)


def testar_supabase(url: Optional[str], chave: Optional[str], timeout: float = 8) -> Resultado:
    nome = "Supabase (nuvem)"
    if not url or not chave:
        return Resultado(nome, PULADO, "Nuvem não configurada (é opcional).")
    inicio = time.monotonic()
    pedido = urllib.request.Request(url.rstrip("/") + "/auth/v1/health", headers={
        "apikey": chave, "User-Agent": "AnotacoesHospitalares"})
    try:
        with urllib.request.urlopen(pedido, timeout=timeout, context=contexto_ssl()):
            pass
    except urllib.error.HTTPError as exc:
        ms = int((time.monotonic() - inicio) * 1000)
        if exc.code in (401, 403):
            return Resultado(nome, AVISO, "O servidor respondeu, mas recusou a chave. "
                             "Confira a chave na página Nuvem.", ms)
        return Resultado(nome, ERRO, f"O servidor respondeu com erro {exc.code}.", ms)
    except Exception as exc:
        return Resultado(nome, ERRO, _explicar_falha(exc), int((time.monotonic() - inicio) * 1000))
    return Resultado(nome, OK, "Conectado.", int((time.monotonic() - inicio) * 1000))


def ultima_linha(caminho: str) -> Optional[str]:
    """Última linha não vazia de um arquivo de texto (ex.: atualizacao.log), ou None."""
    try:
        with open(caminho, "rb") as arq:
            arq.seek(0, os.SEEK_END)
            tamanho = arq.tell()
            arq.seek(max(0, tamanho - 4096))
            linhas = arq.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for linha in reversed(linhas):
        if linha.strip():
            return linha.strip()
    return None


def _tamanho(caminho: str) -> str:
    try:
        bytes_ = os.path.getsize(caminho)
    except OSError:
        return "não encontrado"
    return f"{bytes_ / 1024:.0f} KB" if bytes_ < 1024 * 1024 else f"{bytes_ / (1024 * 1024):.1f} MB"


def linhas_informacao(versao: str, caminho_banco: str, pasta_backups: str,
                      protecao_ativa: bool, inicio_windows: Optional[bool],
                      cripto_disponivel: bool) -> List[Tuple[str, str]]:
    """[(rótulo, valor)] para a página de diagnóstico (sem dados de pacientes)."""
    pasta_dados = os.path.dirname(caminho_banco)
    try:
        backups = [n for n in os.listdir(pasta_backups) if n.endswith((".db", ".dbx"))]
    except OSError:
        backups = []
    cifrados = sum(1 for n in backups if n.endswith(".dbx"))
    exe = sys.executable if getattr(sys, "frozen", False) else "(modo desenvolvimento)"
    linhas = [
        ("Versão do programa", versao),
        ("Programa", exe),
        ("Sistema", f"{platform.system()} {platform.release()} ({platform.machine()})"),
        ("Python", platform.python_version()),
        ("Pasta de dados", pasta_dados),
        ("Banco de dados", f"{os.path.basename(caminho_banco)} — {_tamanho(caminho_banco)}"),
        ("Backups", f"{len(backups)} arquivo(s), {cifrados} criptografado(s)"),
        ("Proteção por PIN", "ativada" if protecao_ativa else "desativada"),
        ("Criptografia de backups", "disponível" if cripto_disponivel else "indisponível neste computador"),
        ("Iniciar com o Windows",
         "indisponível (só no programa instalado)" if inicio_windows is None
         else "ligado" if inicio_windows else "desligado"),
    ]
    for rotulo, nome in (("Último registro de erro", "erros.log"),
                         ("Última atualização", "atualizacao.log")):
        caminho = os.path.join(pasta_dados, nome)
        if nome == "atualizacao.log" and not os.path.exists(caminho) and getattr(sys, "frozen", False):
            caminho = os.path.join(os.path.dirname(sys.executable), nome)
        linhas.append((rotulo, ultima_linha(caminho) or "nenhum"))
    return linhas
