# Arquitetura

Aplicativo desktop (Windows) em Python 3.10+ com CustomTkinter e SQLite, distribuído como um
único `.exe` (PyInstaller, gerado pelo GitHub Actions).

## Camadas

```
main.py ──► anotacoes/app.py ──► interface/janela.py (App)
                                     │  mixins: páginas, atalhos, exportação,
                                     │  atualização, nuvem, identidade
                                     ▼
              nucleo/        nuvem/          atualizacao/
              (regras e      (Supabase +     (GitHub Releases)
               SQLite)        sincronização)
```

| Pasta | Responsabilidade | Depende de |
|-------|------------------|------------|
| `anotacoes/nucleo/` | Banco SQLite (`database.py`), validações e formatação (`util.py`), preferências, exportação CSV/HTML, identidade (nome/logo). **Sem interface.** | biblioteca padrão, Pillow, `theme.py` |
| `anotacoes/nuvem/` | Cliente HTTP do Supabase (`cliente.py`), motor de sincronização (`sincronizacao.py`) e o SQL de configuração (`sql.py`). **Sem interface.** | `nucleo/` |
| `anotacoes/atualizacao/` | Verificação, download, conferência SHA-256 e troca do `.exe` (`updater.py`). **Sem interface.** | biblioteca padrão |
| `anotacoes/interface/` | Janela principal (`janela.py`), componentes (`widgets.py`), ícones desenhados com Pillow (`icons.py`) e os *mixins* de cada área em `mixins/`. | todas as anteriores |
| `anotacoes/theme.py` | Marca, versão, repositório de atualização e paleta clara/escura. | — |
| `anotacoes/caminhos.py` | Onde ficam o `.exe`, a pasta `dados` e os recursos. | — |

Regra de ouro: `nucleo`, `nuvem` e `atualizacao` **não importam** a interface. Por isso são
testados sem tela (`tests/`).

## Janela principal e mixins
`App` (em `interface/janela.py`) herda de vários *mixins* em `interface/mixins/`, cada um dono de
uma área: `resumo` (resumo do dia), `paginas` (editar, lixeira, backup), `atalhos` (atalhos e
desfazer), `exportacao` (CSV e impressão), `atualizacao` (atualizador), `nuvem` (página e
sincronização em segundo plano) e `identidade` (janela Personalizar).

## Dados
Tudo fica na pasta `dados/` ao lado do `.exe` (ou `%LOCALAPPDATA%\AnotacoesHospitalares` se não
houver permissão de gravação):

| Arquivo | Conteúdo |
|---------|----------|
| `anotacoes.db` | Registros (SQLite). |
| `backups/` | Cópias automáticas (1 por dia, 14 guardadas) e manuais. |
| `preferencias.json` | Tema, tamanho da janela, filtros e ordenação. |
| `identidade.json`, `logo_personalizado.png`, `icone_personalizado.ico` | Nome, logo e ícone personalizados. |
| `nuvem.json` | Endereço, chave pública e token de sessão do Supabase (sem senha). |
| `erros.log` | Falhas inesperadas. |

Exclusão em duas etapas: `excluido_em` (lixeira, restaurável por 30 dias) e remoção definitiva.

## Sincronização com a nuvem
* Cada registro tem `uuid` (identidade global), `atualizado_em` (UTC, milissegundos) e `sujo`
  (ainda não enviado). **Gatilhos do SQLite** (`SYNC_SQL` em `database.py`) mantêm esses campos em
  qualquer inserção, edição ou exclusão, sem depender do restante do código.
* Exclusões definitivas viram linhas em `remocoes` e são enviadas como "marcas de remoção" que
  esvaziam o conteúdo na nuvem.
* `sincronizar()`: primeiro **baixa** o que mudou (paginação por chave `(atualizado_em, uuid)`),
  depois **envia** o que está pendente (lotes de 100, *upsert* por `uuid`). Vale a alteração mais
  recente. Falhas de rede deixam o pendente para a próxima vez.
* Segurança: login por e-mail/senha (token renovável) e RLS na tabela (`supabase/setup.sql`).

## Atualização automática
`updater.py` consulta `releases/latest` do repositório (`theme.REPOSITORIO_GITHUB`), baixa
`AnotacoesHospitalares.exe`, confere o SHA-256 de `SHA256.txt`, gera um `.bat` que troca o arquivo
(mantendo `.anterior`) e reabre o programa. Só aceita hosts `github.com` e `githubusercontent.com`.

## Convenções
* Português nos nomes de domínio e textos; funções curtas; docstrings no início de cada módulo.
* Cores e textos de marca são lidos **em tempo de uso** (`T.CONSTANTE`), nunca em valores padrão de
  funções: a troca de tema e a personalização dependem disso.
* CustomTkinter: `CTkLabel` não aceita `padx`/`justify`; defina `width` dos botões (o padrão é 140);
  use `height=1` em faixas `CTkFrame`; não destrua um botão dentro do próprio clique (use `after`);
  a ordem do Tab segue a criação dos widgets (use *bindings* explícitos).

## Testes
```
python -m unittest discover -s tests -t . -v      # unidade (sem tela, sem internet)
python tests/interface/simulacao_interface.py     # simulação da interface (sem tela)
```
`tests/` espelha os pacotes. O Supabase é simulado em `tests/nuvem/test_nuvem.py`. A simulação da
interface valida widgets e fluxos, mas **não** a aparência: o visual deve ser conferido no Windows.
