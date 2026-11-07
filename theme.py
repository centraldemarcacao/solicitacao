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
VERSAO = "2.4"

# --- Barra lateral (azul-marinho) -------------------------------------
NAVY = "#0B2A43"
NAVY_HOVER = "#143B5C"
NAVY_ATIVO = "#18486E"
NAV_TEXTO = "#DCE9F2"
NAV_SUAVE = "#92B2C8"
NAV_LINHA = "#1F4565"

# --- Verde-água clínico (cor principal) -------------------------------
TEAL = "#0B7684"
TEAL_ESCURO = "#085C68"
TEAL_CLARO = "#E1F3F5"
TEAL_BORDA = "#BDE0E5"
TEAL_ACENTO = "#34C6CB"      # detalhe sobre fundo escuro

# --- Estados ----------------------------------------------------------
VERDE = "#17744E"            # ação positiva / "Atendida"
VERDE_HOVER = "#115C3D"
VERDE_CLARO = "#E6F5EE"

AMBAR = "#B45309"            # "Pendente" / atenção
AMBAR_HOVER = "#92400E"
AMBAR_CLARO = "#FFF4E0"

VERMELHO = "#B42318"         # erro / exclusão
VERMELHO_HOVER = "#8F1B12"
VERMELHO_CLARO = "#FDECEA"

# --- Neutros ----------------------------------------------------------
FUNDO = "#EEF4F8"
CARD = "#FFFFFF"
SELECAO = "#D5E4F0"          # linha selecionada na tabela (azul-acinzentado suave)
BORDA = "#D3DEE6"
BORDA_FORTE = "#B6C5D1"
TEXTO = "#13293D"
TEXTO_SUAVE = "#52677A"
PLACEHOLDER = "#65778A"
BRANCO = "#FFFFFF"

# --- Tipografia -------------------------------------------------------
FONTE = "Segoe UI"

# --- Atualização automática -------------------------------------------
# Repositório do GitHub onde as versões são publicadas, no formato
# "usuario/repositorio". Deixe vazio para desativar a atualização automática.
REPOSITORIO_GITHUB = "centraldemarcacao/solicitacao"
