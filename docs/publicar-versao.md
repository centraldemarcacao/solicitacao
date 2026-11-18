# Publicar uma versão nova

O programa instalado verifica o GitHub e se atualiza sozinho. Para lançar uma versão:

## Pré-requisitos (uma vez)
* O repositório precisa ser **público** (o programa consulta as Releases sem login).
  **Nunca** envie dados de pacientes ou clientes ao repositório (`dados/` já está no `.gitignore`).
* Em `anotacoes/theme.py`: `REPOSITORIO_GITHUB = "usuario/repositorio"`.

## Passo a passo
1. Envie o código para a branch `main` (commit e push). **Isso já publica a versão**: o workflow
   **Publicar versão (.exe)** (aba **Actions**) roda os testes e a verificação da interface, gera o `.exe`,
   confere se ele abre, e cria sozinho a Release e a tag `v2.13.N` (o `N` é o número da execução e só
   cresce) com `Anotacoes.exe`, o instalador e `SHA256.txt`. Leva alguns minutos; espere a marca verde.
   **Se qualquer teste falhar, nada é publicado**: corrija e envie de novo.
2. Nos computadores que usam o programa: botão **Atualizações** no rodapé do menu (ou espere a
   verificação automática ao abrir).

Detalhes:
* Envios que mudam **só documentação** (`*.md`, `docs/`) não publicam versão.
* O `2.13` vem de `VERSAO_BASE` no início de `.github/workflows/release.yml`. Para lançar a 2.14 ou 3.0,
  troque esse valor (o terceiro número continua subindo; nunca volta atrás).
* Quer uma versão com número exato (ex.: `v3.0.0`)? Crie e envie a tag: `git tag v3.0.0 && git push origin v3.0.0`.
  A Release usa o número da tag. (Garanta que ele seja **maior** que o da última Release, senão os
  programas instalados não atualizam.)
* Para só obter um `.exe` de teste, sem Release: **Actions > Publicar versão (.exe) > Run workflow**; o arquivo
  fica em *Artifacts* da execução (30 dias).
* Cada commit em `main` vira uma versão que chega aos computadores. Para testar antes, use uma branch e um
  pull request (que roda só os testes) e faça o *merge* quando estiver pronto.

## Primeira instalação
A forma mais simples é o **`Anotacoes-Instalador.exe`** da página **Releases**: instala sem administrador, cria os atalhos e o desinstalador. (Se o passo "Gerar o instalador" do Actions falhar, a Release sai só com o `.exe` solto; abra o log desse passo.) Alternativa sem instalar:

Baixe `Anotacoes.exe` da página **Releases** e copie para uma pasta onde o usuário
possa gravar (Documentos, Área de Trabalho). Os dados ficam em `%LOCALAPPDATA%\AnotacoesHospitalares` (pasta fixa do usuário), então o `.exe` pode ficar em qualquer lugar e ser atualizado sem perder nada.

## Se algo não funcionar
| Sintoma | O que fazer |
|---------|-------------|
| Janela preta repetindo `ping` ao atualizar (v2.9.0 e v2.10.0) | Defeito do script de troca antigo (corrigido na 2.10.1, que troca o `.exe` sem script). Nessas versões, aguarde o programa reabrir (ou feche a janela) e atualize manualmente: baixe o `.exe` em **Releases** e copie por cima do atual (mantenha a pasta `dados`). Nas versões novas, consulte `atualizacao.log` ao lado do `.exe`. |
| Release só com "Source code" (sem `.exe` nem `SHA256.txt`) e nenhuma execução nova em **Actions** | A tag foi criada sem o `v` (ex.: `2.10.0`) em um commit cujo workflow não a reconhecia. Apague a Release e a tag e publique de novo como `v2.10.0`, depois que o commit mais recente da `main` tiver passado no Actions. |
| Enviei o código e nenhuma Release apareceu | Algum teste obrigatório falhou (ou o envio mudou só documentação): abra a execução em **Actions** e veja o passo em vermelho. Corrija e envie de novo. |
| Release sem o `.exe` | Veja a aba **Actions**: o passo que falhou aparece em vermelho. |
| `.exe` da Release com versão antiga | Só ocorre com tags criadas à mão antes de enviar o código novo. Envie tudo, apague a tag e a Release e crie de novo. |
| "Atualizações" diz que está em dia | Confira se a tag é maior que a versão instalada e se a Release foi *publicada* (não rascunho). |
| "CERTIFICATE_VERIFY_FAILED" / "unable to get local issuer certificate" | A rede inspeciona a conexão segura e o certificado dela não é reconhecido. Peça à TI o certificado raiz da instituição (.pem, .crt ou .cer) e, no programa, use **Configurações > Diagnóstico > Importar certificado da rede** (ele é salvo como `ca-extra.pem` na pasta de dados). Cada importação **acrescenta** o certificado à lista (GitHub e Supabase podem usar raízes diferentes; repetidos são ignorados). Dois casos comuns: (1) a rede troca o certificado: use o certificado raiz da instituição; (2) o Windows ainda não tem uma raiz pública nova (ex.: *Sectigo Public Server Authentication Root E46*, usada pelo GitHub): no Chrome, abra o site > cadeado > certificado > Detalhes, selecione o item **de cima** da hierarquia > Exportar > "ASCII codificado na Base64, certificado único", e importe. Aceita .pem/.crt/.cer (texto ou binário, com um ou vários certificados). A verificação não é desligada. |
| Rede da instituição bloqueia o GitHub | A verificação falha em silêncio e o programa funciona normalmente. |

## Gerar o `.exe` no seu computador (sem GitHub)
Dê duplo clique em `scripts/build.bat` (requer Python 3.10+). O resultado fica em `dist/`.

## Atualizar uma instalação existente (esta versão)
**1) GitHub (pelo navegador)**
1. Extraia o zip. No repositório: **Add file > Upload files**, arraste TODO o conteúdo extraído (inclusive `.github`, `anotacoes`, `docs`, `supabase`, `tests`) e faça o commit na `main`.
2. O envio **não apaga** arquivos antigos. Apague estes, um a um (abra o arquivo > menu **...** > **Delete file** > Commit), para o CI não achar testes ou guias velhos:
   * `anotacoes/nucleo/primeiro_uso.py`
   * `scripts/usuarios_nuvem.py` (e a pasta `scripts` fica só com `build.bat`)
   * `assets/README.md`
   * `docs/personalizar.md` e `docs/seguranca.md`
   * `tests/nucleo/test_modelos.py`, `tests/nucleo/test_pausas.py`
   * `tests/nucleo/test_certificados_importar.py`, `tests/nucleo/test_certificados_acumular.py`
   * `tests/nuvem/test_projeto.py`
3. Em **Actions**, espere **Testes (CI)** e **Publicar versão** ficarem verdes (a Release nova aparece em **Releases**).
4. Se for usar o botão "Definir papel na nuvem": Settings > Secrets and variables > Actions > segredo `SUPABASE_SERVICE_KEY`.

**2) Banco de dados (Supabase > SQL Editor)**
1. Abra uma consulta nova (**+**), cole o conteúdo de `supabase/painel.sql` e clique em **Run** (esperado: *Success*). Ele pode ser executado de novo sem problema e traz a função nova de criar usuário. Se nunca rodou o `setup.sql`, rode-o antes da mesma forma.
2. Defina o administrador: Actions > **Definir papel na nuvem** > Run workflow (e-mail + `admin`), ou rode no SQL Editor o `update` comentado no fim do `painel.sql`.

**3) Nos computadores:** o programa se atualiza sozinho (ou instale o `.exe` da Release por cima: dados e backups são preservados). Se a atualização acusar erro de certificado, veja a tabela de erros acima.

