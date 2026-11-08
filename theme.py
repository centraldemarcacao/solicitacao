"""
theme.py
--------
Identidade visual do sistema: paleta clínica (azul-marinho + verde-água),
nome da instituição e tipografia.

Para trocar o nome, as cores ou a fonte, edite somente este arquivo:
toda a interface usa estas constantes.

Todas as combinações texto/fundo foram escolhidas para manter contraste
mínimo de 4,5:1 (leitura rápida em plantões).
"""

# --- Marca ------------------------------------------------------------
NOME_INSTITUICAO = "Liga Contra o Câncer"
SUBTITULO = "Solicitações de pacientes"
VERSAO = "2.8.0"

# --- Barra lateral (azul-marinho) -------------------------------------
NAVY = "#0B2A43"
NAVY_HOVER = "#143B5C"
NAVY_ATIVO = "#18486E"
NAV_TEXTO = "#DCE9F2"
NAV_SUAVE = "#92B2C8"
NAV_LINHA = "#1F4565"

# --- Cores que mudam com o tema (claro / escuro) -----------------------
# Regras de uso:
#   SUPERFICIE  = fundo de campos, tabelas e caixas de texto
#   CARD        = fundo de cartões e janelas
#   SOBRE_COR   = texto/ícone sobre botões coloridos (TEAL, VERDE, AMBAR, VERMELHO)
#   BRANCO      = branco fixo (sobre o azul-marinho da barra lateral)
# Todas as combinações têm contraste mínimo de 4,5:1 (veja test_tema.py).
_CLARO = {
    "TEAL": "#0B7684", "TEAL_ESCURO": "#085C68",
    "TEAL_CLARO": "#E1F3F5", "TEAL_BORDA": "#BDE0E5",
    "VERDE": "#17744E", "VERDE_HOVER": "#115C3D", "VERDE_CLARO": "#E6F5EE",
    "AMBAR": "#B45309", "AMBAR_HOVER": "#92400E", "AMBAR_CLARO": "#FFF4E0",
    "VERMELHO": "#B42318", "VERMELHO_HOVER": "#8F1B12", "VERMELHO_CLARO": "#FDECEA",
    "FUNDO": "#EEF4F8", "CARD": "#FFFFFF", "SUPERFICIE": "#FFFFFF",
    "SELECAO": "#D5E4F0", "BORDA": "#D3DEE6", "BORDA_FORTE": "#B6C5D1",
    "TEXTO": "#13293D", "TEXTO_SUAVE": "#52677A", "PLACEHOLDER": "#65778A",
    "SOBRE_COR": "#FFFFFF", "SEG_SELECIONADO": "#34C6CB",
}
_ESCURO = {
    "TEAL": "#4CC2D0", "TEAL_ESCURO": "#8ADBE5",
    "TEAL_CLARO": "#123640", "TEAL_BORDA": "#1E5663",
    "VERDE": "#4CCB8D", "VERDE_HOVER": "#7BDDAD", "VERDE_CLARO": "#11392B",
    "AMBAR": "#F5A94E", "AMBAR_HOVER": "#FFC27A", "AMBAR_CLARO": "#3B2B10",
    "VERMELHO": "#FF8B7B", "VERMELHO_HOVER": "#FFB0A4", "VERMELHO_CLARO": "#40191B",
    "FUNDO": "#0E1822", "CARD": "#162531", "SUPERFICIE": "#1B2D3B",
    "SELECAO": "#2B4A63", "BORDA": "#2A3F50", "BORDA_FORTE": "#43607A",
    "TEXTO": "#E8F0F6", "TEXTO_SUAVE": "#A3B7C7", "PLACEHOLDER": "#8FA5B7",
    "SOBRE_COR": "#0B1B26", "SEG_SELECIONADO": "#2E6F7B",
}
TEMAS = {"claro": _CLARO, "escuro": _ESCURO}
TEMA_ATUAL = "claro"

TEAL_ACENTO = "#34C6CB"      # detalhe sobre fundo escuro (fixo)
BRANCO = "#FFFFFF"           # branco fixo

# Valores iniciais (tema claro). Os módulos leem T.<nome> na hora de montar a
# tela, então basta chamar aplicar_tema() e reconstruir a interface.
globals().update(_CLARO)


def aplicar_tema(nome: str) -> str:
    """Troca as cores do módulo para o tema 'claro' ou 'escuro'."""
    global TEMA_ATUAL
    if nome not in TEMAS:
        nome = "claro"
    globals().update(TEMAS[nome])
    TEMA_ATUAL = nome
    return nome


# --- Tipografia -------------------------------------------------------
FONTE = "Segoe UI"

# --- Atualização automática -------------------------------------------
# Repositório do GitHub onde as versões são publicadas, no formato
# "usuario/repositorio". Deixe vazio para desativar a atualização automática.
REPOSITORIO_GITHUB = "centraldemarcacao/solicitacao"
