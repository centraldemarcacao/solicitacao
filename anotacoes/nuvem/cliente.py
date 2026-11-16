"""
cliente.py
----------
Cliente mínimo do Supabase (login + API REST do banco), feito só com a
biblioteca padrão do Python: não acrescenta dependências ao programa.

  - Login com e-mail e senha; a SENHA NÃO É GUARDADA. Só o "refresh token"
    (que renova a sessão) fica em dados/nuvem.json.
  - A chave usada é a chave PÚBLICA do projeto (anon / publishable). Chaves
    secretas (service_role / sb_secret_...) são recusadas.
  - Todos os erros viram NuvemErro, com mensagem em português.
"""

import base64
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional

from anotacoes.nucleo.certificados import MENSAGEM_CERTIFICADO, contexto_ssl, erro_de_certificado

TIMEOUT_PADRAO = 20
MIN_SENHA = 8        # tamanho mínimo da senha de contas novas (o Supabase exige 6 por padrão)


class NuvemErro(Exception):
    """Falha ao falar com a nuvem. `precisa_login` indica sessão inválida."""

    def __init__(self, mensagem: str, precisa_login: bool = False) -> None:
        super().__init__(mensagem)
        self.precisa_login = precisa_login


# ----------------------------------------------------------------------
# Validação do que o usuário digita
# ----------------------------------------------------------------------
def normalizar_url(url: str) -> str:
    """'https://abc.supabase.co/' -> 'https://abc.supabase.co'. Aceita sem 'https://'
    e ignora o que vier depois do domínio (ex.: '/rest/v1')."""
    url = (url or "").strip()
    if not url:
        raise ValueError("Informe o endereço do projeto (Project URL).")
    if "://" not in url:
        url = "https://" + url
    partes = urllib.parse.urlsplit(url)
    if partes.scheme != "https" or not partes.hostname or "." not in partes.hostname:
        raise ValueError("O endereço do projeto deve começar com https:// "
                         "(exemplo: https://abcdefgh.supabase.co).")
    return f"https://{partes.netloc}"


def validar_chave(chave: str) -> str:
    """Aceita a chave pública (anon / publishable). Recusa chaves secretas."""
    chave = "".join((chave or "").split())
    if len(chave) < 20:
        raise ValueError("Informe a chave pública do projeto (anon ou publishable).")
    if chave.startswith("sb_secret_"):
        raise ValueError("Essa é uma chave SECRETA. Use a chave pública "
                         "(anon / publishable) e nunca cole a secreta aqui.")
    if chave.startswith("eyJ"):
        try:
            carga = chave.split(".")[1]
            carga += "=" * (-len(carga) % 4)
            papel = json.loads(base64.urlsafe_b64decode(carga)).get("role")
        except Exception:
            papel = None
        if papel == "service_role":
            raise ValueError("Essa é a chave service_role (secreta). Use a chave "
                             "anon / publishable e nunca cole a secreta aqui.")
    return chave


def validar_email(email: str) -> str:
    email = (email or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Informe um e-mail válido.")
    return email


def validar_senha(senha: str) -> Optional[str]:
    """None se a senha serve para uma conta nova; senão, a mensagem de erro."""
    if not senha or len(senha) < MIN_SENHA:
        return f"Use uma senha com pelo menos {MIN_SENHA} caracteres."
    return None


# ----------------------------------------------------------------------
class ClienteSupabase:
    """Faz as chamadas HTTP. Use um cliente por vez (não é thread-safe)."""

    def __init__(self, url: str, chave: str, refresh_token: Optional[str] = None,
                 ao_renovar: Optional[Callable[[str], None]] = None,
                 timeout: float = TIMEOUT_PADRAO) -> None:
        self.url = normalizar_url(url)
        self.chave = validar_chave(chave)
        self.refresh_token = refresh_token
        self.ao_renovar = ao_renovar
        self.timeout = timeout
        self._acesso: Optional[str] = None
        self._expira = 0.0

    # --- HTTP bruto -----------------------------------------------------
    def _http(self, metodo: str, caminho: str, corpo=None, cabecalhos=None,
              token: Optional[str] = None):
        dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
        req = urllib.request.Request(self.url + caminho, data=dados, method=metodo)
        req.add_header("apikey", self.chave)
        req.add_header("Authorization", f"Bearer {token or self.chave}")
        req.add_header("User-Agent", "AnotacoesHospitalares")
        if dados is not None:
            req.add_header("Content-Type", "application/json")
        for nome, valor in (cabecalhos or {}).items():
            req.add_header(nome, valor)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=contexto_ssl()) as resp:
                bruto = resp.read()
        except urllib.error.HTTPError as exc:
            try:
                detalhe = json.loads(exc.read().decode("utf-8", "replace"))
            except Exception:
                detalhe = {}
            raise _erro_http(exc.code, detalhe) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if erro_de_certificado(exc):
                raise NuvemErro(MENSAGEM_CERTIFICADO) from exc
            raise NuvemErro(
                "Sem conexão com o Supabase. Verifique a internet "
                "(a rede da instituição pode estar bloqueando o acesso).") from exc
        if not bruto:
            return None
        try:
            return json.loads(bruto.decode("utf-8"))
        except ValueError:
            raise NuvemErro("Resposta inesperada do Supabase.") from None

    # --- Sessão ---------------------------------------------------------
    def _guardar_sessao(self, resposta) -> None:
        if not isinstance(resposta, dict) or not resposta.get("access_token"):
            raise NuvemErro("O Supabase não devolveu uma sessão válida.")
        self._acesso = resposta["access_token"]
        self._expira = time.time() + max(60, int(resposta.get("expires_in") or 3600)) - 60
        novo = resposta.get("refresh_token")
        if novo:
            self.refresh_token = novo
            if self.ao_renovar:
                self.ao_renovar(novo)

    def entrar(self, email: str, senha: str) -> None:
        """Login com e-mail e senha (a senha não é guardada)."""
        email = validar_email(email)
        if not senha:
            raise NuvemErro("Informe a senha.")
        resposta = self._http("POST", "/auth/v1/token?grant_type=password",
                              {"email": email, "password": senha})
        self._guardar_sessao(resposta)

    def cadastrar(self, email: str, senha: str) -> str:
        """Cria uma conta nova (só funciona se o cadastro estiver liberado no Supabase).

        Retorna "conectado" (conta criada e já com sessão) ou "confirmar_email" (conta criada,
        mas o Supabase exige confirmar o e-mail antes do primeiro login).
        """
        email = validar_email(email)
        erro = validar_senha(senha)
        if erro:
            raise NuvemErro(erro)
        resposta = self._http("POST", "/auth/v1/signup", {"email": email, "password": senha})
        if isinstance(resposta, dict) and resposta.get("access_token"):
            self._guardar_sessao(resposta)
            return "conectado"
        return "confirmar_email"

    def _token_valido(self) -> str:
        if self._acesso and time.time() < self._expira:
            return self._acesso
        if not self.refresh_token:
            raise NuvemErro("Entre com seu e-mail e senha para conectar.", precisa_login=True)
        try:
            resposta = self._http("POST", "/auth/v1/token?grant_type=refresh_token",
                                  {"refresh_token": self.refresh_token})
        except NuvemErro as exc:
            if exc.precisa_login or "inválid" in str(exc).lower():
                raise NuvemErro("A sessão expirou. Entre novamente com e-mail e senha.",
                                precisa_login=True) from None
            raise
        self._guardar_sessao(resposta)
        return self._acesso

    # --- Banco (PostgREST) ---------------------------------------------
    def requisitar(self, metodo: str, tabela: str, parametros: Optional[dict] = None,
                   corpo=None, cabecalhos: Optional[dict] = None):
        caminho = f"/rest/v1/{tabela}"
        if parametros:
            caminho += "?" + urllib.parse.urlencode(parametros, safe=",.()*:")
        try:
            return self._http(metodo, caminho, corpo, cabecalhos, self._token_valido())
        except NuvemErro as exc:
            if not exc.precisa_login:
                raise
            # Token recusado no meio do uso: tenta renovar uma vez.
            self._acesso = None
            return self._http(metodo, caminho, corpo, cabecalhos, self._token_valido())

    def rpc(self, nome: str, corpo: Optional[dict] = None):
        """Chama uma função do banco (`/rest/v1/rpc/<nome>`), com a sessão do usuário."""
        return self.requisitar("POST", f"rpc/{nome}", corpo=corpo if corpo is not None else {})


def _erro_http(codigo: int, detalhe: dict) -> NuvemErro:
    """Traduz respostas de erro do Supabase em mensagens claras."""
    texto = " ".join(str(detalhe.get(k) or "") for k in
                     ("message", "msg", "error_description", "error", "hint")).lower()
    cod = str(detalhe.get("code") or detalhe.get("error_code") or "")
    if cod == "PT403":
        return NuvemErro("Acesso negado: esta ação é exclusiva de administradores.")
    if cod in ("PT400", "PT404"):
        resumo = (detalhe.get("message") or "").strip()
        return NuvemErro(resumo or "Pedido recusado pelo servidor.")
    if cod == "PGRST202" or "could not find the function" in texto:
        return NuvemErro("O painel ainda não foi configurado na nuvem. Execute o SQL do "
                         "painel (botão “Copiar SQL do painel”) no SQL Editor do Supabase.")
    if cod == "PGRST205" or "could not find the table" in texto or (
            codigo == 404 and "relation" in texto):
        return NuvemErro("A tabela da nuvem ainda não existe. Copie o script SQL "
                         "(botão “Copiar SQL”) e execute no SQL Editor do Supabase.")
    if cod == "signup_disabled" or "signups not allowed" in texto or "signup is disabled" in texto:
        return NuvemErro("O cadastro de novas contas está desativado neste projeto. "
                         "Peça ao administrador para criar o seu usuário.")
    if cod in ("user_already_exists", "email_exists") or "already registered" in texto \
            or "already been registered" in texto:
        return NuvemErro("Já existe uma conta com este e-mail. Use “Conectar” (ou peça ao "
                         "administrador para trocar a senha).")
    if cod == "weak_password" or "password should be at least" in texto:
        return NuvemErro(f"Senha fraca. Use pelo menos {MIN_SENHA} caracteres, misturando "
                         "letras e números.")
    if "invalid login" in texto or "invalid_credentials" in texto:
        return NuvemErro("E-mail ou senha incorretos.")
    if "email not confirmed" in texto:
        return NuvemErro("O e-mail ainda não foi confirmado. No painel do Supabase, "
                         "abra Authentication > Users e confirme o usuário.")
    if "refresh token" in texto or "jwt expired" in texto or cod == "PGRST303":
        return NuvemErro("A sessão expirou.", precisa_login=True)
    if codigo in (401, 403) and ("jwt" in texto or "apikey" in texto or "api key" in texto):
        return NuvemErro("A chave informada não foi aceita por este projeto. "
                         "Confira o endereço e a chave pública.")
    if codigo == 401:
        return NuvemErro("Acesso negado pelo Supabase.", precisa_login=True)
    if codigo == 403 or cod == "42501":
        return NuvemErro("Sem permissão na tabela. Execute novamente o script SQL "
                         "(botão “Copiar SQL”) no Supabase.")
    if codigo == 429:
        return NuvemErro("Muitas tentativas seguidas. Aguarde um minuto e tente de novo.")
    if codigo >= 500:
        return NuvemErro("O Supabase está indisponível no momento (ou o projeto está "
                         "pausado). Abra o painel do Supabase e reative o projeto, se preciso.")
    resumo = (detalhe.get("message") or detalhe.get("msg") or "").strip()
    return NuvemErro(f"Erro {codigo} do Supabase" + (f": {resumo}" if resumo else "."))
