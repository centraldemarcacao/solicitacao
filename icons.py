"""
icons.py
--------
Ícones e logotipo desenhados com Pillow (sem emojis e sem depender de
fontes do sistema, que variam de máquina para máquina).

Os desenhos são feitos em alta resolução e reduzidos (antialiasing),
ficando nítidos em telas comuns e de alta densidade.
"""

from functools import lru_cache

from PIL import Image, ImageColor, ImageDraw

import theme as T

_BASE = 64          # coordenadas dos desenhos: grade de 64 x 64
_SS = 4             # fator de super-amostragem
_PX = _BASE * _SS


def _s(valor: float) -> int:
    return int(round(valor * _SS))


def _caixa(x0, y0, x1, y1):
    return [_s(x0), _s(y0), _s(x1), _s(y1)]


def _tela():
    img = Image.new("RGBA", (_PX, _PX), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _linha(d, pontos, cor, largura):
    """Linha grossa com pontas arredondadas."""
    pts = [(_s(x), _s(y)) for x, y in pontos]
    d.line(pts, fill=cor, width=_s(largura), joint="curve")
    r = largura / 2
    for x, y in (pontos[0], pontos[-1]):
        d.ellipse(_caixa(x - r, y - r, x + r, y + r), fill=cor)


# ----------------------------------------------------------------------
# Desenhos (grade 64 x 64)
# ----------------------------------------------------------------------
def _plus(d, c):
    d.rounded_rectangle(_caixa(27, 10, 37, 54), radius=_s(5), fill=c)
    d.rounded_rectangle(_caixa(10, 27, 54, 37), radius=_s(5), fill=c)


def _list(d, c):
    for y in (18, 32, 46):
        d.ellipse(_caixa(10, y - 3.5, 17, y + 3.5), fill=c)
        d.rounded_rectangle(_caixa(24, y - 3, 54, y + 3), radius=_s(3), fill=c)


def _check(d, c):
    _linha(d, [(13, 34), (26, 47), (51, 18)], c, 8)


def _clock(d, c):
    d.ellipse(_caixa(7, 7, 57, 57), outline=c, width=_s(6))
    _linha(d, [(32, 17), (32, 33), (43, 40)], c, 5)


def _trash(d, c):
    d.rounded_rectangle(_caixa(10, 15, 54, 22), radius=_s(3.5), fill=c)
    d.rounded_rectangle(_caixa(23, 7, 41, 17), radius=_s(4), outline=c, width=_s(4.5))
    d.rounded_rectangle(_caixa(16, 25, 48, 57), radius=_s(5), outline=c, width=_s(5))
    _linha(d, [(26, 33), (26, 49)], c, 4.5)
    _linha(d, [(38, 33), (38, 49)], c, 4.5)


def _search(d, c):
    d.ellipse(_caixa(8, 8, 40, 40), outline=c, width=_s(6))
    _linha(d, [(36, 36), (55, 55)], c, 7)


def _eye(d, c):
    d.ellipse(_caixa(5, 17, 59, 47), outline=c, width=_s(5))
    d.ellipse(_caixa(23, 24, 41, 40), fill=c)


def _clipboard(d, c):
    d.rounded_rectangle(_caixa(13, 11, 51, 58), radius=_s(7), outline=c, width=_s(5))
    d.rounded_rectangle(_caixa(23, 5, 41, 18), radius=_s(4.5), fill=c)
    _linha(d, [(22, 31), (42, 31)], c, 4.5)
    _linha(d, [(22, 42), (35, 42)], c, 4.5)


def _warning(d, c):
    _linha(d, [(32, 9), (57, 53), (7, 53), (32, 9)], c, 5)
    _linha(d, [(32, 25), (32, 38)], c, 5)
    d.ellipse(_caixa(29, 42, 35, 48), fill=c)


def _check_circle(d, c):
    d.ellipse(_caixa(6, 6, 58, 58), outline=c, width=_s(5))
    _linha(d, [(19, 33), (28, 42), (45, 24)], c, 6)


def _edit(d, c):
    # lápis na diagonal + linha de base
    d.polygon([(_s(24.2), _s(48.2)), (_s(15.8), _s(39.8)), (_s(41.8), _s(13.8)),
               (_s(50.2), _s(22.2))], fill=c)
    d.polygon([(_s(14), _s(42)), (_s(22), _s(50)), (_s(9), _s(55))], fill=c)
    _linha(d, [(34, 57), (55, 57)], c, 4.5)


def _restore(d, c):
    # seta circular (restaurar)
    d.arc(_caixa(10, 10, 54, 54), start=55, end=335, fill=c, width=_s(6))
    d.polygon([(_s(57), _s(34)), (_s(44), _s(26)), (_s(60), _s(18))], fill=c)


def _database(d, c):
    # cilindro (banco de dados / backup)
    larg = _s(5)
    d.ellipse(_caixa(12, 8, 52, 22), outline=c, width=larg)
    _linha(d, [(12, 15), (12, 49)], c, 5)
    _linha(d, [(52, 15), (52, 49)], c, 5)
    d.arc(_caixa(12, 28, 52, 42), start=0, end=180, fill=c, width=larg)
    d.arc(_caixa(12, 42, 52, 56), start=0, end=180, fill=c, width=larg)


def _download(d, c):
    # seta para baixo sobre uma bandeja
    _linha(d, [(32, 8), (32, 37)], c, 6)
    _linha(d, [(18, 26), (32, 40), (46, 26)], c, 6)
    _linha(d, [(10, 53), (54, 53)], c, 6)


_DESENHOS = {
    "download": _download,
    "edit": _edit,
    "restore": _restore,
    "database": _database,
    "plus": _plus,
    "list": _list,
    "check": _check,
    "clock": _clock,
    "trash": _trash,
    "search": _search,
    "eye": _eye,
    "clipboard": _clipboard,
    "warning": _warning,
    "check_circle": _check_circle,
}


def _desenhar_logo() -> Image.Image:
    """Marca própria: quadrado arredondado em degradê com cruz branca."""
    topo = ImageColor.getrgb(T.TEAL_ACENTO) + (255,)
    base = ImageColor.getrgb(T.TEAL_ESCURO) + (255,)
    gradiente = Image.linear_gradient("L").resize((_PX, _PX))
    fundo = Image.composite(
        Image.new("RGBA", (_PX, _PX), base),
        Image.new("RGBA", (_PX, _PX), topo),
        gradiente,
    )
    mascara = Image.new("L", (_PX, _PX), 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        _caixa(0, 0, 64, 64), radius=_s(17), fill=255
    )
    fundo.putalpha(mascara)

    d = ImageDraw.Draw(fundo)
    branco = (255, 255, 255, 255)
    d.rounded_rectangle(_caixa(25, 13, 39, 51), radius=_s(4), fill=branco)
    d.rounded_rectangle(_caixa(13, 25, 51, 39), radius=_s(4), fill=branco)
    return fundo


@lru_cache(maxsize=None)
def imagem(nome: str, cor: str = T.BRANCO, px: int = 128) -> Image.Image:
    """Imagem PIL do ícone `nome` na cor `cor` (hexadecimal), com `px` pixels."""
    if nome == "logo":
        img = _desenhar_logo()
    else:
        img, d = _tela()
        _DESENHOS[nome](d, ImageColor.getrgb(cor) + (255,))
    return img.resize((px, px), Image.LANCZOS)


@lru_cache(maxsize=None)
def icone(nome: str, cor: str = T.BRANCO, tamanho: int = 20):
    """CTkImage pronto para usar em botões e rótulos (`tamanho` em pixels lógicos)."""
    import customtkinter as ctk

    pil = imagem(nome, cor, max(128, tamanho * 4))
    return ctk.CTkImage(light_image=pil, size=(tamanho, tamanho))


def salvar_ico(caminho: str) -> None:
    """Gera o arquivo .ico (ícone do executável) a partir do logotipo."""
    imagem("logo", T.BRANCO, 256).save(
        caminho,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    # python icons.py  ->  gera icone.ico na pasta atual
    salvar_ico("icone.ico")
    print("icone.ico gerado.")
