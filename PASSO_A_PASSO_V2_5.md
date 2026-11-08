# Passo a passo — publicar e testar a versão 2.5

## Parte 1 — Enviar os arquivos para o GitHub

1. Descompacte o `anotacoes_hospitalares.zip` no computador.
2. Abra https://github.com/centraldemarcacao/solicitacao e clique em **Add file > Upload files**.
3. Arraste os arquivos **soltos** da pasta (não a pasta inteira). Nesta versão:

   | Arquivo | Situação |
   |---|---|
   | `atalhos.py`, `preferencias.py`, `resumo.py` | **novos (obrigatórios)** |
   | `gui.py`, `widgets.py`, `paginas.py`, `database.py`, `util.py`, `icons.py`, `theme.py`, `exportar.py` | alterados |
   | `test_tema.py`, `test_preferencias.py`, `test_database.py`, `test_util_exportar.py` | testes (opcional) |
   | `README.md`, `PASSO_A_PASSO_V2_5.md` | documentação (opcional) |

   Se preferir, envie todos os arquivos `.py` de uma vez. **Não envie a pasta `dados`.**
   Sem os 3 arquivos novos o programa não abre.
   O fluxo em `.github/workflows` não precisa ser alterado.
4. Escreva "Versão 2.5" na mensagem e clique em **Commit changes**.
5. Abra `theme.py` no GitHub e confirme que `VERSAO` mostra `"2.5"`.

## Parte 2 — Gerar a versão

1. **Releases > Draft a new release**.
2. Em **Choose a tag** digite `v2.5` e escolha **Create new tag: v2.5 on publish**.
3. Título `v2.5`, deixe **Latest** marcado (nunca Pre-release).
4. Opcional: descreva as novidades (o texto aparece no aviso de atualização).
5. **Publish release**.
6. Na aba **Actions**, espere a execução da v2.5 ficar verde (cerca de 2 minutos).
7. Confira em Releases > v2.5 se aparecem `AnotacoesHospitalares.exe` e `SHA256.txt`.

## Parte 3 — Atualizar o programa instalado

1. Abra o programa (v2.4). Em poucos segundos ele pergunta **Atualizar agora?**
   (ou clique em **Verificar atualizações** no menu lateral).
2. Clique em **Atualizar agora**. Ele fecha e reabre sozinho na v2.5.
3. Confira **v2.5** no rodapé do menu.

Seus registros continuam ali. Se algo der errado, o `.exe` anterior fica como
`AnotacoesHospitalares.exe.anterior`. Os bancos antigos são atualizados sozinhos
(todos os registros existentes entram como prioridade "Normal").

## Parte 4 — Roteiro de teste (15 minutos)

Use registros de teste e depois exclua e esvazie a Lixeira.

**A. Prioridade**
1. Em **Novo registro**, na linha do "Nome", marque **Urgente**, preencha e salve. A caixa desmarca sozinha.
2. No **Histórico**, o registro mostra **URG** na primeira coluna.
3. Clique no filtro **Urgentes**: só ele aparece. Clique no título **Urg.**: urgentes vão para o topo.
4. Abra **Detalhes**: aparece a etiqueta vermelha "Urgente" ao lado do status.
5. Use **Editar**, desmarque Urgente e salve: o URG some.

**B. Resumo do dia**
1. Deixe um registro urgente pendente e um com retorno para hoje. Feche e abra o programa: ele abre em **Resumo do dia**.
2. Confira a saudação (Bom dia/Boa tarde/Boa noite), os 3 cartões e a lista "Para ver agora" com o motivo de cada item.
3. Clique em **Abrir** em um item: abrem os detalhes. **Novo registro** e **Ver pendentes no histórico** levam às outras telas.
4. Marque tudo como atendido: o resumo mostra "Nada pendente de atenção".
5. Com nada a ver, o programa abre direto em **Novo registro**.

**C. Atalhos e Desfazer**
1. Pressione **F1**: abre a lista de atalhos.
2. **Ctrl+N** vai para Novo registro com o cursor no Contato. **Ctrl+F** vai ao Histórico com o cursor na busca.
3. **Ctrl+E** abre "Salvar como" do CSV; **Ctrl+P** abre a impressão.
4. Marque um registro como Atendida e pressione **Ctrl+Z** (fora de campos de texto): volta a Pendente.
5. Exclua um registro e pressione **Ctrl+Z**: ele volta do lixo. Edite um registro e pressione **Ctrl+Z**: os dados anteriores voltam.
6. Dentro de um campo de texto, **Ctrl+Z** continua desfazendo a digitação (é o esperado).

**D. Tema escuro**
1. Clique na **lua** no rodapé do menu (ou Ctrl+T). Tudo muda para escuro e a tela atual, o formulário e os filtros continuam como estavam.
2. Percorra Resumo, Novo registro, Histórico, Lixeira e Backup: textos legíveis, botões coloridos com letras escuras, tabela e janelas (Detalhes, Editar, confirmação) no mesmo tema.
3. Clique no **sol**: volta ao claro.

**E. Preferências**
1. Mude o tamanho e a posição da janela, ordene por **Nome**, escolha o filtro **Pendentes** e o período **Hoje**, deixe o tema escuro e feche.
2. Abra de novo: tudo volta como estava. Se o arquivo `dados/preferencias.json` for apagado, o programa abre com os padrões.

**F. Visual**
1. Reduza a janela ao tamanho mínimo: na tabela todos os botões (**Atendida, Pendente, Detalhes, Editar, Exportar, Excluir**) e os 5 filtros (Todos, Pendentes, Atendidas, Retornos, Urgentes) continuam visíveis.
2. No menu lateral, os 5 itens aparecem; em janela baixa, o relógio some primeiro.
3. No formulário, a linha "Retornar em" e as mensagens de erro cabem sem cortar.

Se algo falhar, anote a tela e a mensagem (e `dados/erros.log`, se existir).
