# Histórico de versões

Formato: versão mais recente primeiro. As versões são publicadas em **Releases**
(tag `vX.Y.Z`); o programa instalado se atualiza sozinho a partir delas.

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
