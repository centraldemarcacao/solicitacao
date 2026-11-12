# Publicar uma versão nova

O programa instalado verifica o GitHub e se atualiza sozinho. Para lançar uma versão:

## Pré-requisitos (uma vez)
* O repositório precisa ser **público** (o programa consulta as Releases sem login).
  **Nunca** envie dados de pacientes ou clientes ao repositório (`dados/` já está no `.gitignore`).
* Em `anotacoes/theme.py`: `REPOSITORIO_GITHUB = "usuario/repositorio"`.

## Passo a passo
1. Envie o código para a branch `main` (commit e push). O GitHub Actions roda os testes e gera o
   `.exe` (aba **Actions**); isso ainda **não** publica uma versão.
2. Em **Releases > Draft a new release**, clique em **Choose a tag**, digite `v2.9.0`
   (sempre com `v`; a tag decide a versão que o programa passa a ter) e escolha *Create new tag on publish*.
3. Título: `v2.9.0`. Clique em **Publish release**.
4. O Actions gera o `.exe`, ajusta o número da versão no programa e anexa
   `AnotacoesHospitalares.exe` e `SHA256.txt` à Release (leva alguns minutos; espere a marca verde).
5. Nos computadores que usam o programa: botão **Atualizações** no rodapé do menu (ou espere a
   verificação automática ao abrir).

Pela linha de comando: `git tag v2.9.0 && git push origin v2.9.0`.

## Primeira instalação
Baixe `AnotacoesHospitalares.exe` da página **Releases** e copie para uma pasta onde o usuário
possa gravar (Documentos, Área de Trabalho). A pasta `dados` é criada ao lado do `.exe`.

## Se algo não funcionar
| Sintoma | O que fazer |
|---------|-------------|
| Janela preta repetindo `ping` ao atualizar (v2.9.0) | Defeito do script de troca da v2.9.0 (já corrigido na 2.10.1). Feche a janela, aguarde o programa reabrir e atualize manualmente: baixe o `.exe` em **Releases** e copie por cima do atual (mantenha a pasta `dados`). Nas versões novas, veja `atualizacao.log` ao lado do `.exe`. |
| Release só com "Source code" (sem `.exe` nem `SHA256.txt`) e nenhuma execução nova em **Actions** | A tag foi criada sem o `v` (ex.: `2.10.0`) em um commit cujo workflow não a reconhecia. Apague a Release e a tag e publique de novo como `v2.10.0`, depois que o commit mais recente da `main` tiver passado no Actions. |
| Release sem o `.exe` | Veja a aba **Actions**: o passo que falhou aparece em vermelho. |
| `.exe` da Release com versão antiga | A tag foi criada antes de enviar o código novo. Envie tudo, apague a tag e a Release e crie de novo. |
| "Atualizações" diz que está em dia | Confira se a tag é maior que a versão instalada e se a Release foi *publicada* (não rascunho). |
| "CERTIFICATE_VERIFY_FAILED" / "unable to get local issuer certificate" | A rede inspeciona a conexão segura e o certificado dela não é reconhecido. Peça à TI o certificado raiz da instituição (.pem/.crt em Base-64), salve-o como `ca-extra.pem` na pasta `dados` ao lado do `.exe` e reabra o programa. A verificação não é desligada. |
| Rede da instituição bloqueia o GitHub | A verificação falha em silêncio e o programa funciona normalmente. |

## Gerar o `.exe` no seu computador (sem GitHub)
Dê duplo clique em `scripts/build.bat` (requer Python 3.10+). O resultado fica em `dist/`.
