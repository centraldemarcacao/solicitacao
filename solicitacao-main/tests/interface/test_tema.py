"""Contraste mínimo (WCAG AA, 4,5:1) das combinações usadas nos dois temas."""
import unittest

from anotacoes import theme as T


def _lum(hex_):
    h = hex_.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contraste(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (texto, fundo): nomes de constantes de theme.py
PARES = (
    [("TEXTO", f) for f in ("FUNDO", "CARD", "SUPERFICIE", "SELECAO", "TEAL_CLARO",
                            "AMBAR_CLARO", "VERDE_CLARO", "VERMELHO_CLARO", "SEG_SELECIONADO")]
    + [("TEXTO_SUAVE", f) for f in ("FUNDO", "CARD", "SUPERFICIE")]
    + [("PLACEHOLDER", "SUPERFICIE"), ("PLACEHOLDER", "CARD")]
    + [("SOBRE_COR", f) for f in ("TEAL", "TEAL_ESCURO", "VERDE", "VERDE_HOVER", "AMBAR",
                                  "AMBAR_HOVER", "VERMELHO", "VERMELHO_HOVER")]
    + [(c, f) for c in ("TEAL", "VERDE", "AMBAR", "VERMELHO")
       for f in ("FUNDO", "CARD", "SUPERFICIE")]
    + [("TEAL", "TEAL_CLARO"), ("TEAL_ESCURO", "TEAL_CLARO"), ("VERDE", "VERDE_CLARO"),
       ("AMBAR", "AMBAR_CLARO"), ("VERMELHO", "VERMELHO_CLARO")]
)


class TestTema(unittest.TestCase):
    def tearDown(self):
        T.aplicar_tema("claro")

    def _checar(self, tema):
        T.aplicar_tema(tema)
        for texto, fundo in PARES:
            c = contraste(getattr(T, texto), getattr(T, fundo))
            self.assertGreaterEqual(c, 4.5, f"{tema}: {texto} sobre {fundo} = {c:.2f}")

    def test_claro(self):
        self._checar("claro")

    def test_escuro(self):
        self._checar("escuro")

    def test_fixos_na_barra_lateral(self):
        for tema in ("claro", "escuro"):
            T.aplicar_tema(tema)
            self.assertGreaterEqual(contraste(T.BRANCO, T.NAVY), 4.5)
            self.assertGreaterEqual(contraste(T.NAV_SUAVE, T.NAVY), 4.5)

    def test_troca_e_volta(self):
        T.aplicar_tema("escuro"); self.assertEqual(T.FUNDO, "#0E1822")
        T.aplicar_tema("claro"); self.assertEqual(T.FUNDO, "#EEF4F8")
        self.assertEqual(T.aplicar_tema("inexistente"), "claro")


if __name__ == "__main__":
    unittest.main()
