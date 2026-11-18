# Personalizar e proteger o programa

* [Personalizar nome, logo e ícone](#personalizar-nome-logo-e-ícone)
* [Segurança: PIN, bloqueio e backups criptografados](#segurança-pin-bloqueio-e-backups-criptografados)

## Personalizar nome, logo e ícone

Cada computador tem a sua própria identidade, sem mexer em arquivos nem no `.exe`.

1. No rodapé do menu lateral, clique no botão com o **lápis**.
2. Digite o **Nome** e o **Subtítulo** (opcional).
3. **Escolher imagem...**: PNG, JPG, BMP, GIF, WEBP ou ICO, até 10 MB. Imagens quadradas ou
   horizontais com fundo transparente (PNG) ficam melhores.
4. **Salvar**. Nome, logo, título da janela e ícone da barra de tarefas mudam na hora.

**Restaurar padrão** apaga a identidade personalizada deste computador.

### Onde fica
Na pasta de dados (`%LOCALAPPDATA%\AnotacoesHospitalares`): `identidade.json`, `logo_personalizado.png` e
`icone_personalizado.ico`. Não copie a pasta `dados` de um computador para outro (ela também
contém os registros). A atualização automática preserva tudo.

### Limites
* O ícone do **arquivo `.exe`** no Explorer não muda (é gravado no programa ao gerá-lo). Só o
  ícone da janela e da barra de tarefas muda.
* Para mudar o padrão de fábrica (nome inicial, cores, fonte): `anotacoes/theme.py` e um `.exe` novo.

### Arquivos da pasta `assets/`

| Arquivo | Uso |
|---------|-----|
| `icone.ico` | Ícone do `.exe` e da janela. Para gerar o padrão de novo: `python -m anotacoes.interface.icons`. |
| `logo.png` | **Opcional.** Logo padrão da barra lateral (fundo transparente ou branco). Se existir, é incluído no `.exe` automaticamente. Cada computador também pode trocar o logo pelo botão de lápis do programa, sem mexer aqui. |

O PyInstaller inclui esses arquivos no `.exe` (veja `scripts/build.bat` e `.github/workflows/release.yml`).

## Segurança: PIN, bloqueio e backups criptografados

Ative em **Configurações** (engrenagem no rodapé do menu, ou Ctrl + ,) > **Segurança**.

### O que protege
* **PIN/senha** (4 a 64 caracteres): guardado só como hash (scrypt com sal). Ao abrir o programa e
  após o tempo de inatividade escolhido, a tela fica bloqueada. **Ctrl + B** bloqueia na hora.
  Erros repetidos (3, 5 e 8 seguidos) impõem espera de 5 s, 30 s e 2 min.
* **Backups criptografados** (AES-256-GCM, chave derivada da senha com scrypt): arquivos `.dbx` na pasta
  de backups. Podem ser abertos em outro computador que conheça a senha. Use 8+ caracteres.

### O que NÃO protege
* O banco em uso (`anotacoes_hospitalares.db`, em `%LOCALAPPDATA%\AnotacoesHospitalares`) continua legível por quem tiver acesso a essa pasta.
  Combine com conta do Windows com senha e BitLocker. O PIN é uma barreira contra acesso casual.
* A espera por erros de PIN vale só enquanto o programa está aberto.

### Esqueci o PIN
Feche o programa e apague `seguranca.json` da pasta de dados (`%LOCALAPPDATA%\AnotacoesHospitalares`): ele abre sem PIN. Os backups `.dbx` continuam
exigindo a senha antiga: **sem ela, não há como recuperá-los**. Guarde-a em local seguro.

### Iniciar com o Windows
Alertas de pausa > "Abrir o programa ao ligar o computador (minimizado)". Grava uma entrada em
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (sem administrador) e só funciona com o `.exe`.
