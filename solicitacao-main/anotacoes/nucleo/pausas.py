"""
pausas.py
---------
Alertas de pausa do dia (sem interface, fácil de testar).

Padrão:
  14:40  Pausa NR 17
  17:00  Pausa para lanche
  18:10  Pausa NR 17

Os três horários podem ser alterados pelo usuário (janela "Alertas de pausa");
`montar_pausas` junta os horários salvos com os textos de cada alerta e
`pausa_devida` diz qual deve aparecer agora. Quem avisa o usuário é
interface/mixins/pausas.py.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

# Se o programa estava travado, o computador dormindo ou a janela ocupada, o
# alerta ainda aparece até este tempo depois do horário. Passou disso, o aviso
# perdeu o sentido ("pausa das 14:40" às 16:00) e é descartado.
TOLERANCIA_SEGUNDOS = 120

_MSG_NR17 = ("Hora da pausa da NR 17. Levante-se, alongue-se e descanse a vista e as mãos "
             "por alguns minutos.")
_MSG_LANCHE = "Hora da pausa para o lanche. Aproveite para comer e se hidratar."

# (chave, horário padrão, tipo, título do aviso, nome no formulário, mensagem)
MODELOS = (
    ("nr17_1", "14:40", "nr17", "Pausa NR 17", "Pausa NR 17 (1ª)", _MSG_NR17),
    ("lanche", "17:00", "lanche", "Pausa para lanche", "Pausa para lanche", _MSG_LANCHE),
    ("nr17_2", "18:10", "nr17", "Pausa NR 17", "Pausa NR 17 (2ª)", _MSG_NR17),
)
HORARIOS_PADRAO = {chave: padrao for chave, padrao, *_ in MODELOS}

_FORMATOS_HORARIO = (
    re.compile(r"(\d{1,2})\s*[:hH.]\s*(\d{2})"),    # 14:40, 14h40, 14.40
    re.compile(r"(\d{1,2})(\d{2})"),                 # 1440, 940
    re.compile(r"(\d{1,2})\s*[hH]?()"),              # 9, 9h  (= 09:00)
)


def interpretar_horario(texto) -> Optional[time]:
    """'14:40', '14h40', '14.40', '1440' ou '9' (= 09:00) -> time. Inválido -> None."""
    if not isinstance(texto, str):
        return None
    for formato in _FORMATOS_HORARIO:
        m = formato.fullmatch(texto.strip())
        if m:
            hora, minuto = int(m.group(1)), int(m.group(2) or 0)
            return time(hora, minuto) if hora <= 23 and minuto <= 59 else None
    return None


@dataclass(frozen=True)
class Pausa:
    chave: str
    hora: time
    tipo: str          # "nr17" ou "lanche"
    titulo: str
    nome: str          # rótulo no formulário de horários
    mensagem: str

    @property
    def rotulo(self) -> str:
        return self.hora.strftime("%H:%M")


def horarios_validos(brutos) -> dict:
    """{chave: "HH:MM"} completo: o que for ausente ou inválido volta ao padrão."""
    brutos = brutos if isinstance(brutos, dict) else {}
    resultado = {}
    for chave, padrao, *_ in MODELOS:
        hora = interpretar_horario(brutos.get(chave))
        resultado[chave] = hora.strftime("%H:%M") if hora else padrao
    return resultado


def montar_pausas(horarios=None) -> tuple:
    """Pausas do dia com os horários informados (None = padrão)."""
    valid = horarios_validos(horarios)
    return tuple(
        Pausa(chave, interpretar_horario(valid[chave]), tipo, titulo, nome, mensagem)
        for chave, _padrao, tipo, titulo, nome, mensagem in MODELOS)


PAUSAS = montar_pausas()


def pausa_devida(agora: datetime, ja_avisadas: set, pausas=PAUSAS) -> Optional[Pausa]:
    """Pausa cujo horário já chegou (e ainda está dentro da tolerância) e que
    não foi avisada hoje nesse horário. `ja_avisadas` guarda (data, chave, "HH:MM"):
    mudar o horário de uma pausa depois de avisada permite avisar de novo."""
    for pausa in pausas:
        if (agora.date(), pausa.chave, pausa.rotulo) in ja_avisadas:
            continue
        atraso = (agora - datetime.combine(agora.date(), pausa.hora)).total_seconds()
        if 0 <= atraso <= TOLERANCIA_SEGUNDOS:
            return pausa
    return None


def marcar_avisada(ja_avisadas: set, pausa: Pausa, dia: date) -> None:
    """Registra a pausa como avisada no dia e esquece os dias anteriores."""
    ja_avisadas.difference_update({c for c in ja_avisadas if c[0] != dia})
    ja_avisadas.add((dia, pausa.chave, pausa.rotulo))
