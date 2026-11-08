# Nuvem (Supabase) — passo a passo da versão 2.6

> **Antes de começar:** o programa guarda nomes, contatos e descrições de pacientes.
> Confirme com a Liga se pode guardar esses dados numa conta pessoal na nuvem (LGPD).
> Se preferir, simplesmente não conecte: tudo continua funcionando só neste computador.

## 1. Atualizar o programa
Substitua os arquivos do projeto pelos desta versão, envie ao GitHub (commit em `main`)
e crie a tag **v2.6.0** (Releases > Draft a new release). O programa instalado se
atualiza sozinho.

Arquivos novos/alterados: `nuvem.py`, `nuvem_gui.py`, `nuvem_sql.py`, `sincronizacao.py`,
`supabase_setup.sql`, `test_nuvem.py`, `database.py`, `gui.py`, `icons.py`, `theme.py`,
`README.md`, `.github/workflows/build-exe.yml`.

## 2. Preparar o Supabase (uma vez)
1. Abra um dos seus dois projetos (o plano gratuito não permite um terceiro). Só uma tabela nova
   (`solicitacoes_registros`) é criada; nada do que já existe é alterado.
2. **SQL Editor** > New query. Cole o conteúdo de `supabase_setup.sql`
   (ou use o botão **Copiar SQL de configuração** na página Nuvem) e clique em **Run**.
3. **Authentication > Users > Add user > Create new user**: informe um e-mail e uma senha
   e marque **Auto Confirm User**. (Use um usuário só para este programa.)
4. **Project Settings > API**: copie a **Project URL** e a chave **anon / publishable**.
   **Nunca** use a `service_role` / `secret`.

## 3. Conectar no programa
Menu **Nuvem**: cole a URL, a chave, o e-mail e a senha > **Conectar e sincronizar**.
Pronto: seus registros são enviados. Em outro computador, instale o programa, repita o passo 3
e os registros chegam.

## Bom saber
* Projetos gratuitos do Supabase pausam após 1 semana sem uso. Se o programa avisar que o
  Supabase está indisponível, abra o painel e clique em **Restore project**.
* O plano gratuito não inclui backup diário na nuvem: os backups locais continuam essenciais.
* Restaurar um backup (página Backup) passa a valer também na nuvem; registros que só existiam
  na nuvem não voltam sozinhos.
* **Desconectar** não apaga nada. Para apagar a cópia da nuvem, use o painel do Supabase
  (Table Editor > `solicitacoes_registros`).
