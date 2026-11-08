# Personalizar nome e logo (versão 2.8)

## 1. Atualizar
Envie ao GitHub os arquivos desta versão e crie a tag **v2.8.0**. Arquivos novos/alterados:
`identidade.py`, `identidade_gui.py`, `test_identidade.py`, `perfil.py`, `gui.py`,
`exportar.py`, `main.py`, `theme.py`, `README.md`, `.github/workflows/build-exe.yml`.
Depois que o Actions terminar (marca verde), o programa instalado se atualiza sozinho
(botão **Atualizações** no rodapé do menu).

## 2. Personalizar (em cada computador)
1. No rodapé do menu lateral, clique no botão com o **lápis** (entre "Atualizações" e o tema).
2. Digite o **Nome** e o **Subtítulo** (o subtítulo é opcional).
3. Clique em **Escolher imagem...** e selecione o logo (PNG, JPG, BMP, GIF, WEBP ou ICO).
   Prefira uma imagem quadrada ou horizontal, de preferência com fundo transparente (PNG).
4. **Salvar**. O nome, o logo, o título da janela e o ícone da barra de tarefas mudam na hora.

Exemplo para a Intesoftware: Nome `Intesoftware Desenvolvimento`, Subtítulo `Anotações de clientes`.
Na Liga, não precisa fazer nada: continua "Liga Contra o Câncer".

## Bom saber
* Cada computador guarda a sua identidade na pasta `dados` ao lado do programa. Não copie a
  pasta `dados` de um computador para outro, ou os registros também seriam copiados.
* O ícone do **arquivo .exe** no Explorer não muda (ele é gravado no programa na hora de gerar o
  .exe). Só o ícone da janela e da barra de tarefas muda.
* **Restaurar padrão** (na própria janela) apaga a identidade personalizada deste computador.
* A página de impressão e a exportação usam o nome e o subtítulo que você definir.
* O `perfil.json` da versão 2.7 não é mais necessário; se existir, serve só como padrão inicial.
