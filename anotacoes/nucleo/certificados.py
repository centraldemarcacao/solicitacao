"""
certificados.py
---------------
Conexões seguras (HTTPS) do programa: atualização pelo GitHub e nuvem (Supabase).

O Python, sozinho, nem sempre reconhece os certificados que o Windows aceita.
Em redes que inspecionam o tráfego seguro (proxy, firewall ou antivírus que
trocam o certificado), o resultado é o erro
"CERTIFICATE_VERIFY_FAILED ... unable to get local issuer certificate".

`contexto_ssl()` monta uma verificação que CONTINUA ATIVA e confia em:
  1. os certificados padrão do Python (e da variável SSL_CERT_FILE, se existir);
  2. os repositórios "ROOT" e "CA" do Windows (onde a TI instala o certificado
     da instituição);
  3. um arquivo opcional `ca-extra.pem` (certificado raiz da instituição), na pasta
     `dados` ao lado do programa, ao lado do .exe ou em %LOCALAPPDATA%\\AnotacoesHospitalares.

A verificação nunca é desligada: o programa baixa um executável.
"""

import base64
import logging
import os
import re
import ssl
from typing import List, Optional

from anotacoes.caminhos import pasta_programa

log = logging.getLogger(__name__)

NOME_CA_EXTRA = "ca-extra.pem"

MENSAGEM_CERTIFICADO = (
    "O certificado de segurança da rede não é reconhecido neste computador. "
    "Em Configurações > Diagnóstico, use \"Importar certificado da rede\" "
    "e escolha o certificado raiz da instituição (peça à TI, .pem ou .cer)."
)


def pastas_ca_extra() -> List[str]:
    pastas = [os.path.join(pasta_programa(), "dados"), pasta_programa()]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        pastas.append(os.path.join(local, "AnotacoesHospitalares"))
    return pastas


_BLOCO_PEM = re.compile(
    r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", re.S)


def _ler_certificados(bruto: bytes) -> List[bytes]:
    """Certificados (em DER) de um arquivo: PEM com um ou vários, ou um DER binário."""
    texto = None
    for codificacao in ("utf-8-sig", "utf-16"):
        try:
            candidato = bruto.decode(codificacao)
        except UnicodeError:
            continue
        if "-----BEGIN CERTIFICATE-----" in candidato:
            texto = candidato
            break
    if texto is not None:
        ders = []
        for corpo in _BLOCO_PEM.findall(texto):
            try:
                ders.append(base64.b64decode("".join(corpo.split()), validate=True))
            except ValueError:
                raise ValueError("O arquivo tem um certificado danificado. "
                                 "Exporte-o de novo.") from None
        return ders
    if b"-----BEGIN PKCS7-----" in bruto or b"-----BEGIN CMS-----" in bruto:
        raise ValueError("O arquivo está no formato PKCS#7. Exporte de novo escolhendo "
                         "\"ASCII codificado na Base64, certificado único\" (.cer/.crt/.pem).")
    return [bruto]          # tenta como DER binário


def certificados_importados(pasta: str) -> List[bytes]:
    """Certificados (DER) já guardados em `pasta/ca-extra.pem` (lista vazia se não houver)."""
    try:
        with open(os.path.join(pasta, NOME_CA_EXTRA), "rb") as arq:
            return _ler_certificados(arq.read(5_000_000))
    except (OSError, ValueError):
        return []


def importar_certificado_detalhe(origem: str, pasta_destino: str):
    """Como `importar_certificado`, mas devolve (caminho, novos, total).

    Os certificados já importados são MANTIDOS: cada importação acrescenta (sem repetir) ao
    arquivo `ca-extra.pem`. Assim GitHub e Supabase, que usam raízes diferentes, convivem.
    """
    try:
        with open(origem, "rb") as arq:
            bruto = arq.read(2_000_000)
    except OSError as exc:
        raise ValueError(f"Não foi possível ler o arquivo: {exc}") from None
    novos_der = _ler_certificados(bruto)
    for der in novos_der:
        try:
            ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(
                cadata=ssl.DER_cert_to_PEM_cert(der))
        except (ssl.SSLError, ValueError):
            raise ValueError("O arquivo não contém um certificado válido. Exporte-o de novo "
                             "escolhendo \"ASCII codificado na Base64, certificado único\".") from None
    if not novos_der:
        raise ValueError("O arquivo não parece ser um certificado "
                         "(use o formato .pem, .crt ou .cer).")
    existentes = certificados_importados(pasta_destino)
    todos = list(existentes)
    for der in novos_der:
        if der not in todos:
            todos.append(der)
    os.makedirs(pasta_destino, exist_ok=True)
    destino = os.path.join(pasta_destino, NOME_CA_EXTRA)
    with open(destino + ".tmp", "w", encoding="ascii", newline="\n") as arq:
        arq.write("".join(ssl.DER_cert_to_PEM_cert(der) for der in todos))
    os.replace(destino + ".tmp", destino)
    return destino, len(todos) - len(existentes), len(todos)


def importar_certificado(origem: str, pasta_destino: str) -> str:
    """Valida um certificado (.pem/.crt/.cer, texto ou binário) e o ACRESCENTA a
    `ca-extra.pem` em `pasta_destino`. Devolve o caminho gravado. ValueError se o arquivo
    não for um certificado."""
    return importar_certificado_detalhe(origem, pasta_destino)[0]


def _carregar_repositorio_windows(contexto: ssl.SSLContext) -> None:
    enum = getattr(ssl, "enum_certificates", None)     # só existe no Windows
    if enum is None:
        return
    for loja in ("ROOT", "CA"):
        try:
            certificados = enum(loja)
        except OSError:
            continue
        for der, codificacao, _uso in certificados:
            if codificacao == "x509_asn":
                try:
                    contexto.load_verify_locations(cadata=der)
                except ssl.SSLError:
                    log.warning("Falha ignorada em _carregar_repositorio_windows()", exc_info=True)
    # Aceita um certificado intermediário confiável como ponto de partida, como
    # fazem os navegadores (e o Python 3.13 por padrão).
    contexto.verify_flags |= getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)


def _carregar_ca_extra(contexto: ssl.SSLContext) -> None:
    for pasta in pastas_ca_extra():
        caminho = os.path.join(pasta, NOME_CA_EXTRA)
        if os.path.isfile(caminho):
            try:
                contexto.load_verify_locations(cafile=caminho)
            except (ssl.SSLError, OSError):
                pass   # arquivo inválido: segue só com os demais certificados


def contexto_ssl() -> ssl.SSLContext:
    contexto = ssl.create_default_context()
    _carregar_repositorio_windows(contexto)
    _carregar_ca_extra(contexto)
    return contexto


def erro_de_certificado(exc: Optional[BaseException]) -> bool:
    """True se `exc` (ou algo na cadeia de causas) é falha de certificado."""
    visto = set()
    while exc is not None and id(exc) not in visto:
        visto.add(id(exc))
        if isinstance(exc, ssl.SSLCertVerificationError):
            return True
        motivo = getattr(exc, "reason", None)       # URLError.reason pode ser texto
        exc = (motivo if isinstance(motivo, BaseException) else None) \
            or exc.__cause__ or exc.__context__
    return False
