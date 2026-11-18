import sys
import unittest
from unittest import mock

from anotacoes.nucleo import inicializacao as ini


class _Chave:
    def __init__(self, valores): self.valores = valores
    def __enter__(self): return self
    def __exit__(self, *a): return False


class FakeWinreg:
    """Registro de mentira: só a parte usada pelo programa."""
    HKEY_CURRENT_USER, KEY_READ, KEY_SET_VALUE, REG_SZ = "HKCU", 1, 2, 1

    def __init__(self, recusar=False):
        self.valores, self.recusar = {}, recusar
    def OpenKey(self, raiz, caminho, reservado=0, acesso=1):
        if self.recusar: raise PermissionError("negado")
        if caminho != ini.CHAVE_RUN: raise FileNotFoundError(caminho)
        return _Chave(self.valores)
    def CreateKeyEx(self, raiz, caminho, reservado=0, acesso=2):
        if self.recusar: raise PermissionError("negado")
        return _Chave(self.valores)
    def QueryValueEx(self, chave, nome):
        if nome not in chave.valores: raise FileNotFoundError(nome)
        return chave.valores[nome], self.REG_SZ
    def SetValueEx(self, chave, nome, _r, tipo, valor): chave.valores[nome] = valor
    def DeleteValue(self, chave, nome):
        if nome not in chave.valores: raise FileNotFoundError(nome)
        del chave.valores[nome]


class T(unittest.TestCase):
    def _contexto(self, reg, exe=r"C:\Programas\Anotações\App.exe", empacotado=True):
        return (mock.patch.object(ini, "_winreg", lambda: reg),
                mock.patch.object(sys, "executable", exe),
                mock.patch.object(sys, "frozen", empacotado, create=True))

    def _com(self, reg, **kw):
        from contextlib import ExitStack
        pilha = ExitStack()
        for c in self._contexto(reg, **kw):
            pilha.enter_context(c)
        self.addCleanup(pilha.close)

    def test_comando_com_aspas_e_minimizado(self):
        self._com(FakeWinreg())
        self.assertTrue(ini.comando().endswith('" --minimizado'))
        self.assertTrue(ini.comando().startswith('"'))

    def test_ligar_e_desligar(self):
        reg = FakeWinreg(); self._com(reg)
        self.assertTrue(ini.suportado())
        self.assertFalse(ini.ativo())
        ini.ativar()
        self.assertTrue(ini.ativo())
        self.assertEqual(reg.valores[ini.NOME_VALOR], ini.comando())
        ini.desativar()
        self.assertFalse(ini.ativo())
        ini.desativar()                       # desligar de novo não dá erro

    def test_so_funciona_no_exe(self):
        self._com(FakeWinreg(), empacotado=False)
        self.assertFalse(ini.suportado())
        with self.assertRaises(OSError):
            ini.ativar()

    def test_windows_recusa(self):
        self._com(FakeWinreg(recusar=True))
        with self.assertRaises(OSError):
            ini.ativar()
        self.assertFalse(ini.ativo())         # leitura que falha = desligado, sem exceção

    def test_sem_winreg_fora_do_windows(self):
        with mock.patch.object(ini, "_winreg", lambda: None):
            self.assertFalse(ini.suportado() or ini.ativo())
            ini.desativar(); ini.corrigir_caminho()      # não levantam

    def test_corrigir_caminho_quando_o_exe_mudou_de_pasta(self):
        reg = FakeWinreg(); self._com(reg, exe=r"C:\Novo\App.exe")
        reg.valores[ini.NOME_VALOR] = '"C:\\Velho\\App.exe" --minimizado'
        ini.corrigir_caminho()
        self.assertEqual(reg.valores[ini.NOME_VALOR], ini.comando())
        self.assertIn("Novo", reg.valores[ini.NOME_VALOR])

    def test_corrigir_caminho_nao_liga_se_estava_desligado(self):
        reg = FakeWinreg(); self._com(reg)
        ini.corrigir_caminho()
        self.assertEqual(reg.valores, {})


if __name__ == "__main__":
    unittest.main()
