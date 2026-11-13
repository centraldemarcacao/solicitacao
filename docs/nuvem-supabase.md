# Nuvem (Supabase)

A página **Nuvem** mantém uma cópia dos registros num projeto Supabase (plano gratuito). O banco
local continua sendo o principal: o programa funciona sem internet e envia o que ficou pendente
depois.

> **LGPD:** os registros podem conter dados pessoais (nome, contato, descrição). Confirme com a
> instituição se pode guardá-los numa conta pessoal na nuvem. Se não puder, simplesmente não
> conecte: tudo funciona só no computador.

## Como funciona
* Sincroniza ao abrir, a cada poucos minutos (se houver algo pendente) e ao fechar.
* Em conflito, vale a alteração mais recente. Lixeira, restauração e exclusão definitiva também
  sincronizam; na exclusão definitiva o texto é apagado da nuvem.
* Login com e-mail e senha de um usuário do projeto. A senha **não** é guardada; fica só um
  token de sessão em `nuvem.json` (pasta de dados, `%LOCALAPPDATA%\AnotacoesHospitalares`).
* A tabela usa segurança por linha (RLS): cada conta só enxerga as próprias linhas.
  A chave pública sozinha não dá acesso a nenhum dado.

## Configurar (uma vez por projeto)
1. Crie um projeto no [Supabase](https://supabase.com) (de preferência na região São Paulo).
2. **SQL Editor > New query**: cole o conteúdo de [`supabase/setup.sql`](../supabase/setup.sql)
   (ou use o botão **Copiar SQL de configuração** da página Nuvem) e clique em **Run**.
3. **Authentication > Users > Add user > Create new user**: e-mail e senha, marcando
   **Auto Confirm User**. Use um usuário só para este programa.
4. **Project URL**: na página inicial do projeto (botão **Copy** ao lado do nome) ou em
   *Settings > Data API*.
5. **Chave**: *Settings > API Keys > Publishable key* (`sb_publishable_...`).
   **Nunca** use a *Secret key* / `service_role` (o programa a recusa).
6. No programa: **Menu > Nuvem**, preencha URL, chave, e-mail e senha e clique em
   **Conectar e sincronizar**.

Para conferir, abra *Table Editor > `solicitacoes_registros`* no Supabase.

## Várias empresas ou computadores
* Cada computador/empresa pode ter **o seu próprio projeto** Supabase (recomendado quando os
  dados são de organizações diferentes). Os dados de um nunca se misturam com os de outro.
* O mesmo projeto pode ser usado em vários computadores da mesma pessoa: basta conectar em cada
  um com o mesmo usuário.
* Dar acesso a outras pessoas no **mesmo** projeto: cada usuário enxerga só os próprios
  registros, mas o dono do projeto enxerga tudo pelo painel. Desative *Allow new users to sign up*
  em *Authentication > Sign In / Providers* para impedir cadastros por terceiros.

## Bom saber
* Projetos gratuitos pausam após 1 semana sem uso: reative em **Restore project** no painel.
* O plano gratuito não inclui backup diário na nuvem; os backups locais continuam essenciais.
* Restaurar um backup (página Backup) passa a valer também na nuvem; registros que só existiam
  lá não voltam sozinhos.
* **Desconectar** não apaga nada. Para apagar a cópia, use o painel do Supabase.

## Projeto fixo e vários usuários
Para não pedir endereço e chave em cada computador, preencha uma vez `anotacoes/nuvem/projeto.py`
(`URL_PROJETO` e `CHAVE_PUBLICA`, a chave **anon / publishable**, nunca a secret). Depois disso, a página
Nuvem mostra só **e-mail e senha**.

* Para cada pessoa, crie um usuário em **Authentication > Users > Add user** (pode ser um e-mail sem
  caixa de entrada, como `maria@solicitacao.local`; marque **Auto Confirm User**). Cada usuário vê só os
  próprios registros.
* **Desative o cadastro aberto:** em **Authentication > Sign In / Providers** (ou "User Signups"),
  desligue **Allow new users to sign up**. Assim, mesmo com a chave pública visível no programa,
  só entra quem você criou.
* A chave pública foi feita para ficar no programa; a proteção vem do login e das regras do banco
  (`supabase/setup.sql`). Se o repositório for público, isso continua seguro, desde que o SQL tenha
  sido executado e o cadastro aberto esteja desligado.
