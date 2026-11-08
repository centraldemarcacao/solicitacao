# Solicitações de Pacientes — Liga Contra o Câncer

Aplicação desktop (Windows) para registro rápido de solicitações de pacientes,
com banco SQLite local, histórico pesquisável, alteração de status, edição, lixeira e backups.

## Novidades da versão 2.1

* **Editar**: botão "Editar", tecla **F2** ou clique direito. Registros editados
  mostram "Editado em ..." nos detalhes.
* **Lixeira**: excluir não apaga de vez; o registro vai para a Lixeira e pode ser
  restaurado em até 30 dias (depois disso é removido automaticamente).
* **Backup**: cópia automática ao abrir e ao fechar o programa (1 por dia, as 14
  mais recentes ficam guardadas), backup manual e restauração pela página
  **Backup**. Antes de restaurar, o programa guarda uma cópia de segurança do
  estado atual.
* Os backups ficam em `dados/backups`, **no mesmo disco** do banco. Copie essa
  pasta de vez em quando para um pen drive ou nuvem pessoal.

## Correções da versão 2.5.2

* **Troca de tema:** trocar várias vezes seguidas podia deixar a janela vazia. Agora a troca espera o clique terminar, ignora cliques repetidos enquanto acontece e, se algo falhar, volta ao tema claro e avisa (detalhes em `dados/erros.log`).

## Correções da versão 2.5.1

* **Menu lateral:** os itens ocupavam 200 px de altura cada um e empurravam "Backup" (e o rodapé) para fora da tela. Agora ficam compactos.
* **Tab no formulário:** a ordem agora é Contato, Nome, Descrição, Retornar em (e depois volta ao Contato). Shift+Tab volta. Vale também na janela de edição.

## Novidades da versão 2.5

* **Prioridade:** caixa **Urgente** no formulário e na edição. Urgentes aparecem
  com "URG" na tabela, no filtro **Urgentes**, na ordenação pela coluna "Urg."
  e no resumo do dia.
* **Resumo do dia:** tela inicial (quando há algo a ver) com retornos de hoje ou
  atrasados, urgentes pendentes e pendentes há mais de 7 dias, com botão
  **Abrir** em cada item.
* **Lembra como você deixou:** tamanho e posição da janela, ordenação, filtros e
  tema (arquivo `dados/preferencias.json`).
* **Atalhos:** Ctrl+N novo, Ctrl+F buscar, Ctrl+E exportar, Ctrl+P imprimir,
  Ctrl+Z desfazer (status, exclusão e edição), Ctrl+T tema, F1 lista de atalhos.
* **Tema escuro:** botão com lua/sol no rodapé do menu (ou Ctrl+T). Todas as
  combinações de cores mantêm contraste mínimo de 4,5:1.

## Novidades da versão 2.4

* **Formulário:** a ordem agora é **Contato**, **Nome** e **Descrição**; o campo
  "Nome do paciente" virou "Nome" e o contato aceita qualquer informação.
* **Retorno (lembrete):** campo opcional "Retornar em" (dd/mm/aaaa, com atalhos
  Amanhã / Em 7 dias). Pendentes com retorno para hoje ou atrasados ficam com a
  linha vermelha clara, entram no indicador "Retornos a fazer", no filtro
  **Retornos** e em um aviso ao abrir o programa.
* **Busca e ordenação:** a busca agora também olha a descrição; clique no título
  de qualquer coluna para ordenar (clique de novo para inverter); filtro por
  período (Hoje, Últimos 7 dias, Este mês).
* **Exportar e imprimir:** botão **Exportar** > "Exportar para Excel (CSV)" ou
  "Imprimir lista". Vale para o que está na tabela (com filtros e ordem) ou só
  para as linhas selecionadas.

## Atualização automática (versão 2.2)

O programa confere, ao abrir, se há versão nova no GitHub e oferece
**"Atualizar agora"**: baixa o novo `.exe`, confere a assinatura SHA-256, faz
backup, troca o arquivo e reabre sozinho. Os dados não são alterados. O botão
**Verificar atualizações** (menu lateral) faz a checagem na hora. A versão
anterior fica ao lado como `AnotacoesHospitalares.exe.anterior`.

Configuração única:

1. (Já feito) Em `theme.py`, está configurado `REPOSITORIO_GITHUB = "centraldemarcacao/solicitacao"`
   (o repositório precisa ser **público**; não coloque dados de pacientes nele).
2. Para lançar uma versão nova, envie o código e crie a tag, por exemplo:
   `git tag v2.2 && git push origin v2.2`. O GitHub Actions gera o `.exe`,
   ajusta o número da versão e publica em **Releases**.
3. Os programas já instalados passam a receber a atualização sozinhos.

A primeira instalação com este recurso ainda precisa ser feita manualmente.
Se a rede da instituição bloquear o GitHub, a checagem falha em silêncio e o
programa funciona normalmente. O .exe deve ficar em pasta com permissão de
gravação (Documentos, Área de Trabalho).

## Estrutura de arquivos

```
anotacoes_hospitalares/
├── main.py            # Ponto de entrada
├── gui.py             # Janela principal: barra lateral, formulário e histórico
├── paginas.py         # Telas de edição, Lixeira e Backup
├── resumo.py          # Página 'Resumo do dia'
├── atalhos.py         # Atalhos de teclado e Desfazer
├── preferencias.py    # Preferências (tema, janela, filtros)
├── test_tema.py       # Contraste dos dois temas
├── test_preferencias.py
├── exportar.py        # CSV e página de impressão
├── exportacao.py      # Botão Exportar (telas)
├── test_util_exportar.py  # Testes de datas e exportação
├── updater.py         # Atualização: consulta, download, SHA-256 e troca do .exe
├── atualizacao.py     # Telas/fluxo da atualização
├── test_updater.py    # Testes da atualização
├── util.py            # Funções de texto/data
├── widgets.py         # Componentes visuais (menu, cartões, busca, avisos, diálogos)
├── icons.py           # Ícones e logotipo desenhados com Pillow
├── theme.py           # Cores, nome da instituição e fonte
├── database.py        # SQLite: schema automático e operações
├── requirements.txt   # Dependências
├── build.bat          # Gera o .exe com um duplo clique
├── GUIA_GITHUB_ACTIONS.md  # Gera o .exe pelo navegador, sem instalar nada
├── .github/workflows/build-exe.yml  # Fluxo do GitHub Actions
├── .gitignore         # Impede o envio de dados de pacientes
├── test_database.py   # Testes da camada de banco
├── icone.ico          # Ícone do programa (gerado por "python icons.py")
├── logo.png           # (opcional) logotipo oficial da instituição
└── dados/             # Criada automaticamente; contém o banco e o erros.log
```

## 1. Pré-requisitos (somente no computador onde o .exe será gerado)

* Windows 10/11
* Python **3.10 ou superior** (https://www.python.org/downloads/) —
  marque **"Add Python to PATH"** na instalação. Não instale pela Microsoft Store.

O computador que **usa** o programa não precisa de Python nem de instalação.

## 2. Rodar em modo de desenvolvimento

```bash
pip install -r requirements.txt
python main.py
```

Testes do banco de dados:

```bash
python -m unittest test_database test_updater test_util_exportar test_preferencias test_tema -v
```

## 3. Gerar o executável (.exe)

### Opção A — um clique

Dê duplo clique em **`build.bat`**. Ele localiza o Python sozinho, instala as
dependências e gera `dist\AnotacoesHospitalares.exe`. Se existirem
`icone.ico` e/ou `logo.png` na pasta, são incluídos automaticamente.

### Opção B — comando manual

```bash
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "AnotacoesHospitalares" --collect-all customtkinter --hidden-import PIL._tkinter_finder --icon "icone.ico" --add-data "icone.ico;." main.py
```

| Opção | Função |
|-------|--------|
| `--onefile` | Gera um único `.exe` |
| `--windowed` | Não abre janela de console preta |
| `--collect-all customtkinter` | Inclui temas e arquivos do CustomTkinter (**obrigatório**, senão o .exe abre e fecha) |
| `--hidden-import PIL._tkinter_finder` | Garante que as imagens/ícones funcionem no .exe |
| `--icon` / `--add-data` | Ícone do executável e da janela |

### Opção C — sem instalar nada (GitHub Actions)

O projeto inclui o fluxo `.github/workflows/build-exe.yml`, que gera o `.exe`
em um servidor Windows do GitHub. Veja o passo a passo em
**`GUIA_GITHUB_ACTIONS.md`**.

## 4. Distribuição

Copie **apenas** `AnotacoesHospitalares.exe` para o computador de destino, em
uma pasta onde o usuário possa gravar (Documentos, Área de Trabalho).
Na primeira execução, a pasta `dados` é criada ao lado do `.exe`. Se essa pasta
não permitir gravação, o programa usa `%LOCALAPPDATA%\AnotacoesHospitalares`.
O botão **Abrir pasta dos dados**, na barra lateral, mostra onde ficou.

> **Importante:** faça backup periódico da pasta `dados` — é lá que ficam
> todos os registros.

## 5. Uso

* **Novo registro:** preencha Nome (obrigatório), Contato e Descrição
  (obrigatória) e clique em **Salvar registro** (ou `Ctrl + S`). Os erros
  aparecem abaixo do campo. Limites: nome 120, contato 80 e descrição 2000
  caracteres. À direita, o resumo do dia e os últimos registros.
* **Histórico:**
  * Indicadores: total, pendentes e atendidas.
  * Busca por nome ou contato enquanto você digita (não diferencia maiúsculas
    nem acentos: "jose" encontra "José").
  * Filtro por status: Todos, Pendentes ou Atendidas.
  * Selecione uma ou mais linhas (Ctrl/Shift) e use **Marcar como atendida**
    ou **Marcar como pendente**.
  * **Ver detalhes:** botão, duplo clique ou Enter. Na janela de detalhes
    também é possível alterar o status.
  * **Excluir:** botão, tecla `Delete` ou clique direito. O programa pede
    confirmação, pois a exclusão é definitiva.
* Linhas âmbar claro = Pendente; verde claro = Atendida; azul-acinzentado
  suave = linha selecionada.
* **Telas pequenas ou com escala 125%/150%:** o programa reduz a interface
  automaticamente para caber na tela, sem cortar textos ou botões.

## 6. Personalizar a identidade visual

* **Cores, nome e fonte:** edite `theme.py` e gere o `.exe` novamente.
* **Logotipo oficial:** salve como `logo.png` na pasta do projeto (fundo
  transparente ou branco). Ele substitui a marca padrão na barra lateral,
  sobre uma placa branca.
* **Ícone do programa:** substitua `icone.ico`, ou rode `python icons.py`
  para gerar novamente o ícone padrão.

## 7. Segurança e privacidade (LGPD)

Dados de pacientes são **dados pessoais sensíveis**. Antes de usar em produção:

* Obtenha autorização da TI e do responsável pela LGPD da instituição.
* Restrinja o acesso à pasta `dados` (permissões do Windows).
* Use criptografia de disco (BitLocker) no computador.
* Defina política de backup e retenção conforme as normas da instituição.
* Esta ferramenta é um bloco de anotações de solicitações; **não substitui**
  o prontuário eletrônico oficial.
* Registros excluídos não podem ser recuperados.

## 8. Problemas comuns

| Sintoma | Solução |
|---------|---------|
| `.exe` abre e fecha na hora | Gere novamente com `--collect-all customtkinter` |
| Aviso de erro inesperado | Veja o arquivo `erros.log` na pasta `dados` |
| Antivírus ou SmartScreen bloqueia | Falso positivo comum com `--onefile`; solicite liberação à TI ou gere com `--onedir` |
| "Python não encontrado" ao rodar o `build.bat` | Instale o Python marcando "Add Python to PATH" (apenas no computador de build) |
| Textos pequenos demais | Em telas pequenas a interface é reduzida de propósito; use uma tela maior ou diminua a escala do Windows (Configurações > Sistema > Vídeo) |
| Logotipo não aparece | Confirme o nome `logo.png` e gere o `.exe` novamente |
