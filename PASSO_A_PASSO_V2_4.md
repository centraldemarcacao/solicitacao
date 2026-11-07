# Passo a passo — publicar e testar a versão 2.4

## Parte 1 — Enviar os arquivos para o GitHub

1. Descompacte o `anotacoes_hospitalares.zip` no computador.
2. Abra https://github.com/centraldemarcacao/solicitacao e clique em **Add file > Upload files**.
3. Arraste para a página os arquivos **soltos** da pasta (não a pasta inteira). Os
   que mudaram ou são novos nesta versão são:

   | Arquivo | Situação |
   |---|---|
   | `gui.py`, `widgets.py`, `paginas.py`, `database.py`, `util.py`, `icons.py`, `theme.py` | alterados |
   | `exportar.py`, `exportacao.py` | **novos (obrigatórios)** |
   | `test_database.py`, `test_util_exportar.py` | testes (novo e alterado) |
   | `README.md`, `PASSO_A_PASSO_V2_4.md` | documentação |

   Se enviar tudo de uma vez, também funciona. **Não envie a pasta `dados`.**
   Não é preciso mexer em `.github/workflows`: o fluxo atual já serve.
4. No fim da página, escreva "Versão 2.4" na mensagem e clique em **Commit changes**.
5. Abra `theme.py` no GitHub e confirme que a linha `VERSAO` mostra `"2.4"`.

## Parte 2 — Gerar a versão

1. No repositório, clique em **Releases > Draft a new release**.
2. Em **Choose a tag** digite `v2.4` e escolha **Create new tag: v2.4 on publish**.
3. Em **Release title** escreva `v2.4`. Deixe **Latest** marcado (não use Pre-release).
4. Se quiser, escreva em **Describe this release** um resumo curto (aparece no aviso de atualização).
5. Clique em **Publish release**.
6. Abra a aba **Actions** e espere a execução da v2.4 ficar verde (cerca de 2 minutos).
7. Volte em Releases > v2.4 e confira que aparecem `AnotacoesHospitalares.exe` e `SHA256.txt`.

## Parte 3 — Atualizar o programa instalado

1. Abra o programa que você já usa (v2.3). Em poucos segundos ele pergunta **Atualizar agora?**
   (ou clique em **Verificar atualizações** no menu lateral).
2. Clique em **Atualizar agora**. O programa fecha e abre de novo sozinho, já na v2.4.
3. Confirme no rodapé do menu: **v2.4**.

Seus registros continuam ali: a atualização não mexe na pasta `dados`.
Se algo der errado, o `.exe` anterior fica ao lado como `AnotacoesHospitalares.exe.anterior`.

## Parte 4 — Roteiro de teste (10 minutos)

Faça com registros de teste e exclua-os depois (Histórico > Excluir > Lixeira > Esvaziar).

**A. Formulário**
1. Em **Novo registro**, confira a ordem: Contato, Nome, Descrição, Retornar em.
2. O texto de dica do contato deve ser só `Ex.: (84) 99999-0000`; o rótulo deve ser apenas `Contato`.
3. Clique em **Salvar registro** com tudo vazio: deve avisar que falta o **Nome** e a **Descrição**.
4. Preencha Nome e Descrição, digite `99/99/2026` em "Retornar em" e salve: deve recusar a data.
5. Digite uma data passada: deve avisar "A data de retorno já passou."
6. Digite só números (ex.: `10112026`): as barras aparecem sozinhas.
7. Clique em **Amanhã**, salve: aparece "Registro salvo com sucesso." e os campos limpam.

**B. Retornos**
1. Em **Histórico**, o registro novo mostra **Amanhã** na coluna Retorno.
2. Crie outro e use **Editar** para colocar a data de hoje: a linha fica vermelha clara e mostra **Hoje**.
3. O cartão **Retornos a fazer** deve mostrar 1. O filtro **Retornos** deve listar só esse registro.
4. Marque o registro como **Atendida**: a cor vermelha some e o cartão volta para 0.
5. Feche e abra o programa com um retorno de hoje pendente: deve aparecer o aviso "Retornos a fazer".

**C. Busca, ordem e período**
1. Digite uma palavra que existe só na descrição de um registro: ele deve ser encontrado.
2. Clique no título **Nome**: ordena de A a Z (seta ▲); clique de novo: Z a A (▼).
3. Clique em **Retorno**: quem não tem retorno fica sempre no fim.
4. Escolha **Hoje**, **Últimos 7 dias** e **Este mês** no seletor de período.

**D. Exportar e imprimir**
1. Clique em **Exportar > Exportar para Excel (CSV)**, salve e abra no Excel: acentos corretos e uma coluna por campo.
2. Selecione 2 linhas e exporte de novo: o arquivo deve ter só essas 2.
3. Clique em **Exportar > Imprimir lista**: abre no navegador já com a janela de impressão.

**E. Visual**
1. Reduza a janela até o tamanho mínimo: os botões **Atendida, Pendente, Detalhes, Editar, Exportar, Excluir** devem continuar todos visíveis.
2. No menu lateral, **Backup** deve aparecer mesmo com a janela baixa.
3. Com a tabela vazia (filtro sem resultado), a mensagem fica abaixo dos títulos das colunas.

Se algo falhar, anote a tela e a mensagem (e o arquivo `dados/erros.log`, se existir).
