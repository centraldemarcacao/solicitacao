"""
nuvem_sql.py
------------
Script SQL que o usuário executa UMA vez no painel do Supabase
(SQL Editor) para criar a tabela que recebe a cópia dos registros.

Também é gravado no arquivo supabase_setup.sql (veja test_nuvem.py, que
garante que os dois são idênticos).

Segurança: a tabela só pode ser lida e alterada por quem está autenticado e
somente nas linhas que pertencem à própria conta (RLS). A chave pública do
projeto, sozinha, não dá acesso a nenhum dado.
"""

TABELA = "solicitacoes_registros"

SQL_CONFIGURACAO = """\
-- Solicitações (registros de atendimento): tabela de sincronização (execute uma única vez)
-- Pode ser executado de novo sem problemas.

create table if not exists public.solicitacoes_registros (
    uuid          text primary key,
    user_id       uuid not null default auth.uid()
                  references auth.users (id) on delete cascade,
    data_hora     text not null,
    nome          text not null,
    contato       text,
    descricao     text not null,
    status        text not null default 'Pendente'
                  check (status in ('Pendente', 'Atendida')),
    lembrete      text,
    prioridade    text not null default 'Normal',
    editado_em    text,
    excluido_em   text,
    apagado       boolean not null default false,
    atualizado_em timestamptz not null
);

create index if not exists solicitacoes_registros_sync
    on public.solicitacoes_registros (user_id, atualizado_em, uuid);

-- Segurança em nível de linha: cada conta enxerga apenas o que é seu.
alter table public.solicitacoes_registros enable row level security;

drop policy if exists "solicitacoes: somente o dono" on public.solicitacoes_registros;
create policy "solicitacoes: somente o dono"
    on public.solicitacoes_registros
    for all
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

-- Visitantes (chave pública sem login) não têm acesso nenhum.
revoke all on public.solicitacoes_registros from anon;
grant select, insert, update, delete on public.solicitacoes_registros to authenticated;
"""
