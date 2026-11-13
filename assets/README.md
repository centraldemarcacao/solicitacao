# Recursos do programa

| Arquivo | Uso |
|---------|-----|
| `icone.ico` | Ícone do `.exe` e da janela. Para gerar o padrão de novo: `python -m anotacoes.interface.icons`. |
| `logo.png` | **Opcional.** Logo padrão da barra lateral (fundo transparente ou branco). Se existir, é incluído no `.exe` automaticamente. Cada computador também pode trocar o logo pelo botão de lápis do programa, sem mexer aqui. |

O PyInstaller inclui esses arquivos no `.exe` (veja `scripts/build.bat` e `.github/workflows/release.yml`).
