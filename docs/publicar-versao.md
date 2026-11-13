# Publicar uma versão nova

O programa instalado verifica o GitHub e se atualiza sozinho. Para lançar uma versão:

## Pré-requisitos (uma vez)
* O repositório precisa ser **público** (o programa consulta as Releases sem login).
  **Nunca** envie dados de pacientes ou clientes ao repositório (`dados/` já está no `.gitignore`).
* Em `anotacoes/theme.py`: `REPOSITORIO_GITHUB = "usuario/repositorio"`.

## Passo a passo
1. Envie o código para a branch `main` (commit e push). O workflow **Testes (CI)** roda os testes e a
   verificação da interface (aba **Actions**); isso **não** gera `.exe` nem publica uma versão. Espere a marca verde.
2. Em **Releases > Draft a new release**, clique em **Choose a tag**, digite `v2.9.0`
   (sempre com `v`; a tag decide a versão que o programa passa a ter) e escolha *Create new tag on publish*.
3. Título: `v2.9.0`. Clique em **Publish release**.
4. O workflow **Publicar versão (.exe)** roda os testes de novo, gera o `.exe`, confere se ele abre, ajusta o
   número da versão no programa e anexa `Anotacoes.exe`, o instalador e `SHA256.txt` à Release (leva alguns
   minutos; espere a marca verde). **Se qualquer teste falhar, nada é publicado**: corrija e crie a tag de novo.
5. Nos computadores que usam o programa: botão **Atualizações** no rodapé do menu (ou espere a
   verificação automática ao abrir).

Pela linha de comando: `git tag v2.9.0 && git push origin v2.9.0`.

Para só obter um `.exe` de teste, sem Release: **Actions > Publicar versão (.exe) > Run workflow**; o arquivo
fica em *Artifacts* da execução (30 dias).

## Primeira instalação
A forma mais simples é o **`Anotacoes-Instalador.exe`** da página **Releases**: instala sem administrador, cria os atalhos e o desinstalador. (Se o passo "Gerar o instalador" do Actions falhar, a Release sai só com o `.exe` solto; abra o log desse passo.) Alternativa sem instalar:

Baixe `Anotacoes.exe` da página **Releases** e copie para uma pasta onde o usuário
possa gravar (Documentos, Área de Trabalho). Os dados ficam em `%LOCALAPPDATA%\AnotacoesHospitalares` (pasta fixa do usuário), então o `.exe` pode ficar em qualquer lugar e ser atualizado sem perder nada.

## Se algo não funcionar
| Sintoma | O que fazer |
|---------|-------------|
| Janela preta repetindo `ping` ao atualizar (v2.9.0 e v2.10.0) | Defeito do script de troca antigo (corrigido na 2.10.1, que troca o `.exe` sem script). Nessas versões, aguarde o programa reabrir (ou feche a janela) e atualize manualmente: baixe o `.exe` em **Releases** e copie por cima do atual (mantenha a pasta `dados`). Nas versões novas, consulte `atualizacao.log` ao lado do `.exe`. |
| Release só com "Source code" (sem `.exe` nem `SHA256.txt`) e nenhuma execução nova em **Actions** | A tag foi criada sem o `v` (ex.: `2.10.0`) em um commit cujo workflow não a reconhecia. Apague a Release e a tag e publique de novo como `v2.10.0`, depois que o commit mais recente da `main` tiver passado no Actions. |
| Tag criada e nenhuma Release apareceu | Algum teste obrigatório falhou: abra a execução em **Actions** e veja o passo em vermelho. Corrija, apague a tag (`git push --delete origin v2.9.0`) e crie de novo. |
| Release sem o `.exe` | Veja a aba **Actions**: o passo que falhou aparece em vermelho. |
| `.exe` da Release com versão antiga | A tag foi criada antes de enviar o código novo. Envie tudo, apague a tag e a Release e crie de novo. |
| "Atualizações" diz que está em dia | Confira se a tag é maior que a versão instalada e se a Release foi *publicada* (não rascunho). |
| "CERTIFICATE_VERIFY_FAILED" / "unable to get local issuer certificate" | A rede inspeciona a conexão segura e o certificado dela não é reconhecido. Peça à TI o certificado raiz da instituição (.pem, .crt ou .cer) e, no programa, use **Configurações > Diagnóstico > Importar certificado da rede** (ele é salvo como `ca-extra.pem` na pasta de dados). A verificação não é desligada. |
| Rede da instituição bloqueia o GitHub | A verificação falha em silêncio e o programa funciona normalmente. |

## Gerar o `.exe` no seu computador (sem GitHub)
Dê duplo clique em `scripts/build.bat` (requer Python 3.10+). O resultado fica em `dist/`.
