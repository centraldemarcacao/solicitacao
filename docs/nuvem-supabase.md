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
3. Crie o usuário do programa: pelo painel (**Authentication > Users > Add user > Create new user**,
   marcando **Auto Confirm User**) ou, sem abrir o painel, pelo script de administrador
   (veja [Criar usuários sem abrir o painel](#criar-usuários-sem-abrir-o-painel)). Use um usuário
   só para este programa.
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

## Painel de controle (administrador e usuário)
O menu **Painel** tem duas abas:

* **Meu painel**: qualquer usuário vê só os seus números (calculados neste computador).
* **Administração**: aparece apenas para administradores *confirmados pelo servidor*. Mostra as contas, os totais
  por conta (registros, pendentes, atendidas), permite **ativar/desativar o acesso** e **alterar o papel**, e lista
  as últimas ações. Nunca exibe nome, contato ou descrição de pacientes.

**Ativar (uma vez):**
1. No Supabase, SQL Editor, execute `supabase/setup.sql` e depois `supabase/painel.sql` (no programa:
   Painel > Administração > *Copiar SQL do painel*; antes do primeiro administrador, copie o arquivo do repositório).
2. Defina o primeiro administrador: `python scripts/usuarios_nuvem.py papel seu@email.com admin`
   (ou o `update` comentado no fim do `painel.sql`). Entre de novo no programa para valer.
   **Sem terminal (pelo GitHub):** em Settings > Secrets and variables > Actions, crie o segredo
   `SUPABASE_SERVICE_KEY` com a chave secreta; depois, em Actions > *Definir papel na nuvem* > Run workflow,
   informe o e-mail e o papel. **Sem GitHub:** no SQL Editor, rode o `update` comentado no fim do `painel.sql`.
3. Novos usuários (sem terminal): Supabase > Authentication > Users > Add user > Create new user, marcando *Auto Confirm User*. Pelo terminal: `python scripts/usuarios_nuvem.py criar EMAIL --gerar-senha [--admin]`.

**Como é protegido:** o papel fica em `app_metadata` (o usuário não consegue alterar); cada função do painel
confere o papel no banco a cada chamada; visitantes (`anon`) não executam nada; o programa nunca recebe a chave
secreta; cada ação administrativa é gravada em `painel_auditoria`. Ninguém desativa o próprio acesso nem remove o
próprio papel de administrador.

**Limites:** desativar uma conta bloqueia novos logins e renovações, mas quem já está conectado mantém a sessão até
o token expirar (cerca de 1 hora). Os dados da conta são mantidos. Dados de saúde: informe-se sobre a LGPD e use
o painel só com as pessoas autorizadas.

## Criar usuários sem abrir o painel
Para o **administrador** criar, listar ou trocar a senha de usuários direto do projeto, sem entrar
no Supabase:

```
python scripts/usuarios_nuvem.py listar
python scripts/usuarios_nuvem.py criar medico@hospital.org --gerar-senha
python scripts/usuarios_nuvem.py senha medico@hospital.org
```

* O script usa a chave **secreta** do projeto (*Project Settings > API Keys > Secret key*, ou a
  `service_role`). Informe-a na variável de ambiente `SUPABASE_SERVICE_KEY` (no PowerShell:
  `$env:SUPABASE_SERVICE_KEY = "sb_secret_..."`) ou digite quando o script pedir (não aparece na tela).
  Se a variável `SUPABASE_URL` (ou `--url`) não existir, usa o endereço de `anotacoes/nuvem/projeto.py`.
* **Essa chave nunca vai para o programa, o repositório ou o GitHub.** Ela dá controle total do projeto.
  O script recusa a chave pública para você não se confundir.
* `--gerar-senha` cria uma senha forte e a mostra **uma única vez**; sem ele, o script pede a senha duas
  vezes. A senha digitada nunca é exibida.
* O usuário nasce já confirmado e funciona **mesmo com o cadastro aberto desligado** (recomendado:
  *Authentication > Sign In / Providers > Allow new users to sign up = desligado*), então ninguém de
  fora consegue criar conta.
* Cada conta vê só os próprios registros. Para dois computadores compartilharem o histórico, entre nos
  dois com o **mesmo** e-mail e senha.
* Remover um usuário continua sendo feito no painel (*Authentication > Users*), porque apaga também os
  registros dele na nuvem.

### Botão "Criar conta" (desligado por padrão)
A página Nuvem pode mostrar um botão **Criar conta** (cria a conta com o e-mail e a senha digitados,
mínimo de 8 caracteres). Ele vem **desligado**: `PERMITIR_CADASTRO = False` em
`anotacoes/nuvem/projeto.py`.

* Esse arquivo é público, então ligar o botão **não abre** nada por si só: quem decide se alguém pode
  se cadastrar é o Supabase (*Allow new users to sign up*). Com o cadastro fechado, o botão responde
  "o cadastro de novas contas está desativado".
* Uso pontual: ligue o cadastro no Supabase, ligue `PERMITIR_CADASTRO`, deixe as pessoas criarem as contas
  e **desfaça os dois**. Se o Supabase exigir confirmação de e-mail, a pessoa confirma o e-mail e depois
  clica em *Conectar*.
* Para a maioria dos casos, prefira o script de administrador: nada fica aberto para terceiros.

