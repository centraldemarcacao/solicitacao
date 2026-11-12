"""
updater.py
----------
Atualização automática pelo GitHub Releases (somente biblioteca padrão).

Fluxo: consulta a última versão publicada -> baixa o novo .exe -> confere o
SHA-256 -> troca o arquivo quando o programa fecha -> reabre já atualizado.
Os dados (pasta "dados") nunca são tocados.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from anotacoes.nucleo.certificados import MENSAGEM_CERTIFICADO, contexto_ssl, erro_de_certificado

NOME_EXE = "AnotacoesHospitalares.exe"
NOME_HASH = "SHA256.txt"
HOSTS_PERMITIDOS = ("github.com", "githubusercontent.com")
LIMITE_TAMANHO = 300 * 1024 * 1024   # recusa arquivos absurdamente grandes


class ErroAtualizacao(Exception):
    """Falha previsível (rede, arquivo inválido...) com mensagem para o usuário."""


@dataclass
class InfoAtualizacao:
    versao: str
    notas: str
    url_exe: str
    url_hash: str
    tamanho: int


def versao_para_tupla(texto: str) -> tuple:
    """'v2.10.1' -> (2, 10, 1). Texto sem números -> ()."""
    return tuple(int(n) for n in re.findall(r"\d+", texto or ""))


def e_mais_nova(remota: str, local: str) -> bool:
    r, l = versao_para_tupla(remota), versao_para_tupla(local)
    return bool(r) and r > l


def _url_segura(url: str) -> bool:
    partes = urlparse(url or "")
    host = (partes.hostname or "").lower()
    return partes.scheme == "https" and any(
        host == h or host.endswith("." + h) for h in HOSTS_PERMITIDOS
    )


def _abrir(url: str, timeout: float):
    if not _url_segura(url):
        raise ErroAtualizacao("Endereço de atualização não confiável.")
    req = urllib.request.Request(url, headers={
        "User-Agent": "AnotacoesHospitalares-Updater",
        "Accept": "application/vnd.github+json, application/octet-stream",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=contexto_ssl())
    except Exception as exc:
        if erro_de_certificado(exc):
            raise ErroAtualizacao(MENSAGEM_CERTIFICADO) from exc
        raise ErroAtualizacao(f"Sem acesso ao servidor de atualizações ({exc}).") from exc
    if not _url_segura(resp.geturl()):
        resp.close()
        raise ErroAtualizacao("Redirecionamento para endereço não confiável.")
    return resp


def buscar_ultima(repositorio: str, timeout: float = 8) -> "InfoAtualizacao | None":
    """Dados da última versão publicada, ou None se não houver release utilizável."""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repositorio or ""):
        raise ErroAtualizacao("Repositório de atualizações não configurado.")
    with _abrir(f"https://api.github.com/repos/{repositorio}/releases/latest", timeout) as r:
        try:
            dados = json.loads(r.read(2_000_000).decode("utf-8"))
        except ValueError as exc:
            raise ErroAtualizacao("Resposta inválida do servidor.") from exc
    return interpretar_release(dados)


def interpretar_release(dados: dict) -> "InfoAtualizacao | None":
    assets = {a.get("name"): a for a in dados.get("assets", []) if isinstance(a, dict)}
    exe, hash_ = assets.get(NOME_EXE), assets.get(NOME_HASH)
    tag = dados.get("tag_name") or ""
    if not (exe and hash_ and versao_para_tupla(tag)):
        return None  # sem .exe ou sem assinatura: não é seguro atualizar
    return InfoAtualizacao(
        versao=tag.lstrip("vV"),
        notas=(dados.get("body") or "").strip(),
        url_exe=exe.get("browser_download_url", ""),
        url_hash=hash_.get("browser_download_url", ""),
        tamanho=int(exe.get("size") or 0),
    )


def _hash_esperado(info: InfoAtualizacao, timeout: float) -> str:
    with _abrir(info.url_hash, timeout) as r:
        texto = r.read(4096).decode("utf-8", "ignore")
    achado = re.search(r"\b[0-9a-fA-F]{64}\b", texto)
    if not achado:
        raise ErroAtualizacao("Assinatura SHA-256 ausente na publicação.")
    return achado.group(0).lower()


def baixar(info: InfoAtualizacao, pasta: str, progresso=None, cancelar=None,
           timeout: float = 20) -> str:
    """Baixa e confere o novo .exe. Retorna o caminho do arquivo verificado."""
    if info.tamanho > LIMITE_TAMANHO:
        raise ErroAtualizacao("Arquivo de atualização grande demais.")
    esperado = _hash_esperado(info, timeout)
    destino = os.path.join(pasta, "AnotacoesHospitalares.novo.exe")
    parcial = destino + ".part"
    sha = hashlib.sha256()
    baixados = 0
    try:
        with _abrir(info.url_exe, timeout) as r, open(parcial, "wb") as f:
            total = int(r.headers.get("Content-Length") or info.tamanho or 0)
            while True:
                if cancelar is not None and cancelar.is_set():
                    raise ErroAtualizacao("Atualização cancelada.")
                bloco = r.read(256 * 1024)
                if not bloco:
                    break
                baixados += len(bloco)
                if baixados > LIMITE_TAMANHO:
                    raise ErroAtualizacao("Arquivo de atualização grande demais.")
                sha.update(bloco)
                f.write(bloco)
                if progresso and total:
                    progresso(min(1.0, baixados / total))
        if sha.hexdigest() != esperado:
            raise ErroAtualizacao("O arquivo baixado não confere com a assinatura (SHA-256).")
        with open(parcial, "rb") as f:
            if f.read(2) != b"MZ":
                raise ErroAtualizacao("O arquivo baixado não é um executável do Windows.")
        os.replace(parcial, destino)
        return destino
    except BaseException:
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise


def pode_atualizar_sozinho() -> bool:
    """Só no .exe (PyInstaller), no Windows, em pasta com permissão de gravação."""
    return (sys.platform == "win32" and getattr(sys, "frozen", False)
            and os.access(os.path.dirname(sys.executable), os.W_OK))


def _bat(caminho: str) -> str:
    """Caminho seguro dentro de um .bat ('%' precisa ser dobrado)."""
    return caminho.replace("%", "%%")


def gerar_script_troca(novo: str, atual: str, pasta_script: str, pid: "int | None" = None) -> str:
    """Cria o .bat que espera o programa fechar, troca o .exe e o reabre.

    - Espera o processo `pid` terminar (no máximo ~60 s) e só então troca.
    - Tenta renomear o .exe atual por até ~60 s; nunca fica em laço infinito.
    - Confere o resultado olhando os arquivos (não depende de ERRORLEVEL).
    - Se a troca falhar, devolve a versão anterior e reabre o programa.
    - Registra o que aconteceu em `atualizacao.log` (ao lado do .exe).
    Roda sem janela (veja `executar_troca`).
    """
    n, a = _bat(novo), _bat(atual)
    anterior = a + ".anterior"
    log = _bat(os.path.join(pasta_script, "atualizacao.log"))
    linhas = [
        "@echo off",
        "chcp 65001 >nul",
        f'echo [%date% %time%] Atualizacao iniciada > "{log}"',
    ]
    if pid:
        linhas += [
            "set /a espera=0",
            ":esperar",
            "set /a espera+=1",
            f'tasklist /FI "PID eq {int(pid)}" /NH 2>nul | find " {int(pid)} " >nul',
            "if errorlevel 1 goto fechou",
            "if %espera% GEQ 60 goto fechou",
            "ping -n 2 127.0.0.1 >nul",
            "goto esperar",
            ":fechou",
            "ping -n 3 127.0.0.1 >nul",
        ]
    linhas += [
        "set /a t=0",
        ":trocar",
        "set /a t+=1",
        f'if exist "{anterior}" del /f /q "{anterior}" >nul 2>&1',
        f'move /y "{a}" "{anterior}" >nul 2>&1',
        f'if not exist "{a}" goto colocar',
        f'echo [%date% %time%] Tentativa %t%: nao foi possivel renomear o programa atual >> "{log}"',
        "if %t% GEQ 30 goto fim",
        "ping -n 3 127.0.0.1 >nul",
        "goto trocar",
        ":colocar",
        f'move /y "{n}" "{a}" >nul 2>&1',
        f'if exist "{a}" goto pronto',
        f'echo [%date% %time%] Falha ao colocar a nova versao; restaurando a anterior >> "{log}"',
        f'move /y "{anterior}" "{a}" >nul 2>&1',
        "goto fim",
        ":pronto",
        f'echo [%date% %time%] Atualizado com sucesso >> "{log}"',
        ":fim",
        f'start "" "{a}"',
        '(goto) 2>nul & del "%~f0"',
        "",
    ]
    caminho = os.path.join(pasta_script, "atualizar.bat")
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(linhas))
    return caminho


CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


def _opcoes_sem_janela() -> dict:
    """Opções do Popen para rodar o .bat OCULTO. Não usar DETACHED_PROCESS: sem
    console, cada comando do .bat (ex.: ping) abriria uma janela própria."""
    opcoes = {"creationflags": CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP}
    if hasattr(subprocess, "STARTUPINFO"):                 # só no Windows
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = 0                               # SW_HIDE
        opcoes["startupinfo"] = info
    return opcoes


def executar_troca(novo: str) -> None:
    """Dispara o script de troca (oculto). Depois, o programa deve fechar."""
    atual = sys.executable
    script = gerar_script_troca(novo, atual, os.path.dirname(atual), pid=os.getpid())
    ambiente = {k: v for k, v in os.environ.items()
                if not k.startswith("_PYI") and k != "_MEIPASS2"}
    ambiente["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen(["cmd", "/c", script], env=ambiente, close_fds=True,
                     **_opcoes_sem_janela())
