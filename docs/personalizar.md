# Personalizar nome, logo e ícone

Cada computador tem a sua própria identidade, sem mexer em arquivos nem no `.exe`.

1. No rodapé do menu lateral, clique no botão com o **lápis**.
2. Digite o **Nome** e o **Subtítulo** (opcional).
3. **Escolher imagem...**: PNG, JPG, BMP, GIF, WEBP ou ICO, até 10 MB. Imagens quadradas ou
   horizontais com fundo transparente (PNG) ficam melhores.
4. **Salvar**. Nome, logo, título da janela e ícone da barra de tarefas mudam na hora.

**Restaurar padrão** apaga a identidade personalizada deste computador.

## Onde fica
Na pasta de dados (`%LOCALAPPDATA%\AnotacoesHospitalares`): `identidade.json`, `logo_personalizado.png` e
`icone_personalizado.ico`. Não copie a pasta `dados` de um computador para outro (ela também
contém os registros). A atualização automática preserva tudo.

## Limites
* O ícone do **arquivo `.exe`** no Explorer não muda (é gravado no programa ao gerá-lo). Só o
  ícone da janela e da barra de tarefas muda.
* Para mudar o padrão de fábrica (nome inicial, cores, fonte): `anotacoes/theme.py` e um `.exe` novo.
