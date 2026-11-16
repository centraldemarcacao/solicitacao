-- Imita o mínimo do Supabase para validar supabase/setup.sql e supabase/painel.sql num PostgreSQL comum.
-- (Não faz parte do programa nem do CI. Uso: tests/supabase/rodar_painel.sh)
-- papéis valem para o servidor inteiro: cria só se ainda não existirem
do $$ begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
end $$;
create schema auth;
create table auth.users (
    id uuid primary key default gen_random_uuid(),
    email varchar(255),
    raw_app_meta_data jsonb,
    banned_until timestamptz,
    created_at timestamptz not null default now(),
    last_sign_in_at timestamptz
);
create function auth.uid() returns uuid language sql stable as
$$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema public to anon, authenticated;
