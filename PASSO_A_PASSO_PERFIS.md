# Duas empresas, um programa (versão 2.7)

Cada empresa usa uma **pasta própria** com o programa. Os dados, os backups e a
conexão com a nuvem ficam dentro da pasta, então nada se mistura.

## No computador da Liga (como já é)
Nada muda. Sem `perfil.json`, o programa continua "Liga Contra o Câncer".
Atualize pela tag **v2.7.0** (atualização automática). Se for usar a nuvem,
siga o `PASSO_A_PASSO_NUVEM.md` com o projeto Supabase **da Liga**.

## Neste computador (Intesoftware Desenvolvimento)
1. Crie uma pasta, por exemplo `C:\Intesoftware\Anotacoes`.
2. Copie para lá o `AnotacoesHospitalares.exe` (baixe da página Releases do GitHub).
3. Na mesma pasta, coloque o arquivo `perfil.json` com este conteúdo
   (o modelo é o `perfil_intesoftware.json`; basta copiar e renomear):

       {
         "nome": "Intesoftware Desenvolvimento",
         "subtitulo": "Anotações de clientes"
       }

4. Abra o programa. A barra lateral e o título da janela já mostram a Intesoftware,
   e a pasta `dados` é criada ao lado, vazia e separada da Liga.
5. (Opcional) Nuvem: use um projeto Supabase **só da Intesoftware**
   (`PASSO_A_PASSO_NUVEM.md`, passos 2 e 3).

## Cuidados
* Nunca copie a pasta `dados` de uma empresa para a outra.
* Os projetos Supabase ficam separados: um para a Liga, outro para a Intesoftware.
* O `perfil.json` precisa estar na **mesma pasta do .exe**, com aspas retas (") e
  salvo como UTF-8 (o Bloco de Notas já faz isso).
* Se o arquivo tiver algum erro, o programa abre com o nome padrão (Liga) em vez de
  travar: confira o nome na barra lateral.
