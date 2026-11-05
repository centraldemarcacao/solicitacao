# Gerar o .exe sem instalar nada (GitHub Actions)

O GitHub compila o programa em um servidor Windows dele e deixa o `.exe` para
download. Tudo é feito pelo navegador, sem instalar Python, Git ou qualquer
programa no computador.

> **Atenção (LGPD):** envie apenas o código. **Nunca** envie a pasta `dados`
> nem arquivos `.db`. O `.gitignore` deste projeto já bloqueia isso, mas
> não envie arquivos de pacientes por conta própria.

## 1. Criar o repositório (uma única vez)

1. Crie uma conta gratuita em https://github.com (se ainda não tiver).
2. Clique em **+** (canto superior direito) > **New repository**.
3. Nome: `anotacoes-hospitalares`. Marque **Private** (privado).
4. Clique em **Create repository**.

## 2. Enviar os arquivos

1. Extraia o `anotacoes_hospitalares.zip` no computador.
2. No repositório, clique em **uploading an existing file**.
3. Abra a pasta extraída e arraste **o conteúdo dela** (não a pasta em si)
   para a página. `main.py` deve ficar na raiz do repositório.
4. Confira se a pasta **`.github`** apareceu na lista. Se não apareceu, siga o
   passo 2.1 abaixo.
5. Clique em **Commit changes**.

### 2.1 Se a pasta `.github` não for enviada

1. No repositório: **Add file** > **Create new file**.
2. No campo do nome, digite exatamente `.github/workflows/build-exe.yml`
   (ao digitar a `/`, o GitHub cria as pastas).
3. Abra o arquivo `build-exe.yml` do projeto no Bloco de Notas, copie todo o
   conteúdo e cole na caixa de texto.
4. Clique em **Commit changes**.

## 3. Gerar e baixar o .exe

1. Abra a aba **Actions** do repositório. (Se aparecer um botão para habilitar
   os workflows, clique nele.)
2. Em **Gerar executável (.exe)**, clique em **Run workflow** > **Run workflow**.
   O processo também roda sozinho a cada envio de código.
3. Aguarde de 3 a 6 minutos até aparecer o visto verde.
4. Clique na execução concluída. Na seção **Artifacts**, baixe
   **AnotacoesHospitalares-windows**.
5. Extraia o zip: ele contém `AnotacoesHospitalares.exe` e `SHA256.txt`.

O arquivo fica disponível por 30 dias. Depois disso, rode o workflow de novo.

## 4. Auditoria pela TI

* O código-fonte completo está no repositório e pode ser lido pela TI.
* `SHA256.txt` traz a assinatura do `.exe`. Para conferir no Windows:
  `certutil -hashfile AnotacoesHospitalares.exe SHA256`
  O resultado deve ser igual ao do arquivo.
* O log de cada compilação fica na aba **Actions**.

## 5. Se algo falhar

| Sintoma | O que fazer |
|---------|-------------|
| Círculo vermelho na aba Actions | Abra a execução e veja qual passo falhou |
| "No file ... requirements.txt" | Os arquivos foram enviados dentro de uma subpasta; envie o conteúdo na raiz |
| Passo "Testar se o executável abre" com aviso amarelo | O `.exe` foi gerado, mas fechou sozinho no teste; avise para investigarmos |
| Não aparece o botão **Run workflow** | Confirme que `.github/workflows/build-exe.yml` está no repositório |
| Rede da instituição bloqueia o GitHub | Faça o envio e o download de outro computador (por exemplo, o de casa) |
