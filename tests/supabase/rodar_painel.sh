#!/usr/bin/env bash
# Valida supabase/setup.sql + supabase/painel.sql num PostgreSQL de verdade (com um "Supabase" mínimo).
# Uso: PGHOST=<socket ou host> PGPORT=<porta> PGUSER=postgres tests/supabase/rodar_painel.sh
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"; RAIZ="$(dirname "$(dirname "$AQUI")")"
BANCO="painel_teste_$$"
psql -d postgres -qc "create database $BANCO"
trap 'psql -d postgres -qc "drop database if exists $BANCO" >/dev/null' EXIT
P="psql -d $BANCO -v ON_ERROR_STOP=1 -q"
$P -f "$AQUI/ambiente_supabase.sql"
$P -f "$RAIZ/supabase/setup.sql"
$P -f "$RAIZ/supabase/painel.sql"
$P -f "$RAIZ/supabase/painel.sql"          # idempotente: roda de novo sem erro
$P -tA -f "$AQUI/painel_teste.sql" | tail -1
