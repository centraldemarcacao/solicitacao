"""Administra os usuários da nuvem (Supabase) sem abrir o painel. Uso:

    python scripts/usuarios_nuvem.py listar
    python scripts/usuarios_nuvem.py criar medico@hospital.org --gerar-senha
    python scripts/usuarios_nuvem.py senha medico@hospital.org

Precisa da chave SECRETA do Supabase: defina a variável SUPABASE_SERVICE_KEY (ou digite quando
pedir). Nunca coloque essa chave em arquivo do repositório. Veja docs/nuvem-supabase.md.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anotacoes.nuvem.admin import executar_cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(executar_cli(sys.argv[1:]))
