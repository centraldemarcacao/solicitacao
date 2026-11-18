-- Imita o mínimo do Supabase para validar supabase/setup.sql e supabase/painel.sql num PostgreSQL comum.
-- (Não faz parte do programa nem do CI. Uso: tests/supabase/rodar_painel.sh)
-- papéis valem para o servidor inteiro: cria só se ainda não existirem
do $$ begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
end $$;
create schema auth;
create schema extensions;
create extension pgcrypto schema extensions;
create table auth.users (
    instance_id uuid,
    id uuid primary key default gen_random_uuid(),
    aud varchar(255),
    role varchar(255),
    email varchar(255),
    encrypted_password varchar(255),
    email_confirmed_at timestamptz,
    raw_app_meta_data jsonb,
    raw_user_meta_data jsonb,
    banned_until timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz,
    last_sign_in_at timestamptz,
    confirmation_token varchar(255) not null default '',
    recovery_token varchar(255) not null default '',
    email_change_token_new varchar(255) not null default '',
    email_change varchar(255) not null default ''
);
create table auth.identities (
    id uuid primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    provider_id text not null,
    identity_data jsonb not null,
    provider text not null,
    last_sign_in_at timestamptz,
    created_at timestamptz,
    updated_at timestamptz,
    unique (provider_id, provider)
);
create function auth.uid() returns uuid language sql stable as
$$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema public to anon, authenticated;
