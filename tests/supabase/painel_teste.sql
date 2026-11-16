-- Cenários de segurança do painel. Cada bloco "esperar_erro" precisa FALHAR com o código dado.
\set ON_ERROR_STOP on
create or replace function pg_temp.esperar_erro(p_sql text, p_codigo text) returns void
language plpgsql as $$
begin
    execute p_sql;
    raise exception 'DEVERIA TER FALHADO (%): %', p_codigo, p_sql;
exception when others then
    if sqlstate <> p_codigo then
        raise exception 'erro errado (esperado %, veio % - %): %', p_codigo, sqlstate, sqlerrm, p_sql;
    end if;
end $$;

-- massa de dados ------------------------------------------------------
insert into auth.users (id, email, raw_app_meta_data, created_at) values
 ('aaaaaaaa-0000-0000-0000-000000000001', 'admin@x.co',  '{"role":"admin"}', now() - interval '3 days'),
 ('bbbbbbbb-0000-0000-0000-000000000002', 'maria@x.co',  null,               now() - interval '2 days'),
 ('cccccccc-0000-0000-0000-000000000003', 'joao@x.co',   '{"role":"usuario"}', now() - interval '1 day');
insert into public.solicitacoes_registros (uuid, user_id, data_hora, nome, descricao, status, prioridade, excluido_em, apagado, atualizado_em) values
 ('r1','bbbbbbbb-0000-0000-0000-000000000002','2026-11-01 10:00:00','SEGREDO PACIENTE','texto sigiloso','Pendente','Urgente',null,false, now()),
 ('r2','bbbbbbbb-0000-0000-0000-000000000002','2026-11-01 11:00:00','Fulano','x','Pendente','Normal',null,false, now()),
 ('r3','bbbbbbbb-0000-0000-0000-000000000002','2026-11-01 12:00:00','Ciclano','x','Atendida','Normal',null,false, now()),
 ('r4','bbbbbbbb-0000-0000-0000-000000000002','2026-11-01 13:00:00','Na lixeira','x','Pendente','Urgente','2026-11-02',false, now()),
 ('r5','bbbbbbbb-0000-0000-0000-000000000002','2026-11-01 14:00:00','Apagado','x','Pendente','Urgente',null,true, now()),
 ('r6','cccccccc-0000-0000-0000-000000000003','2026-11-01 15:00:00','Beltrano','x','Atendida','Normal',null,false, now());

-- visitante (anon): nada ----------------------------------------------
set role anon;
select pg_temp.esperar_erro('select public.painel_meu_papel()', '42501');
select pg_temp.esperar_erro('select * from public.painel_listar_usuarios()', '42501');
select pg_temp.esperar_erro('select * from public.painel_auditoria', '42501');
reset role;

-- usuário comum (maria) -----------------------------------------------
set role authenticated; set request.jwt.claim.sub = 'bbbbbbbb-0000-0000-0000-000000000002';
do $$ begin assert public.painel_meu_papel() = 'usuario', 'maria deveria ser usuario'; end $$;
select pg_temp.esperar_erro('select * from public.painel_listar_usuarios()', 'PT403');
select pg_temp.esperar_erro('select * from public.painel_listar_auditoria()', 'PT403');
select pg_temp.esperar_erro($q$select public.painel_definir_papel('bbbbbbbb-0000-0000-0000-000000000002','admin')$q$, 'PT403');
select pg_temp.esperar_erro($q$select public.painel_definir_acesso('cccccccc-0000-0000-0000-000000000003', false)$q$, 'PT403');
select pg_temp.esperar_erro('select * from public.painel_auditoria', '42501');
select pg_temp.esperar_erro($q$update auth.users set raw_app_meta_data = '{"role":"admin"}'$q$, '42501');   -- não se promove direto
do $$ begin assert (select count(*) from public.solicitacoes_registros) = 5, 'RLS: maria só vê as próprias linhas (5)'; end $$;
reset role;

-- administrador ----------------------------------------------------------
set role authenticated; set request.jwt.claim.sub = 'aaaaaaaa-0000-0000-0000-000000000001';
do $$ begin assert public.painel_meu_papel() = 'admin', 'admin deveria ser admin'; end $$;
do $$
declare r record; n int := 0;
begin
    for r in select * from public.painel_listar_usuarios() loop
        n := n + 1;
        if r.email = 'maria@x.co' then
            assert r.registros = 3 and r.pendentes = 2 and r.atendidas = 1 and r.urgentes = 1,
                format('contagem errada da maria: %s/%s/%s/%s', r.registros, r.pendentes, r.atendidas, r.urgentes);
            assert r.papel = 'usuario' and r.ativo;
        elsif r.email = 'joao@x.co' then
            assert r.registros = 1 and r.atendidas = 1 and r.pendentes = 0;
        elsif r.email = 'admin@x.co' then
            assert r.papel = 'admin' and r.registros = 0;
        end if;
    end loop;
    assert n = 3, 'deveria listar 3 usuários';
end $$;
-- a função nunca devolve texto de paciente
do $$ begin
    assert not exists (select 1 from information_schema.routines r
        join information_schema.parameters p on p.specific_name = r.specific_name
        where r.routine_name = 'painel_listar_usuarios' and p.parameter_name in ('nome','descricao','contato')),
        'a listagem não pode expor nome/descrição/contato';
end $$;

select pg_temp.esperar_erro($q$select public.painel_definir_acesso('aaaaaaaa-0000-0000-0000-000000000001', false)$q$, 'PT400');  -- próprio acesso
select pg_temp.esperar_erro($q$select public.painel_definir_papel('aaaaaaaa-0000-0000-0000-000000000001', 'usuario')$q$, 'PT400'); -- próprio papel
select pg_temp.esperar_erro($q$select public.painel_definir_papel('bbbbbbbb-0000-0000-0000-000000000002', 'super')$q$, 'PT400');
select pg_temp.esperar_erro($q$select public.painel_definir_acesso('00000000-0000-0000-0000-00000000dead', false)$q$, 'PT404');

select public.painel_definir_acesso('cccccccc-0000-0000-0000-000000000003', false);       -- desativa o joão
do $$ begin assert (select not ativo from public.painel_listar_usuarios() where email = 'joao@x.co'), 'joão deveria estar inativo'; end $$;
select public.painel_definir_acesso('cccccccc-0000-0000-0000-000000000003', true);        -- reativa
do $$ begin assert (select ativo from public.painel_listar_usuarios() where email = 'joao@x.co'); end $$;
select public.painel_definir_papel('bbbbbbbb-0000-0000-0000-000000000002', 'admin');       -- promove a maria
do $$ begin
    assert (select count(*) from public.painel_listar_auditoria(50)) = 3, 'auditoria deveria ter 3 ações';
    assert (select count(*) from public.painel_listar_auditoria(2)) = 2, 'limite da auditoria';
    assert (select detalhe from public.painel_listar_auditoria(1)) = 'admin';
end $$;
reset role;

-- a maria agora é admin; ela desativa o admin original e este perde o poder NA HORA -----
set role authenticated; set request.jwt.claim.sub = 'bbbbbbbb-0000-0000-0000-000000000002';
do $$ begin assert public.painel_meu_papel() = 'admin', 'maria promovida'; end $$;
select public.painel_definir_acesso('aaaaaaaa-0000-0000-0000-000000000001', false);
reset role;
set role authenticated; set request.jwt.claim.sub = 'aaaaaaaa-0000-0000-0000-000000000001';
do $$ begin assert public.painel_meu_papel() = 'usuario', 'admin desativado não pode continuar admin'; end $$;
select pg_temp.esperar_erro('select * from public.painel_listar_usuarios()', 'PT403');
reset role;
select 'TODOS OS CENARIOS DO PAINEL PASSARAM' as resultado;
