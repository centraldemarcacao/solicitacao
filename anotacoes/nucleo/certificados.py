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

import os
import ssl
from typing import List, Optional

from anotacoes.caminhos import pasta_programa

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


def importar_certificado(origem: str, pasta_destino: str) -> str:
    """Valida um certificado (.pem/.crt/.cer, texto ou binário) e o salva como
    `ca-extra.pem` em `pasta_destino`. Devolve o caminho gravado. ValueError se o
    arquivo não for um certificado."""
    try:
        with open(origem, "rb") as arq:
            bruto = arq.read(2_000_000)
    except OSError as exc:
        raise ValueError(f"Não foi possível ler o arquivo: {exc}") from None
    if b"-----BEGIN CERTIFICATE-----" in bruto:
        pem = bruto.decode("ascii", "ignore")
    else:
        try:
            pem = ssl.DER_cert_to_PEM_cert(bruto)
        except Exception:
            raise ValueError("O arquivo não parece ser um certificado "
                             "(use o formato .pem, .crt ou .cer).") from None
    try:
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=pem)
    except ssl.SSLError:
        raise ValueError("O arquivo não contém um certificado válido.") from None
    os.makedirs(pasta_destino, exist_ok=True)
    destino = os.path.join(pasta_destino, NOME_CA_EXTRA)
    with open(destino + ".tmp", "w", encoding="ascii") as arq:
        arq.write(pem)
    os.replace(destino + ".tmp", destino)
    return destino


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
                    pass
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
