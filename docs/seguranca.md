# Segurança: PIN, bloqueio e backups criptografados

Ative em **Configurações** (engrenagem no rodapé do menu, ou Ctrl + ,) > **Segurança**.

## O que protege
* **PIN/senha** (4 a 64 caracteres): guardado só como hash (scrypt com sal). Ao abrir o programa e
  após o tempo de inatividade escolhido, a tela fica bloqueada. **Ctrl + B** bloqueia na hora.
  Erros repetidos (3, 5 e 8 seguidos) impõem espera de 5 s, 30 s e 2 min.
* **Backups criptografados** (AES-256-GCM, chave derivada da senha com scrypt): arquivos `.dbx` na pasta
  de backups. Podem ser abertos em outro computador que conheça a senha. Use 8+ caracteres.

## O que NÃO protege
* O banco em uso (`dados/solicitacoes.db`) continua legível por quem tiver acesso à pasta do programa.
  Combine com conta do Windows com senha e BitLocker. O PIN é uma barreira contra acesso casual.
* A espera por erros de PIN vale só enquanto o programa está aberto.

## Esqueci o PIN
Feche o programa e apague `dados/seguranca.json`: ele abre sem PIN. Os backups `.dbx` continuam
exigindo a senha antiga: **sem ela, não há como recuperá-los**. Guarde-a em local seguro.

## Iniciar com o Windows
Alertas de pausa > "Abrir o programa ao ligar o computador (minimizado)". Grava uma entrada em
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (sem administrador) e só funciona com o `.exe`.
