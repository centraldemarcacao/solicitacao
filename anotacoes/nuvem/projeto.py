"""
projeto.py
----------
Projeto Supabase usado por TODOS os computadores. Preencha as duas linhas abaixo UMA vez
(no GitHub: abra este arquivo > lápis > cole os valores > Commit). Com as duas preenchidas,
a aba Nuvem (em Configurações) mostra só E-mail e Senha.

  URL_PROJETO   -> Supabase > Project Settings > API > Project URL
  CHAVE_PUBLICA -> Supabase > Project Settings > API Keys > anon / publishable
                   (a chave PÚBLICA, que foi feita para ficar no programa; a proteção dos
                   dados vem das regras do banco e do login. NUNCA use a secret/service_role)

Deixe vazio para voltar a pedir endereço e chave na tela.

  PERMITIR_CADASTRO -> mostra o botão "Criar conta" na aba Nuvem (em Configurações). Deixe False (padrão):
                       este arquivo é público, então a chave NÃO protege nada, e o que
                       impede cadastros de terceiros é o Supabase com "Allow new users to
                       sign up" DESLIGADO. Para criar usuários use o administrador:
                       anotacoes/nuvem/admin.py (veja docs/nuvem-supabase.md).
                       Só ligue se o cadastro estiver liberado no Supabase de propósito.
"""

from typing import Optional, Tuple

from anotacoes.nuvem.cliente import normalizar_url, validar_chave

URL_PROJETO = "https://ojoenkaehillwxgiffhf.supabase.co"
CHAVE_PUBLICA = "sb_publishable_CKVkrUUdR1DoUKbuobnlPA_QJCFn-EM"
PERMITIR_CADASTRO = False


def projeto_fixo(url: str = URL_PROJETO, chave: str = CHAVE_PUBLICA) -> Optional[Tuple[str, str]]:
    """(url, chave) se os dois estão preenchidos e válidos; senão None."""
    if not (url or "").strip() or not (chave or "").strip():
        return None
    try:
        return normalizar_url(url), validar_chave(chave)
    except ValueError:
        return None
