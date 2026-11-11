# Solicitações

Aplicativo desktop para **Windows** que registra solicitações de atendimento (pacientes, clientes…)
de forma rápida: formulário simples, histórico pesquisável, status, lembretes de retorno, lixeira,
backups automáticos e, se quiser, cópia na nuvem. Feito em Python com CustomTkinter e SQLite, e
entregue como um único `.exe` que se atualiza sozinho.

## Funcionalidades
* **Registro rápido**: Contato, Nome, Descrição, data de retorno e prioridade *Urgente*.
* **Resumo do dia**: retornos de hoje ou atrasados, urgentes e pendências antigas.
* **Histórico**: busca sem diferenciar acentos, filtros (status, retornos, urgentes, período),
  ordenação por coluna, edição, status em lote e detalhes.
* **Exportar e imprimir**: CSV para Excel e página de impressão.
* **Lixeira** (30 dias) e **Backup** automático/manual com restauração.
* **Desfazer** (Ctrl+Z), atalhos de teclado (F1 mostra todos) e tema claro/escuro.
* **Nuvem (opcional)**: sincronização com Supabase gratuito, com uso offline.
* **Alertas de pausa**: avisos às 14:40 (NR 17), 17:00 (lanche) e 18:10 (NR 17); horários editáveis e liga/desliga no sino do menu (Ctrl + L).
* **Personalizar**: nome, subtítulo e logo por computador.
* **Atualização automática** pelo GitHub Releases, com conferência SHA-256.

## Estrutura do repositório

```
.
├── main.py                    # ponto de entrada (python main.py)
├── anotacoes/                 # código do programa
│   ├── app.py                 #   inicialização
│   ├── theme.py               #   marca, versão e paleta de cores
│   ├── caminhos.py            #   pastas do programa, dados e recursos
│   ├── nucleo/                #   regras e dados (sem interface)
│   │   ├── database.py        #     SQLite, lixeira, backups, gatilhos de sincronização
│   │   ├── util.py            #     validações e formatação
│   │   ├── preferencias.py    #     preferências do usuário
│   │   ├── pausas.py          #     horários dos alertas de pausa
│   │   ├── certificados.py    #     HTTPS: certificados do Windows e ca-extra.pem
│   │   ├── exportar.py        #     CSV e página de impressão
│   │   └── identidade.py      #     nome, subtítulo, logo e ícone
│   ├── nuvem/                 #   Supabase (sem interface)
│   │   ├── cliente.py         #     login e API REST
│   │   ├── sincronizacao.py   #     motor de sincronização
│   │   └── sql.py             #     SQL de configuração
│   ├── atualizacao/
│   │   └── updater.py         #   atualização automática (GitHub Releases)
│   └── interface/             #   telas (CustomTkinter)
│       ├── janela.py          #     janela principal
│       ├── widgets.py, icons.py
│       └── mixins/            #     uma área por arquivo (resumo, páginas, nuvem…)
├── tests/                     # testes (espelha o pacote)
├── assets/                    # ícone e logo
├── supabase/setup.sql         # tabela e regras de segurança da nuvem
├── scripts/build.bat          # gera o .exe no seu computador
├── docs/                      # guias (arquitetura, publicar versão, nuvem, personalizar)
├── .github/workflows/         # CI: testa, gera o .exe e publica Releases
├── CHANGELOG.md               # histórico de versões
├── requirements.txt           # dependências de execução
└── requirements-dev.txt       # + PyInstaller
```

## Começando (desenvolvimento)
Requer Python 3.10+ (Windows; a interface usa a fonte Segoe UI).

```
python -m pip install -r requirements.txt
python main.py
```

Em desenvolvimento, os dados ficam em `dados/` na raiz do repositório (ignorada pelo Git).

## Testes
```
python -m unittest discover -s tests -t . -v      # unidade (sem tela, sem internet)
python tests/interface/simulacao_interface.py     # simulação da interface (sem tela)
```
A simulação valida widgets e fluxos, mas não a aparência; confira o visual no Windows.

## Gerar o `.exe`
* **No GitHub (recomendado):** cada envio para `main` roda os testes e gera o `.exe` (aba
  **Actions**). Ao criar uma tag `vX.Y.Z`, o `.exe` e o `SHA256.txt` são publicados em **Releases**
  e os programas instalados se atualizam sozinhos. Veja [docs/publicar-versao.md](docs/publicar-versao.md).
* **No seu computador:** duplo clique em `scripts/build.bat` (resultado em `dist/`).

## Instalação e uso
Copie `AnotacoesHospitalares.exe` para uma pasta com permissão de gravação (Documentos, Área de
Trabalho). Na primeira execução é criada a pasta `dados/` ao lado do `.exe` (ou
`%LOCALAPPDATA%\AnotacoesHospitalares`, se não houver permissão) com o banco, os backups e as
preferências. **Copie essa pasta de vez em quando para um pen drive ou nuvem pessoal.**

Atalhos principais: `Ctrl+N` novo · `Ctrl+S` salvar · `Ctrl+F` buscar · `F2` editar ·
`Delete` excluir · `Ctrl+Z` desfazer · `Ctrl+E` exportar · `Ctrl+P` imprimir · `Ctrl+T` tema ·
`F1` lista de atalhos.

## Documentação
* [Arquitetura](docs/arquitetura.md): camadas, dados, sincronização, convenções.
* [Publicar uma versão](docs/publicar-versao.md): tag, Release e atualização automática.
* [Nuvem (Supabase)](docs/nuvem-supabase.md): configuração e cuidados.
* [Personalizar nome, logo e ícone](docs/personalizar.md).
* [Histórico de versões](CHANGELOG.md).

## Segurança e privacidade (LGPD)
Registros podem conter **dados pessoais sensíveis**. Antes de usar em produção:
* obtenha autorização da TI e do responsável pela LGPD da instituição;
* restrinja o acesso à pasta `dados` e use criptografia de disco (BitLocker);
* defina política de backup e retenção conforme as normas da instituição;
* a nuvem é opcional: só conecte se a instituição permitir guardar esses dados fora do computador;
* o programa é um bloco de anotações e **não substitui** o prontuário oficial;
* o repositório é público (necessário para a atualização automática): **nunca** envie a pasta
  `dados` ou o `nuvem.json` (ambos estão no `.gitignore`).

## Problemas comuns
| Sintoma | Solução |
|---------|---------|
| `.exe` abre e fecha na hora | Gere novamente (o build usa `--collect-all customtkinter`); veja `dados/erros.log`. |
| Antivírus/SmartScreen bloqueia | Falso positivo comum com `--onefile`; peça liberação à TI (o `SHA256.txt` da Release serve de conferência). |
| "Python não encontrado" no `build.bat` | Instale o Python marcando *Add Python to PATH* (não pela Microsoft Store). |
| Aviso de erro inesperado | Veja `dados/erros.log`. |
| Textos pequenos demais | Em telas pequenas a interface reduz de propósito; use uma tela maior ou diminua a escala do Windows. |
