"""
identidade.py
-------------
Identidade visual editável dentro do programa: nome, subtítulo, logo e ícone
da janela. Tudo fica na pasta `dados` DESTE computador, então cada computador
(Liga, Intesoftware...) tem a sua própria identidade, sem arquivos para mexer
na mão e sem mexer no .exe.

Arquivos em `dados/`:
  identidade.json           nome e subtítulo
  logo_personalizado.png    logo mostrado na barra lateral
  icone_personalizado.ico   ícone da janela / barra de tarefas (gerado do logo)

Sem identidade.json, valem o nome e o subtítulo de fábrica (theme.NOME_PADRAO
e theme.SUBTITULO_PADRAO).
"""

import json
import os
from typing import Optional, Tuple

from anotacoes import theme as T

ARQ_JSON = "identidade.json"
ARQ_LOGO = "logo_personalizado.png"
ARQ_ICONE = "icone_personalizado.ico"

MAX_NOME = 40
MAX_SUBTITULO = 40
MAX_BYTES_IMAGEM = 10 * 1024 * 1024
MAX_PIXELS = 50_000_000
LADO_LOGO = 512
TAMANHOS_ICONE = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
EXTENSOES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico")


def titulo_completo() -> str:
    """'Nome — Subtítulo' (ou só o nome, se não houver subtítulo)."""
    if T.SUBTITULO:
        return f"{T.NOME_INSTITUICAO} — {T.SUBTITULO}"
    return T.NOME_INSTITUICAO


def validar_textos(nome: str, subtitulo: str) -> Tuple[str, str]:
    """Normaliza os espaços e valida. O subtítulo pode ficar em branco."""
    nome = " ".join((nome or "").split())
    subtitulo = " ".join((subtitulo or "").split())
    if not nome:
        raise ValueError("Informe o nome.")
    if len(nome) > MAX_NOME:
        raise ValueError(f"O nome pode ter até {MAX_NOME} caracteres.")
    if len(subtitulo) > MAX_SUBTITULO:
        raise ValueError(f"O subtítulo pode ter até {MAX_SUBTITULO} caracteres.")
    return nome, subtitulo


class Identidade:
    def __init__(self, pasta: str) -> None:
        self.pasta = pasta

    # --- caminhos ----------------------------------------------------------
    def _caminho(self, nome: str) -> str:
        return os.path.join(self.pasta, nome)

    def caminho_logo(self) -> Optional[str]:
        c = self._caminho(ARQ_LOGO)
        return c if os.path.isfile(c) else None

    def caminho_icone(self) -> Optional[str]:
        c = self._caminho(ARQ_ICONE)
        return c if os.path.isfile(c) else None

    # --- textos --------------------------------------------------------------
    def carregar(self) -> Optional[Tuple[str, str]]:
        """(nome, subtítulo) salvos aqui, ou None se nunca foram personalizados
        (ou se o arquivo estiver ilegível)."""
        try:
            with open(self._caminho(ARQ_JSON), encoding="utf-8-sig") as arq:
                dados = json.load(arq)
            return validar_textos(dados["nome"], dados.get("subtitulo", ""))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def salvar_textos(self, nome: str, subtitulo: str) -> Tuple[str, str]:
        nome, subtitulo = validar_textos(nome, subtitulo)
        _gravar_atomico(self._caminho(ARQ_JSON),
                        json.dumps({"nome": nome, "subtitulo": subtitulo},
                                   ensure_ascii=False, indent=2).encode("utf-8"))
        return nome, subtitulo

    def aplicar(self) -> None:
        """Coloca a identidade em uso (theme.NOME_INSTITUICAO / SUBTITULO)."""
        textos = self.carregar()
        if textos:
            T.NOME_INSTITUICAO, T.SUBTITULO = textos

    # --- logo e ícone -------------------------------------------------------
    def definir_logo(self, origem: str) -> None:
        """Importa uma imagem: gera o logo (PNG) e o ícone da janela (ICO).
        Lança ValueError com mensagem em português se a imagem não servir."""
        from PIL import Image, ImageOps

        try:
            if os.path.getsize(origem) > MAX_BYTES_IMAGEM:
                raise ValueError("A imagem é muito grande (máximo 10 MB).")
            with Image.open(origem) as bruta:
                if bruta.width * bruta.height > MAX_PIXELS:
                    raise ValueError("A imagem tem dimensões grandes demais.")
                bruta.load()
                img = ImageOps.exif_transpose(bruta).convert("RGBA")
        except ValueError:
            raise
        except Exception:
            raise ValueError("Não foi possível abrir essa imagem. "
                             "Use um arquivo PNG, JPG, BMP, GIF, WEBP ou ICO.") from None

        logo = img.copy()
        logo.thumbnail((LADO_LOGO, LADO_LOGO))
        lado = max(img.size)
        quadrado = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        quadrado.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2))
        quadrado = quadrado.resize((256, 256))

        os.makedirs(self.pasta, exist_ok=True)
        _gravar_imagem(self._caminho(ARQ_LOGO), logo, "PNG")
        _gravar_imagem(self._caminho(ARQ_ICONE), quadrado, "ICO", sizes=TAMANHOS_ICONE)

    def remover_logo(self) -> None:
        for nome in (ARQ_LOGO, ARQ_ICONE):
            try:
                os.remove(self._caminho(nome))
            except FileNotFoundError:
                pass

    def restaurar_padrao(self) -> None:
        """Volta ao nome e logo de fábrica."""
        self.remover_logo()
        try:
            os.remove(self._caminho(ARQ_JSON))
        except FileNotFoundError:
            pass
        T.NOME_INSTITUICAO, T.SUBTITULO = T.NOME_PADRAO, T.SUBTITULO_PADRAO


# ----------------------------------------------------------------------
def _gravar_atomico(caminho: str, conteudo: bytes) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "wb") as arq:
        arq.write(conteudo)
    os.replace(tmp, caminho)


def _gravar_imagem(caminho: str, imagem, formato: str, **opcoes) -> None:
    tmp = caminho + ".tmp"
    imagem.save(tmp, format=formato, **opcoes)
    os.replace(tmp, caminho)
