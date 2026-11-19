"""Preferências do usuário: arquivo de preferências, modelos de descrição, alertas de pausa e regra do assistente de primeiro uso."""

import os
import tempfile
import unittest
from anotacoes.nucleo.preferencias import Preferencias
from anotacoes.nucleo import modelos, preferencias
from datetime import date, datetime
from anotacoes.nucleo.pausas import (HORARIOS_PADRAO, PAUSAS, TOLERANCIA_SEGUNDOS, horarios_validos,
                                     interpretar_horario, marcar_avisada, mensagem_da_pausa, montar_pausas, nomes_validos, pausa_devida)


def escrever(caminho, texto):
    with open(caminho, "w", encoding="utf-8") as arq:
        arq.write(texto)


class TestPreferencias(unittest.TestCase):
    def test_ciclo_e_arquivo_ruim(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "p.json")
            p = Preferencias(c)
            self.assertEqual(p.get("tema", "claro"), "claro")       # sem arquivo
            p.definir(tema="escuro", janela={"w": 1300})
            self.assertTrue(p.salvar())
            self.assertEqual(Preferencias(c).get("tema"), "escuro")
            self.assertEqual(Preferencias(c).get("janela")["w"], 1300)
            self.assertFalse(os.path.exists(c + ".tmp"))
            escrever(c, "{ isto não é json")                          # corrompido
            self.assertEqual(Preferencias(c).get("tema", "claro"), "claro")
            escrever(c, "[1, 2]")                                     # tipo errado
            self.assertEqual(Preferencias(c).dados, {})

    def test_alertas_de_pausa(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "p.json")
            p = Preferencias(c)
            self.assertTrue(p.alertas_pausa)                      # padrão: ligado
            p.alertas_pausa = False
            self.assertTrue(p.salvar())
            self.assertFalse(Preferencias(c).alertas_pausa)       # persiste
            p.alertas_pausa = True
            p.salvar()
            self.assertTrue(Preferencias(c).alertas_pausa)
            escrever(c, '{"alertas_pausa": "nao"}')               # valor inválido
            self.assertTrue(Preferencias(c).alertas_pausa)

    def test_horarios_de_pausa(self):
        padrao = {"nr17_1": "14:40", "lanche": "17:00", "nr17_2": "18:10"}
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "p.json")
            p = Preferencias(c)
            self.assertEqual(p.horarios_pausa, padrao)
            p.horarios_pausa = {"nr17_1": "9h30", "lanche": "12:00", "nr17_2": "bad"}
            self.assertTrue(p.salvar())
            self.assertEqual(Preferencias(c).horarios_pausa,
                             {"nr17_1": "09:30", "lanche": "12:00", "nr17_2": "18:10"})
            escrever(c, '{"horarios_pausa": [1, 2]}')                 # tipo errado
            self.assertEqual(Preferencias(c).horarios_pausa, padrao)

    def test_pasta_inexistente_nao_levanta(self):
        p = Preferencias(os.path.join(tempfile.gettempdir(), "nao_existe_xyz", "p.json"))
        p.definir(a=1)
        self.assertFalse(p.salvar())


class TestModelos(unittest.TestCase):
    def test_ausente_ou_invalido_volta_ao_padrao(self):
        for ruim in (None, "x", 5, {"a": 1}):
            self.assertEqual(modelos.validar_modelos(ruim), modelos.padrao())

    def test_lista_vazia_e_respeitada(self):
        self.assertEqual(modelos.validar_modelos([]), [])

    def test_descarta_itens_ruins_repetidos_e_limita(self):
        lixo = [{"titulo": "A", "texto": "a"}, {"titulo": "a", "texto": "outra"}, 3, {"titulo": ""},
                {"titulo": "B", "texto": "  "}, {"titulo": "C" * 80, "texto": "t" * 999}]
        r = modelos.validar_modelos(lixo)
        self.assertEqual([m["titulo"] for m in r], ["A", "C" * modelos.MAX_TITULO])
        self.assertEqual(len(r[1]["texto"]), modelos.MAX_TEXTO)
        muitos = [{"titulo": f"t{i}", "texto": "x"} for i in range(40)]
        self.assertEqual(len(modelos.validar_modelos(muitos)), modelos.MAX_MODELOS)

    def test_texto_com_modelo(self):
        self.assertEqual(modelos.texto_com_modelo("", "Solicita água.", 100), "Solicita água.")
        self.assertEqual(modelos.texto_com_modelo("  Algo \n", "Água.", 100), "Algo\nÁgua.")
        self.assertIsNone(modelos.texto_com_modelo("x" * 99, "yy", 100))

    def test_preferencias_guardam_modelos_e_primeiro_uso(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = os.path.join(d, "p.json")
            p = Preferencias(caminho)
            self.assertEqual(p.modelos_descricao, modelos.padrao())
            self.assertFalse(p.primeiro_uso_concluido)
            p.modelos_descricao = [{"titulo": "X", "texto": "y"}]
            p.primeiro_uso_concluido = True
            self.assertTrue(p.salvar())
            q = Preferencias(caminho)
            self.assertEqual(q.modelos_descricao, [{"titulo": "X", "texto": "y"}])
            self.assertTrue(q.primeiro_uso_concluido)

    def test_assistente_so_em_instalacao_nova(self):
        self.assertTrue(preferencias.deve_mostrar_primeiro_uso(False, 0, False, False))
        self.assertFalse(preferencias.deve_mostrar_primeiro_uso(True, 0, False, False))
        self.assertFalse(preferencias.deve_mostrar_primeiro_uso(False, 3, False, False))
        self.assertFalse(preferencias.deve_mostrar_primeiro_uso(False, 0, True, False))
        self.assertFalse(preferencias.deve_mostrar_primeiro_uso(False, 0, False, True))


def em(h, m, s=0, dia=11):
    return datetime(2026, 11, dia, h, m, s)


class TestPausas(unittest.TestCase):
    def test_horarios_e_tipos(self):
        self.assertEqual([(p.rotulo, p.tipo) for p in PAUSAS],
                         [("14:40", "nr17"), ("17:00", "lanche"), ("18:10", "nr17")])

    def test_dispara_no_segundo_zero_e_nao_antes(self):
        self.assertIsNone(pausa_devida(em(14, 39, 59), set()))
        self.assertEqual(pausa_devida(em(14, 40, 0), set()).rotulo, "14:40")
        self.assertEqual(pausa_devida(em(17, 0, 0), set()).tipo, "lanche")
        self.assertEqual(pausa_devida(em(18, 10, 30), set()).tipo, "nr17")

    def test_fora_de_horario_nao_dispara(self):
        for h, m in ((8, 0), (12, 0), (14, 38), (16, 59), (18, 9), (23, 59)):
            self.assertIsNone(pausa_devida(em(h, m), set()), f"{h}:{m}")

    def test_atraso_dentro_e_fora_da_tolerancia(self):
        self.assertIsNotNone(pausa_devida(em(14, 41, 59), set()))     # 1 min 59 s depois
        self.assertIsNone(pausa_devida(em(14, 42, 1), set()))         # passou de 2 min
        self.assertEqual(TOLERANCIA_SEGUNDOS, 120)

    def test_avisa_uma_vez_por_dia(self):
        avisadas = set()
        p = pausa_devida(em(14, 40), avisadas)
        marcar_avisada(avisadas, p, date(2026, 11, 11))
        self.assertIsNone(pausa_devida(em(14, 40, 1), avisadas))
        self.assertIsNone(pausa_devida(em(14, 41), avisadas))
        self.assertEqual(pausa_devida(em(14, 40, 0, dia=12), avisadas).rotulo, "14:40")  # dia seguinte

    def test_marcar_esquece_dias_anteriores(self):
        avisadas = set()
        marcar_avisada(avisadas, PAUSAS[0], date(2026, 11, 11))
        marcar_avisada(avisadas, PAUSAS[1], date(2026, 11, 12))
        self.assertEqual(avisadas, {(date(2026, 11, 12), "lanche", "17:00")})

    def test_interpretar_horario(self):
        for texto, esperado in (("14:40", (14, 40)), ("14h40", (14, 40)), ("14.40", (14, 40)),
                                ("1440", (14, 40)), ("940", (9, 40)), ("9", (9, 0)),
                                ("9h", (9, 0)), (" 7:05 ", (7, 5))):
            h = interpretar_horario(texto)
            self.assertEqual((h.hour, h.minute), esperado, texto)
        for ruim in ("24:00", "12:60", "abc", "", "14:4", "1:2", "14:40:10", None, 1440):
            self.assertIsNone(interpretar_horario(ruim), repr(ruim))

    def test_horarios_validos_completa_e_corrige(self):
        self.assertEqual(horarios_validos(None), HORARIOS_PADRAO)
        self.assertEqual(horarios_validos("lixo"), HORARIOS_PADRAO)
        r = horarios_validos({"lanche": "16h30", "nr17_1": "xx", "extra": "10:00"})
        self.assertEqual(r, {"nr17_1": "14:40", "lanche": "16:30", "nr17_2": "18:10"})

    def test_horarios_personalizados(self):
        pausas = montar_pausas({"nr17_1": "10:15", "lanche": "12:00", "nr17_2": "15:30"})
        self.assertEqual([p.rotulo for p in pausas], ["10:15", "12:00", "15:30"])
        self.assertIsNone(pausa_devida(em(14, 40), set(), pausas))          # horário antigo não dispara
        self.assertEqual(pausa_devida(em(12, 0), set(), pausas).tipo, "lanche")

    def test_mudar_horario_depois_de_avisar_avisa_de_novo(self):
        avisadas = set()
        antes = montar_pausas()
        p = pausa_devida(em(14, 40), avisadas, antes)
        marcar_avisada(avisadas, p, date(2026, 11, 11))
        depois = montar_pausas({"nr17_1": "14:50"})
        self.assertIsNone(pausa_devida(em(14, 40, 30), avisadas, depois))
        self.assertEqual(pausa_devida(em(14, 50), avisadas, depois).chave, "nr17_1")

    def test_nomes_padrao_e_personalizados(self):
        self.assertEqual([p.nome for p in montar_pausas()],
                         ["Pausa NR 17 (1ª)", "Pausa para lanche", "Pausa NR 17 (2ª)"])
        pausas = montar_pausas(None, {"lanche": "  Café   da tarde "})
        self.assertEqual(pausas[1].nome, "Café da tarde")
        self.assertEqual(pausas[1].titulo, "Café da tarde")        # título do aviso = nome na janela
        self.assertIn("Café da tarde", pausas[1].mensagem)

    def test_nome_invalido_volta_ao_padrao(self):
        r = nomes_validos({"lanche": "   ", "nr17_1": 5, "extra": "x"})
        self.assertEqual(r["lanche"], "Pausa para lanche")
        self.assertEqual(r["nr17_1"], "Pausa NR 17 (1ª)")
        self.assertEqual(set(r), {"nr17_1", "lanche", "nr17_2"})
        self.assertEqual(len(nomes_validos({"lanche": "x" * 200})["lanche"]), 40)

    def test_mensagem_coerente_com_o_nome(self):
        self.assertIn("NR 17", mensagem_da_pausa("nr17_1", "Pausa NR 17 (1ª)"))
        self.assertNotIn("NR 17", mensagem_da_pausa("nr17_1", "Alongamento"))   # nome trocado: sem dica de NR 17

    def test_preferencias_guardam_nomes(self):
        d = tempfile.mkdtemp()
        p = Preferencias(os.path.join(d, "p.json"))
        p.nomes_pausa = {"lanche": "Café"}
        p.salvar()
        self.assertEqual(Preferencias(os.path.join(d, "p.json")).nomes_pausa["lanche"], "Café")


class TestPrazosRetorno(unittest.TestCase):
    def test_padrao_e_invalidos(self):
        from anotacoes.nucleo.prazos import validar_prazos
        self.assertEqual(validar_prazos(None), [1, 3, 7])
        self.assertEqual(validar_prazos([]), [1, 3, 7])
        self.assertEqual(validar_prazos([7, 1, 7, 0, 400, "x", True, 3.5]), [1, 7])
        self.assertEqual(validar_prazos([5, 4, 3, 2, 1]), [1, 2, 3, 4])      # no máximo 4

    def test_interpretar(self):
        from anotacoes.nucleo.prazos import interpretar_prazos, rotulo_prazo, prazos_para_texto
        self.assertEqual(interpretar_prazos("1, 3  7;14"), [1, 3, 7, 14])
        self.assertEqual(interpretar_prazos("7,1,7"), [1, 7])
        for ruim in ("", "  ", "a", "0", "366", "-1", "1,2,3,4,5"):
            with self.assertRaises(ValueError, msg=ruim):
                interpretar_prazos(ruim)
        self.assertEqual((rotulo_prazo(1), rotulo_prazo(3)), ("Amanhã", "3 dias"))
        self.assertEqual(prazos_para_texto([3, 1]), "1, 3")

    def test_preferencias_guardam_prazos(self):
        d = tempfile.mkdtemp()
        p = Preferencias(os.path.join(d, "p.json"))
        self.assertEqual(p.prazos_retorno, [1, 3, 7])
        p.prazos_retorno = [2, 10]
        p.salvar()
        self.assertEqual(Preferencias(os.path.join(d, "p.json")).prazos_retorno, [2, 10])


if __name__ == "__main__":
    unittest.main()
