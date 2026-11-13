# Histórico de versões

Formato: versão mais recente primeiro. As versões são publicadas em **Releases**
(tag `vX.Y.Z`); o programa instalado se atualiza sozinho a partir delas.

## 2.12.0 — Modelos de descrição, instalador e boas-vindas
* **Modelos de descrição:** botões com frases prontas ("Solicita água.", "Solicita travesseiro."...) no
  formulário Novo registro. Um clique insere o texto (em nova linha, se já houver algo). **Editar modelos**
  permite trocar, adicionar (até 10) e remover; ficam em `preferencias.json`.
* **Instalador:** cada Release traz também `Anotacoes-Instalador.exe`, que instala só para o usuário (sem
  administrador), cria atalhos na **Área de Trabalho** e no **Menu Iniciar** e um desinstalador. Os dados
  ficam fora da pasta do programa e **não são apagados** ao atualizar, reinstalar ou desinstalar. O `.exe`
  solto continua disponível. O instalador não tem assinatura digital: o Windows pode pedir confirmação.
* **Assistente de boas-vindas** (só em instalação nova, uma vez): começar do zero, entrar pela nuvem
  ("já uso em outro computador") ou **restaurar um backup**.
* **Restaurar de um arquivo** (página Backup): restaura um backup `.db`/`.dbx` de qualquer pasta, como
  pendrive ou OneDrive, e não só os da pasta de backups.

## 2.11.1 — Segurança, início com o Windows e diagnóstico
* **Projeto Supabase fixo:** o endereço e a chave pública do projeto passam a ficar no arquivo `anotacoes/nuvem/projeto.py` (preenchidos uma vez). Com os dois preenchidos, a página Nuvem pede **só e-mail e senha**, e o mesmo projeto vale em todos os computadores. Para dar acesso a outra pessoa, basta criar um novo usuário no Supabase.
* **Novo nome do arquivo:** o executável passa a se chamar `Anotacoes.exe` (sem acento, porque o GitHub troca letras acentuadas no nome dos arquivos publicados e isso quebraria a atualização). A Release também traz uma cópia com o nome antigo, `AnotacoesHospitalares.exe`, para que os programas já instalados continuem se atualizando. Quem já usa o programa mantém o arquivo como está; o nome só muda em novas instalações. O nome mostrado na janela continua o que você definir em Personalizar.
* **Dados em pasta fixa:** o programa passa a guardar tudo em `%LOCALAPPDATA%\AnotacoesHospitalares`, e não mais ao lado do `.exe`. Mover o `.exe`, baixá-lo de novo ou atualizá-lo não faz mais os dados "sumirem". Quem já tinha a pasta `dados` ao lado do `.exe` tem o conteúdo **copiado** na primeira abertura (a original fica como backup, com um `LEIA-ME.txt`).
* **Certificado da rede:** novo botão **Importar certificado da rede** (Configurações > Diagnóstico) que valida e instala o certificado raiz fornecido pela TI, sem editar arquivos à mão. O aviso de erro agora quebra em linhas (antes ficava cortado na janela). A verificação continua sempre ligada.
* **Correção antes da publicação:** o atalho Ctrl + , fazia o programa fechar ao abrir ("bad event type or keysym COMMA"). Corrigido e coberto por teste.
* **PIN ou senha** (Configurações > Segurança): o programa pode abrir e **bloquear sozinho** após 1 a 30
  minutos sem uso (**Ctrl + B** bloqueia na hora). Erros repetidos impõem espera crescente.
* **Backups criptografados** (AES-256-GCM, arquivos `.dbx`) com a mesma senha; a restauração pede a senha.
  Os backups antigos podem ser convertidos com um clique. **Guarde a senha**: sem ela o backup não abre.
  O PIN protege o uso do programa; o banco em uso continua legível por quem acessa a pasta (veja
  `docs/seguranca.md`).
* **Iniciar com o Windows, minimizado**: opção na janela Alertas de pausa; os avisos de pausa funcionam
  sem abrir o programa à mão. Só uma janela do programa abre por vez.
* **Diagnóstico** (Configurações): versão, pastas, estado da proteção e **teste de conexão** com GitHub e
  Supabase, com explicação do problema (certificado, rede, endereço).
* Teste de interface com o Tk real no GitHub Actions (`tests/interface/fumaca_tk_real.py`), inicialmente
  sem bloquear a entrega.
* Nova dependência: `cryptography`.

## 2.10.1 — Correção da atualização automática
* **Fim da tela de comando ao atualizar.** Antes, a troca do `.exe` dependia de um script `.bat` que
  ficava repetindo `ping` (abrindo e fechando janelas de console) enquanto esperava o programa fechar.
  Agora o próprio programa renomeia o `.exe` em uso (o Windows permite), coloca o novo no lugar e o
  reabre: sem script, sem janelas e sem espera.
* Se o Windows ou um antivírus não permitir renomear o programa em uso, entra em ação uma reserva: um
  script **oculto** e com **tempo limite** (não fica em laço), que confere o resultado pelos arquivos,
  restaura a versão anterior se falhar e registra tudo em `atualizacao.log` (ao lado do `.exe`).
* Se uma atualização baixada não puder ser aplicada, o programa avisa ao abrir. O `.exe` da versão
  anterior (`.exe.anterior`) é apagado sozinho na próxima abertura.
* Computadores ainda na v2.9.0 ou v2.10.0 usam o script antigo ao atualizar para esta versão: nesses,
  baixe o `.exe` na página **Releases** e copie por cima do atual (a pasta `dados` não muda).

## 2.10.0 — Alertas de pausa
* Janela de aviso, com sinal sonoro, às **14:40** (Pausa NR 17), **17:00** (Pausa para lanche) e
  **18:10** (Pausa NR 17). Aparece mesmo com o programa minimizado e não bloqueia o trabalho.
* Botão de **sino** no relógio do menu lateral abre a janela **Alertas de pausa**: liga/desliga e
  permite **mudar os três horários** (aceita 14:40, 14h40 ou 1440; restaurar padrão). **Ctrl + L** liga/desliga
  direto. Fica em `preferencias.json` (`alertas_pausa` e `horarios_pausa`).
* **Correção:** "CERTIFICATE_VERIFY_FAILED" ao verificar atualizações (e na nuvem) em redes que inspecionam a
  conexão segura. O programa passa a confiar também nos certificados do Windows e em um `ca-extra.pem`
  opcional na pasta `dados`. A verificação do certificado continua sempre ativa.

## 2.9.0 — Organização do projeto
* Código reorganizado em pacote: `anotacoes/` (`nucleo`, `nuvem`, `atualizacao`, `interface`),
  com `tests/`, `docs/`, `assets/`, `scripts/` e `supabase/` (veja `docs/arquitetura.md`).
* Documentação consolidada em `docs/` e histórico movido para este arquivo.
* Removido o `perfil.json` (substituído pela janela **Personalizar**, desde a 2.8).
* Comportamento do programa e dados: sem alterações.

## 2.8.0 — Personalizar (nome, logo e ícone)
* Botão de **lápis** no rodapé do menu lateral abre a janela **Personalizar**: nome, subtítulo
  e logo (PNG, JPG, BMP, GIF, WEBP ou ICO, até 10 MB). O ícone da janela e da barra de tarefas
  é gerado do logo.
* Salvo na pasta `dados` de cada computador (`identidade.json`, `logo_personalizado.png`,
  `icone_personalizado.ico`). "Restaurar padrão" volta ao de fábrica.
* Botão "Verificar atualizações" passou a se chamar "Atualizações".

## 2.7.0 — Perfis por empresa
* Nome e subtítulo vindos de um `perfil.json` ao lado do `.exe` (recurso substituído na 2.8/2.9).

## 2.6.0 — Nuvem (Supabase)
* Página **Nuvem**: cópia dos registros num projeto Supabase gratuito, sincronizada sozinha
  (ao abrir, a cada poucos minutos e ao fechar). O banco local continua sendo o principal e o
  programa funciona sem internet.
* Em conflito vale a alteração mais recente. Lixeira, restauração e exclusão definitiva também
  sincronizam (a exclusão definitiva apaga o texto do paciente na nuvem).
* Login por e-mail e senha (a senha não é guardada) e regras de acesso por linha (RLS).
  Chaves secretas são recusadas.

## 2.5.2
* Trocar o tema várias vezes seguidas podia deixar a janela vazia: a troca agora é protegida e,
  se algo falhar, volta ao tema claro e avisa (detalhes em `dados/erros.log`).

## 2.5.1
* Menu lateral compacto: os itens ocupavam 200 px cada um e escondiam "Backup" e o rodapé.
* Tab no formulário: Contato, Nome, Descrição, Retornar em (Shift+Tab volta). Vale na edição.

## 2.5.0
* **Prioridade** (caixa "Urgente"), com selo "URG", filtro e ordenação.
* **Resumo do dia**: retornos de hoje/atrasados, urgentes pendentes e pendentes há mais de 7 dias.
* Lembra tamanho/posição da janela, ordenação, filtros e tema (`dados/preferencias.json`).
* Atalhos: Ctrl+N, Ctrl+F, Ctrl+E, Ctrl+P, Ctrl+Z (desfazer), Ctrl+T (tema), F1 (lista).
* **Tema escuro**, com contraste mínimo de 4,5:1.

## 2.4.0
* Formulário: Contato, Nome e Descrição ("Nome do paciente" virou "Nome").
* **Retorno (lembrete)**: campo "Retornar em", filtro **Retornos** e aviso ao abrir.
* Busca também na descrição; ordenação por coluna; filtro por período.
* **Exportar** para Excel (CSV) e **imprimir** a lista.

## 2.2.0
* **Atualização automática** pelo GitHub (confere a assinatura SHA-256, faz backup e reabre).

## 2.1.0
* **Editar** registros (botão, F2 ou clique direito).
* **Lixeira**: excluir envia para a lixeira, com restauração em até 30 dias.
* **Backup** automático (1 por dia, 14 guardados), manual e restauração.

## 2.0.0
* Primeira versão: registro de solicitações, histórico pesquisável, status
  (pendente/atendida), banco SQLite local.
