import unittest

from anotacoes.nuvem import projeto

CHAVE = "sb_publishable_" + "A" * 24


class T(unittest.TestCase):
    def test_sem_chave_nao_fixa(self):
        self.assertIsNone(projeto.projeto_fixo("https://abc.supabase.co", ""))
        self.assertIsNone(projeto.projeto_fixo("", CHAVE))

    def test_completo_normaliza(self):
        self.assertEqual(projeto.projeto_fixo("abc.supabase.co", CHAVE),
                         ("https://abc.supabase.co", CHAVE))

    def test_recusa_chave_secreta(self):
        self.assertIsNone(projeto.projeto_fixo("https://abc.supabase.co", "sb_secret_" + "x" * 30))

    def test_padrao_do_repositorio_e_valido_ou_vazio(self):
        r = projeto.projeto_fixo()
        self.assertTrue(r is None or r[1].startswith(("sb_publishable_", "eyJ")))


if __name__ == "__main__":
    unittest.main()
