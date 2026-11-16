"""
sql.py
------
Script SQL que o usuário executa UMA vez no painel do Supabase
(SQL Editor) para criar a tabela que recebe a cópia dos registros.

Também é gravado no arquivo supabase/setup.sql (veja tests/nuvem/test_nuvem.py, que
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


# Painel de controle (execute depois do script acima). Idêntico a supabase/painel.sql.
SQL_PAINEL = """\
-- Solicitações: PAINEL DE CONTROLE (administrador e usuário)
-- Execute UMA vez no SQL Editor do Supabase, DEPOIS do setup.sql. Pode ser executado de novo.
--
-- Como funciona
--   * Papel "admin": guardado em auth.users.raw_app_meta_data ->> 'role'. Só quem tem a chave
--     secreta (script scripts/usuarios_nuvem.py) ou o painel do Supabase consegue alterar isso;
--     o usuário comum NÃO consegue se promover.
--   * O programa nunca recebe a chave secreta: o painel conversa só com as funções abaixo, que
--     conferem o papel NO BANCO a cada chamada (desativar um administrador vale na hora).
--   * O administrador vê usuários e NÚMEROS (totais). Nenhuma função devolve nome, contato
--     ou descrição de paciente.
--   * Cada ação administrativa fica registrada em public.painel_auditoria.

-- ----------------------------------------------------------------------
-- Auditoria (sem acesso direto: só as funções abaixo leem e gravam)
-- ----------------------------------------------------------------------
create table if not exists public.painel_auditoria (
    id          bigint generated always as identity primary key,
    quando      timestamptz not null default now(),
    admin_id    uuid not null,
    admin_email text,
    acao        text not null,
    alvo_id     uuid,
    alvo_email  text,
    detalhe     text
);
alter table public.painel_auditoria enable row level security;   -- sem policies = sem acesso direto
revoke all on public.painel_auditoria from anon, authenticated;

-- ----------------------------------------------------------------------
-- Papel de quem está chamando
-- ----------------------------------------------------------------------
create or replace function public.painel_eh_admin()
returns boolean
language sql stable security definer set search_path = ''
as $$
    select exists (
        select 1 from auth.users u
        where u.id = (select auth.uid())
          and u.raw_app_meta_data ->> 'role' = 'admin'
          and (u.banned_until is null or u.banned_until < now())
    );
$$;

create or replace function public.painel_meu_papel()
returns text
language sql stable security definer set search_path = ''
as $$
    select case when public.painel_eh_admin() then 'admin' else 'usuario' end;
$$;

create or replace function public.painel_exigir_admin()
returns void
language plpgsql stable security definer set search_path = ''
as $$
begin
    if not public.painel_eh_admin() then
        raise exception 'Acesso negado: somente administradores.' using errcode = 'PT403';
    end if;
end;
$$;

-- ----------------------------------------------------------------------
-- Administração (somente admin)
-- ----------------------------------------------------------------------
create or replace function public.painel_listar_usuarios()
returns table (
    id uuid, email text, papel text, ativo boolean,
    criado_em timestamptz, ultimo_acesso timestamptz,
    registros bigint, pendentes bigint, atendidas bigint, urgentes bigint,
    ultima_atividade timestamptz
)
language plpgsql stable security definer set search_path = ''
as $$
begin
    perform public.painel_exigir_admin();
    return query
    select
        u.id,
        u.email::text,
        coalesce(u.raw_app_meta_data ->> 'role', 'usuario'),
        (u.banned_until is null or u.banned_until < now()),
        u.created_at,
        u.last_sign_in_at,
        count(r.uuid) filter (where r.excluido_em is null and not r.apagado),
        count(r.uuid) filter (where r.excluido_em is null and not r.apagado
                              and r.status = 'Pendente'),
        count(r.uuid) filter (where r.excluido_em is null and not r.apagado
                              and r.status = 'Atendida'),
        count(r.uuid) filter (where r.excluido_em is null and not r.apagado
                              and r.status = 'Pendente' and r.prioridade = 'Urgente'),
        max(r.atualizado_em) filter (where r.excluido_em is null and not r.apagado)
    from auth.users u
    left join public.solicitacoes_registros r on r.user_id = u.id
    group by u.id
    order by u.created_at;
end;
$$;

create or replace function public.painel_definir_acesso(p_usuario uuid, p_ativo boolean)
returns void
language plpgsql volatile security definer set search_path = ''
as $$
declare
    v_admin_email text;
    v_alvo_email  text;
begin
    perform public.painel_exigir_admin();
    if p_usuario = (select auth.uid()) then
        raise exception 'Você não pode desativar o seu próprio acesso.' using errcode = 'PT400';
    end if;
    update auth.users
       set banned_until = case when p_ativo then null else now() + interval '100 years' end
     where id = p_usuario
    returning email into v_alvo_email;
    if not found then
        raise exception 'Usuário não encontrado.' using errcode = 'PT404';
    end if;
    select email into v_admin_email from auth.users where id = (select auth.uid());
    insert into public.painel_auditoria (admin_id, admin_email, acao, alvo_id, alvo_email)
    values ((select auth.uid()), v_admin_email,
            case when p_ativo then 'ativar_acesso' else 'desativar_acesso' end,
            p_usuario, v_alvo_email);
end;
$$;

create or replace function public.painel_definir_papel(p_usuario uuid, p_papel text)
returns void
language plpgsql volatile security definer set search_path = ''
as $$
declare
    v_admin_email text;
    v_alvo_email  text;
begin
    perform public.painel_exigir_admin();
    if p_papel not in ('admin', 'usuario') then
        raise exception 'Papel inválido.' using errcode = 'PT400';
    end if;
    if p_usuario = (select auth.uid()) and p_papel <> 'admin' then
        raise exception 'Você não pode remover o seu próprio papel de administrador. Peça a outro administrador.'
            using errcode = 'PT400';
    end if;
    update auth.users
       set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb)
                               || jsonb_build_object('role', p_papel)
     where id = p_usuario
    returning email into v_alvo_email;
    if not found then
        raise exception 'Usuário não encontrado.' using errcode = 'PT404';
    end if;
    select email into v_admin_email from auth.users where id = (select auth.uid());
    insert into public.painel_auditoria (admin_id, admin_email, acao, alvo_id, alvo_email, detalhe)
    values ((select auth.uid()), v_admin_email, 'definir_papel', p_usuario, v_alvo_email, p_papel);
end;
$$;

create or replace function public.painel_criar_usuario(
    p_email text, p_senha text, p_papel text default 'usuario')
returns uuid
language plpgsql volatile security definer set search_path = ''
as $$
declare
    v_email       text := lower(btrim(coalesce(p_email, '')));
    v_id          uuid := gen_random_uuid();
    v_admin_email text;
begin
    perform public.painel_exigir_admin();
    if v_email !~ '^[^@ ]+@[^@ ]+[.][^@ ]+$' then
        raise exception 'E-mail inválido.' using errcode = 'PT400';
    end if;
    if length(coalesce(p_senha, '')) < 8 then
        raise exception 'A senha precisa ter pelo menos 8 caracteres.' using errcode = 'PT400';
    end if;
    if length(p_senha) > 72 then
        raise exception 'A senha pode ter no máximo 72 caracteres.' using errcode = 'PT400';
    end if;
    if p_papel not in ('admin', 'usuario') then
        raise exception 'Papel inválido.' using errcode = 'PT400';
    end if;
    if exists (select 1 from auth.users u where lower(u.email) = v_email) then
        raise exception 'Já existe uma conta com este e-mail.' using errcode = 'PT400';
    end if;

    -- Conta já confirmada (não depende de e-mail nem do cadastro aberto). A senha é guardada
    -- só como hash (bcrypt), no mesmo formato do Supabase Auth.
    insert into auth.users (
        instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
        raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
        confirmation_token, recovery_token, email_change_token_new, email_change)
    values (
        '00000000-0000-0000-0000-000000000000', v_id, 'authenticated', 'authenticated', v_email,
        extensions.crypt(p_senha, extensions.gen_salt('bf')), now(),
        jsonb_build_object('provider', 'email', 'providers', jsonb_build_array('email'),
                           'role', p_papel),
        '{}'::jsonb, now(), now(), '', '', '', '');
    insert into auth.identities (
        id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
    values (
        gen_random_uuid(), v_id, v_id::text,
        jsonb_build_object('sub', v_id::text, 'email', v_email, 'email_verified', true,
                           'phone_verified', false),
        'email', now(), now(), now());

    select email into v_admin_email from auth.users where id = (select auth.uid());
    insert into public.painel_auditoria (admin_id, admin_email, acao, alvo_id, alvo_email, detalhe)
    values ((select auth.uid()), v_admin_email, 'criar_usuario', v_id, v_email, p_papel);
    return v_id;
end;
$$;

create or replace function public.painel_listar_auditoria(p_limite integer default 20)
returns table (quando timestamptz, admin_email text, acao text, alvo_email text, detalhe text)
language plpgsql stable security definer set search_path = ''
as $$
begin
    perform public.painel_exigir_admin();
    return query
    select a.quando, a.admin_email, a.acao, a.alvo_email, a.detalhe
      from public.painel_auditoria a
     order by a.quando desc, a.id desc
     limit greatest(1, least(coalesce(p_limite, 20), 200));
end;
$$;

-- ----------------------------------------------------------------------
-- Permissões: visitantes (anon) não executam nada; só quem fez login.
-- ----------------------------------------------------------------------
revoke all on function public.painel_eh_admin()                     from public, anon;
revoke all on function public.painel_meu_papel()                    from public, anon;
revoke all on function public.painel_exigir_admin()                 from public, anon;
revoke all on function public.painel_listar_usuarios()              from public, anon;
revoke all on function public.painel_definir_acesso(uuid, boolean)  from public, anon;
revoke all on function public.painel_definir_papel(uuid, text)      from public, anon;
revoke all on function public.painel_criar_usuario(text, text, text) from public, anon;
revoke all on function public.painel_listar_auditoria(integer)      from public, anon;

grant execute on function public.painel_eh_admin()                     to authenticated;
grant execute on function public.painel_meu_papel()                    to authenticated;
grant execute on function public.painel_exigir_admin()                 to authenticated;
grant execute on function public.painel_listar_usuarios()              to authenticated;
grant execute on function public.painel_definir_acesso(uuid, boolean)  to authenticated;
grant execute on function public.painel_definir_papel(uuid, text)      to authenticated;
grant execute on function public.painel_criar_usuario(text, text, text) to authenticated;
grant execute on function public.painel_listar_auditoria(integer)      to authenticated;

-- Para o PostgREST enxergar as funções novas sem esperar:
notify pgrst, 'reload schema';

-- ----------------------------------------------------------------------
-- Primeiro administrador (execute UMA vez, trocando o e-mail), ou use:
--   python scripts/usuarios_nuvem.py papel seu@email.com admin
--
--   update auth.users
--      set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"role":"admin"}'
--    where email = 'seu@email.com';
-- ----------------------------------------------------------------------
"""
