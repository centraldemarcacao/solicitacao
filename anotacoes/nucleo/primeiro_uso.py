"""
primeiro_uso.py
---------------
Quando mostrar o assistente de boas-vindas. Só em instalação realmente nova: sem registros,
sem nuvem conectada, sem PIN e sem ter sido concluído antes. Sem interface.
"""


def deve_mostrar(concluido: bool, total_registros: int, nuvem_conectada: bool,
                 tem_pin: bool) -> bool:
    return not (concluido or total_registros > 0 or nuvem_conectada or tem_pin)
